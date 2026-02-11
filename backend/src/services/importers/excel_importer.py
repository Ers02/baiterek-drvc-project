from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ValidationError, field_validator
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
import openpyxl
import io
from ...models import models
from ...utils.helpers import get_need_type_by_typename, is_smr
from ..dictionary_service import get_mkei_map, get_cost_item_map, get_kato_map, get_agsk_map

# --- Pydantic модель для строки импорта ---
class ImportRow(BaseModel):
    row_idx: int
    trucode: str
    additional_specs: str
    additional_specs_kz: str
    unit_raw: Optional[str] = None
    quantity: Decimal = Field(gt=0)
    price: Decimal = Field(ge=0)
    kato_purchase_code: str
    kato_delivery_code: str
    expense_id: int
    source_id: int
    agsk_code: Optional[str] = None
    resident_share: Decimal = Field(default=100, ge=0, le=100)
    non_resident_reason: Optional[str] = None

    @field_validator('trucode')
    def validate_trucode(cls, v):
        if not v or not v.strip():
            raise ValueError("Код ЕНС ТРУ обязателен")
        return v.strip()

def extract_code(val):
    if val is None: return None
    val_str = str(val).strip()
    if not val_str: return None
    if " - " in val_str:
        return val_str.split(" - ")[0].strip()
    return val_str

def parse_excel_rows(ws) -> list[dict]:
    """Читает Excel и возвращает список сырых словарей."""
    rows = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # Проверка на пустую строку
        if not any(cell is not None and str(cell).strip() for cell in row):
            continue
            
        row_data = list(row) + [None] * max(0, 16 - len(row))
        
        # Формируем словарь для Pydantic
        try:
            # Обработка числовых полей с защитой от None
            qty = row_data[6]
            price = row_data[7]
            
            # Обработка доли
            res_share = row_data[14]
            if res_share is None: res_share = 100
            
            data = {
                "row_idx": row_idx,
                "trucode": str(row_data[1]) if row_data[1] else "",
                "additional_specs": str(row_data[3]).strip() if row_data[3] else "",
                "additional_specs_kz": str(row_data[4]).strip() if row_data[4] else "",
                "unit_raw": str(row_data[5]).strip() if row_data[5] else None,
                "quantity": qty,
                "price": price,
                "kato_purchase_code": extract_code(row_data[9]) or "",
                "kato_delivery_code": extract_code(row_data[10]) or "",
                "expense_id": int(extract_code(row_data[11]) or 0),
                "source_id": int(extract_code(row_data[12]) or 0),
                "agsk_code": str(row_data[13]).strip() if (row_data[13] and str(row_data[13]).strip()) else None,
                "resident_share": res_share,
                "non_resident_reason": str(row_data[15]).strip() if row_data[15] else None
            }
            rows.append(data)
        except Exception as e:
            rows.append({"row_idx": row_idx, "error": str(e)})
            
    return rows

def import_items_from_excel(db: Session, version_id: int, file_content: bytes) -> tuple[list[models.PlanItemVersion], list[dict]]:
    """
    Основная функция импорта.
    Возвращает (список созданных объектов, список ошибок).
    """
    wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True)
    ws = wb["Позиции для загрузки"] if "Позиции для загрузки" in wb.sheetnames else wb.active
    
    raw_rows = parse_excel_rows(ws)
    valid_rows = []
    errors = []

    # 1. Валидация Pydantic и сбор кодов для Batch Fetch (только для ЕНС ТРУ)
    trucodes_to_fetch = set()

    for r in raw_rows:
        if "error" in r:
            errors.append({"row": r["row_idx"], "message": f"Ошибка чтения строки: {r['error']}"})
            continue
            
        try:
            row_obj = ImportRow(**r)
            valid_rows.append(row_obj)
            trucodes_to_fetch.add(row_obj.trucode)
        except ValidationError as e:
            msg = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
            errors.append({"row": r["row_idx"], "message": msg})

    # 2. Загрузка справочников (Кэш + Batch Fetch)

    # Кэшированные справочники (быстрый доступ)
    mkei_map = get_mkei_map()
    kato_map = get_kato_map()
    agsk_map = get_agsk_map()
    cost_map = get_cost_item_map()
    
    # ЕНС ТРУ (Batch Fetch, так как он большой)
    enstru_map = {}
    if trucodes_to_fetch:
        # Загружаем только type_name, так как он нужен для логики
        items = db.query(models.Enstru.code, models.Enstru.type_name).filter(models.Enstru.code.in_(trucodes_to_fetch)).all()
        for code, type_name in items:
            enstru_map[code] = type_name

    # Reestr KTP (min dvc)
    reestr_ktp_map = {}
    if trucodes_to_fetch:
        ktp_results = db.query(
            models.Reestr_KTP.enstru_code,
            func.min(models.Reestr_KTP.dvc_percent)
        ).filter(
            models.Reestr_KTP.enstru_code.in_(trucodes_to_fetch)
        ).group_by(models.Reestr_KTP.enstru_code).all()
        for code, dvc in ktp_results:
            reestr_ktp_map[code] = Decimal(str(dvc)) if dvc is not None else Decimal(0)

    # 3. Создание объектов
    new_items = []
    
    # Счетчики номеров
    last_numbers = {
        models.NeedType.GOODS: 0,
        models.NeedType.WORKS: 0,
        models.NeedType.SERVICES: 0
    }
    for nt in last_numbers:
        last = db.query(models.PlanItemVersion).filter(
            models.PlanItemVersion.version_id == version_id,
            models.PlanItemVersion.need_type == nt
        ).order_by(desc(models.PlanItemVersion.item_number)).first()
        if last: last_numbers[nt] = last.item_number

    for row in valid_rows:
        # Проверки справочников
        if row.trucode not in enstru_map:
            errors.append({"row": row.row_idx, "message": f"Не найден ЕНС ТРУ {row.trucode}"})
            continue
            
        kato_p_id = kato_map.get(row.kato_purchase_code)
        kato_d_id = kato_map.get(row.kato_delivery_code)
        if not kato_p_id or not kato_d_id:
            errors.append({"row": row.row_idx, "message": "Не найден КАТО"})
            continue
            
        if row.expense_id not in cost_map:
             errors.append({"row": row.row_idx, "message": f"Не найдена статья затрат {row.expense_id}"})
             continue

        # Проверка СМР по ID=1
        is_smr_item = is_smr(row.expense_id)
        
        agsk_code = None
        if row.agsk_code:
            if row.agsk_code.lower() == "прайс-лист":
                agsk_code = None
            else:
                if row.agsk_code not in agsk_map:
                    errors.append({"row": row.row_idx, "message": f"Не найден АГСК {row.agsk_code}"})
                    continue
                agsk_code = row.agsk_code
        
        if is_smr_item and agsk_code is None and (not row.agsk_code or row.agsk_code.lower() != "прайс-лист"):
             errors.append({"row": row.row_idx, "message": "Для СМР (ID=1) нужен код АГСК или 'Прайс-лист'"})
             continue

        # Определение типа
        type_name = enstru_map[row.trucode]
        need_type = get_need_type_by_typename(type_name)
        
        # Единица измерения
        unit_id = None
        original_unit_name = None
        
        if is_smr_item:
            original_unit_name = row.unit_raw
        elif need_type == models.NeedType.GOODS:
            unit_code = extract_code(row.unit_raw)
            if unit_code and unit_code in mkei_map:
                unit_id = mkei_map[unit_code]
            else:
                original_unit_name = row.unit_raw
            
            if not unit_id and not original_unit_name:
                errors.append({"row": row.row_idx, "message": "Не указана единица измерения"})
                continue
        
        # Корректировка количества для работ/услуг
        quantity = row.quantity
        if need_type != models.NeedType.GOODS:
            quantity = Decimal(1)
            
        # Доля ВЦ
        resident_share = row.resident_share
        non_resident_reason = row.non_resident_reason
        if need_type == models.NeedType.GOODS:
            resident_share = Decimal(0)
            non_resident_reason = None
        else:
            if resident_share < 100 and not non_resident_reason:
                errors.append({"row": row.row_idx, "message": "Нужно обоснование для доли < 100%"})
                continue

        # Расчет ВЦ
        is_ktp = False
        min_dvc = Decimal(0)
        if need_type == models.NeedType.GOODS:
            dvc = reestr_ktp_map.get(row.trucode)
            if dvc is not None:
                is_ktp = True
                min_dvc = dvc
        else:
            min_dvc = resident_share

        last_numbers[need_type] += 1
        
        item = models.PlanItemVersion(
            version_id=version_id,
            item_number=last_numbers[need_type],
            need_type=need_type,
            trucode=row.trucode,
            unit_id=unit_id,
            original_unit_name=original_unit_name,
            expense_item_id=row.expense_id,
            funding_source_id=row.source_id,
            agsk_id=agsk_code,
            kato_purchase_id=kato_p_id,
            kato_delivery_id=kato_d_id,
            additional_specs=row.additional_specs,
            additional_specs_kz=row.additional_specs_kz,
            quantity=quantity,
            price_per_unit=row.price,
            total_amount=quantity * row.price,
            is_ktp=is_ktp,
            is_deleted=False,
            revision_number=0,
            min_dvc_percent=min_dvc,
            resident_share=resident_share,
            non_resident_reason=non_resident_reason
        )
        new_items.append(item)

    return new_items, errors
