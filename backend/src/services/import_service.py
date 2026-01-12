import io
from decimal import Decimal

from sqlalchemy import desc
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
import openpyxl
from openpyxl.styles import Font, PatternFill
from ..models import models
from ..services import plan_service

def generate_import_template(db: Session) -> bytes:
    """Генерирует Excel-шаблон для импорта позиций со справочниками."""
    wb = openpyxl.Workbook()
    
    # --- Лист 1: Данные для заполнения ---
    ws_data = wb.active
    ws_data.title = "Позиции для загрузки"
    
    headers = [
        "Код ЕНС ТРУ (обязательно)", 
        "Код Ед. изм. (МКЕИ) (обязательно)", 
        "Кол-во (обязательно)", 
        "Цена за ед. (обязательно)", 
        "ID Статьи затрат (см. Справочники)", 
        "ID Источника фин. (см. Справочники)",
        "Код КАТО закупки (обязательно)",
        "Код КАТО поставки (обязательно)",
        "Код АГСК (обязательно для СМР)",
        "Доп. характеристика"
    ]
    
    # Стилизация заголовков
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1B5E20", end_color="1B5E20", fill_type="solid")
    
    ws_data.append(headers)
    for cell in ws_data[1]:
        cell.font = header_font
        cell.fill = header_fill

    # Пример данных
    ws_data.append(["01.11.11.000.000.00.0000.000000", "796", 100, 5000, 1, 1, "710000000", "710000000", "", "Пример описания"])

    # Настройка ширины колонок
    ws_data.column_dimensions['A'].width = 35
    ws_data.column_dimensions['B'].width = 15
    ws_data.column_dimensions['G'].width = 20
    ws_data.column_dimensions['H'].width = 20
    ws_data.column_dimensions['I'].width = 25
    ws_data.column_dimensions['J'].width = 40

    # --- Лист 2: Справочники ---
    ws_ref = wb.create_sheet("Справочники")
    
    # Статьи затрат
    ws_ref.cell(row=1, column=1, value="СТАТЬИ ЗАТРАТ").font = Font(bold=True)
    ws_ref.cell(row=2, column=1, value="ID").font = Font(bold=True)
    ws_ref.cell(row=2, column=2, value="Наименование").font = Font(bold=True)
    
    cost_items = db.query(models.Cost_Item).all()
    for idx, item in enumerate(cost_items, start=3):
        ws_ref.cell(row=idx, column=1, value=item.id)
        ws_ref.cell(row=idx, column=2, value=item.name_ru)

    # Источники финансирования
    ws_ref.cell(row=1, column=4, value="ИСТОЧНИКИ ФИНАНСИРОВАНИЯ").font = Font(bold=True)
    ws_ref.cell(row=2, column=4, value="ID").font = Font(bold=True)
    ws_ref.cell(row=2, column=5, value="Наименование").font = Font(bold=True)
    
    sources = db.query(models.Source_Funding).all()
    for idx, item in enumerate(sources, start=3):
        ws_ref.cell(row=idx, column=4, value=item.id)
        ws_ref.cell(row=idx, column=5, value=item.name_ru)

    # Популярные МКЕИ
    ws_ref.cell(row=1, column=7, value="ПОПУЛЯРНЫЕ ЕД. ИЗМ. (МКЕИ)").font = Font(bold=True)
    ws_ref.cell(row=2, column=7, value="Код").font = Font(bold=True)
    ws_ref.cell(row=2, column=8, value="Наименование").font = Font(bold=True)
    
    mkeis = db.query(models.Mkei).limit(50).all() # Берем первые 50 для примера
    for idx, item in enumerate(mkeis, start=3):
        ws_ref.cell(row=idx, column=7, value=item.code)
        ws_ref.cell(row=idx, column=8, value=item.name_ru)

    virtual_workbook = io.BytesIO()
    wb.save(virtual_workbook)
    return virtual_workbook.getvalue()


def process_import_file(db: Session, plan_id: int, file: UploadFile, user: models.User):
    """Читает Excel и создает позиции."""
    
    # 1. Получаем активную версию плана
    active_version = plan_service._get_active_version(db, plan_id)
    if not active_version:
        raise HTTPException(status_code=404, detail="Активная версия плана не найдена")
    
    if active_version.status != models.PlanStatus.DRAFT:
        raise HTTPException(status_code=403, detail="Импорт возможен только в черновик")
    
    if active_version.plan.created_by != user.id:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование этого плана")

    # 2. Читаем файл
    try:
        contents = file.file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        ws = wb.active
    except Exception:
        raise HTTPException(status_code=400, detail="Неверный формат файла. Ожидается .xlsx")

    # 3. Парсим строки
    new_items = []
    errors = []
    
    # Находим последний номер позиции (включая удаленные)
    last_item = db.query(models.PlanItemVersion).filter(
        models.PlanItemVersion.version_id == active_version.id
    ).order_by(desc(models.PlanItemVersion.item_number)).first()
    next_item_number = (last_item.item_number + 1) if last_item else 1

    # Пропускаем заголовок (строка 1)
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # Ожидаемый формат:
        # 0: trucode, 1: unit_code, 2: quantity, 3: price, 4: expense_id, 5: source_id, 
        # 6: kato_purchase, 7: kato_delivery, 8: agsk, 9: specs
        
        if not row[0]: # Если нет кода ЕНС ТРУ, пропускаем или считаем концом
            continue

        trucode = str(row[0]).strip()
        unit_code = str(row[1]).strip() if row[1] else None
        try:
            quantity = Decimal(str(row[2])) if row[2] else Decimal(0)
            price = Decimal(str(row[3])) if row[3] else Decimal(0)
            expense_id = int(row[4]) if row[4] else None
            source_id = int(row[5]) if row[5] else None
        except (ValueError, TypeError):
            errors.append(f"Строка {row_idx}: Ошибка в числах (кол-во, цена или ID)")
            continue

        kato_purchase_code = str(row[6]).strip() if row[6] else None
        kato_delivery_code = str(row[7]).strip() if row[7] else None
        agsk_code = str(row[8]).strip() if row[8] else None
        # specs = row[9] 

        # Валидация данных
        enstru = db.query(models.Enstru).filter(models.Enstru.code == trucode).first()
        if not enstru:
            errors.append(f"Строка {row_idx}: Не найден ЕНС ТРУ {trucode}")
            continue

        unit = db.query(models.Mkei).filter(models.Mkei.code == unit_code).first()
        if not unit:
            errors.append(f"Строка {row_idx}: Не найден код ед. изм. {unit_code}")
            continue
            
        if not expense_id or not source_id:
             errors.append(f"Строка {row_idx}: Не указан ID статьи затрат или источника")
             continue

        # Проверка КАТО
        if not kato_purchase_code or not kato_delivery_code:
            errors.append(f"Строка {row_idx}: Не указаны коды КАТО")
            continue

        kato_purchase = db.query(models.Kato).filter(models.Kato.code == kato_purchase_code).first()
        if not kato_purchase:
            errors.append(f"Строка {row_idx}: Не найден КАТО закупки {kato_purchase_code}")
            continue

        kato_delivery = db.query(models.Kato).filter(models.Kato.code == kato_delivery_code).first()
        if not kato_delivery:
            errors.append(f"Строка {row_idx}: Не найден КАТО поставки {kato_delivery_code}")
            continue

        # Проверка АГСК для СМР
        expense_item = db.query(models.Cost_Item).filter(models.Cost_Item.id == expense_id).first()
        if not expense_item:
            errors.append(f"Строка {row_idx}: Не найдена статья затрат {expense_id}")
            continue
            
        if expense_item.name_ru == "СМР" and not agsk_code:
            errors.append(f"Строка {row_idx}: Для статьи затрат 'СМР' обязательно укажите код АГСК")
            continue

        # Создаем объект
        total_amount = quantity * price
        
        # Проверяем КТП
        is_ktp = False
        # Используем правильное поле enstru_code
        reestr_record = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.enstru_code == trucode).first()
        if reestr_record:
            is_ktp = True
            min_dvc = Decimal(str(reestr_record.dvc_percent)) if reestr_record.dvc_percent is not None else 0
        else:
            min_dvc = 0

        new_item = models.PlanItemVersion(
            version_id=active_version.id,
            item_number=next_item_number,
            need_type=models.NeedType(enstru.type_ru),
            trucode=trucode,
            unit_id=unit.id,
            expense_item_id=expense_id,
            funding_source_id=source_id,
            agsk_id=agsk_code,
            kato_purchase_id=kato_purchase.id,
            kato_delivery_id=kato_delivery.id,
            quantity=quantity,
            price_per_unit=price,
            total_amount=total_amount,
            is_ktp=is_ktp,
            is_resident=False,
            is_deleted=False,
            root_item_id=None, # Будет установлен после flush
            source_version_id=active_version.id,
            revision_number=0,
            min_dvc_percent=min_dvc
        )
        
        new_items.append(new_item)
        next_item_number += 1

    if errors:
        raise HTTPException(status_code=400, detail={"message": "Ошибки в файле", "errors": errors[:10]})

    if not new_items:
        raise HTTPException(status_code=400, detail="Файл пуст или не содержит корректных данных")

    # Сохраняем
    db.add_all(new_items)
    db.flush()
    
    # Проставляем root_item_id для новых записей
    for item in new_items:
        item.root_item_id = item.id
    
    db.commit()
    
    # Пересчитываем итоги
    plan_service._recalculate_version_metrics(db, active_version.id)
    
    return {"message": f"Успешно импортировано {len(new_items)} позиций"}
