import io
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import UploadFile, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.utils import quote_sheetname
from ..models import models
from ..services import plan_service

def generate_import_template(db: Session) -> bytes:
    """Генерирует Excel-шаблон с отдельными листами для справочников и именованными диапазонами."""
    wb = openpyxl.Workbook()
    
    # Удаляем дефолтный лист, создадим свой
    default_sheet = wb.active
    wb.remove(default_sheet)

    # --- Функция-помощник для создания листа справочника ---
    def create_ref_sheet(sheet_name, data_list, range_name):
        ws = wb.create_sheet(sheet_name)
        ws.sheet_state = 'hidden' # Скрываем лист
        
        # Записываем данные
        for idx, val in enumerate(data_list, start=1):
            ws.cell(row=idx, column=1, value=val)
        
        if data_list:
            # Создаем именованный диапазон (Defined Name)
            # Формат: SheetName!$A$1:$A$100
            quoted_name = quote_sheetname(sheet_name)
            formula = f"{quoted_name}!$A$1:$A${len(data_list)}"
            
            # Создаем объект DefinedName
            d_name = DefinedName(range_name, attr_text=formula)
            wb.defined_names.add(d_name)

    # 1. Подготовка данных для МКЕИ (Оптимизация: выбираем только нужные поля)
    mkeis = db.query(models.Mkei.code, models.Mkei.name_ru).all()
    mkei_data = [f"{code} - {name}" for code, name in mkeis]
    create_ref_sheet("Ref_MKEI", mkei_data, "List_MKEI")

    # 2. Подготовка данных для Статей затрат
    cost_items = db.query(models.Cost_Item.id, models.Cost_Item.name_ru).all()
    cost_data = [f"{id} - {name}" for id, name in cost_items]
    create_ref_sheet("Ref_Cost", cost_data, "List_Cost")

    # 3. Подготовка данных для Источников
    sources = db.query(models.Source_Funding.id, models.Source_Funding.name_ru).all()
    source_data = [f"{id} - {name}" for id, name in sources]
    create_ref_sheet("Ref_Source", source_data, "List_Source")

    # 4. Подготовка данных для КАТО
    katos = db.query(models.Kato.code, models.Kato.name_ru).all()
    kato_data = [f"{code} - {name}" for code, name in katos]
    create_ref_sheet("Ref_KATO", kato_data, "List_KATO")

    # --- Основной лист: Данные для заполнения ---
    ws_data = wb.create_sheet("Позиции для загрузки", 0) # Ставим первым
    
    headers = [
        "№",                                      # A
        "Код по ЕНС ТРУ",                         # B
        "Наименование закупаемых товаров, работ и услуг", # C
        "Дополнительная характеристика (рус)",    # D
        "Дополнительная характеристика (каз)",    # E
        "Единица измерения(МКЕИ) (для товаров)", # F
        "Количество, объем",                      # G
        "Цена за единицу, тенге без НДС",         # H
        "Сумма планируемая для закупок ТРУ без НДС, тенге", # I
        "Место закупки (КАТО)",                   # J
        "Место поставки (КАТО)",                  # K
        "Статья затрат",                          # L
        "Источник финансирования",                # M
        "Код АГСК (для СМР)",                     # N
        "Доля местного содержания (%)",           # O
        "Обоснование нерезидентства"              # P
    ]
    
    # Стилизация заголовков
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1B5E20", end_color="1B5E20", fill_type="solid")
    header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True) # Добавил wrap_text
    
    ws_data.append(headers)
    
    # Увеличиваем высоту первой строки
    ws_data.row_dimensions[1].height = 45

    for cell in ws_data[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment # Применяем выравнивание

    # Настройка ширины колонок
    ws_data.column_dimensions['A'].width = 5
    ws_data.column_dimensions['B'].width = 20
    ws_data.column_dimensions['C'].width = 20
    ws_data.column_dimensions['D'].width = 20
    ws_data.column_dimensions['E'].width = 20
    ws_data.column_dimensions['F'].width = 20
    ws_data.column_dimensions['G'].width = 15
    ws_data.column_dimensions['H'].width = 15
    ws_data.column_dimensions['I'].width = 20
    ws_data.column_dimensions['J'].width = 21
    ws_data.column_dimensions['K'].width = 21
    ws_data.column_dimensions['L'].width = 21
    ws_data.column_dimensions['M'].width = 21
    ws_data.column_dimensions['N'].width = 20
    ws_data.column_dimensions['O'].width = 15
    ws_data.column_dimensions['P'].width = 30

    # --- Настройка Data Validation ---
    data_rows_count = 2000 

    def add_dv(formula_name, col_letter):
        dv = DataValidation(type="list", formula1=f"={formula_name}", allow_blank=True)
        dv.error = 'Выберите значение из списка'
        dv.errorTitle = 'Неверное значение'
        ws_data.add_data_validation(dv)
        dv.add(f'{col_letter}2:{col_letter}{data_rows_count}')

    if mkei_data: add_dv("List_MKEI", "F")
    if kato_data: 
        add_dv("List_KATO", "J")
        add_dv("List_KATO", "K")
    if cost_data: add_dv("List_Cost", "L")
    if source_data: add_dv("List_Source", "M")

    virtual_workbook = io.BytesIO()
    wb.save(virtual_workbook)
    return virtual_workbook.getvalue()


def generate_error_report(errors: list) -> bytes:
    """Генерирует Excel-файл с отчетом об ошибках."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Ошибки импорта"
    
    headers = ["Номер строки", "Описание ошибки"]
    ws.append(headers)
    
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="B71C1C", end_color="B71C1C", fill_type="solid")
    
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        
    for err in errors:
        ws.append([err['row'], err['message']])
        
    ws.column_dimensions['A'].width = 15
    ws.column_dimensions['B'].width = 100
    
    virtual_workbook = io.BytesIO()
    wb.save(virtual_workbook)
    return virtual_workbook.getvalue()


def process_import_file(db: Session, plan_id: int, file: UploadFile, user: models.User):
    """Читает Excel и создает позиции."""
    
    active_version = plan_service._get_active_version(db, plan_id)
    if not active_version:
        raise HTTPException(status_code=404, detail="Активная версия плана не найдена")
    
    if active_version.status != models.PlanStatus.DRAFT:
        raise HTTPException(status_code=403, detail="Импорт возможен только в черновик")
    
    if active_version.plan.created_by != user.id:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование этого плана")

    try:
        contents = file.file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents), data_only=True)
        if "Позиции для загрузки" in wb.sheetnames:
            ws = wb["Позиции для загрузки"]
        else:
            ws = wb.active
    except Exception:
        raise HTTPException(status_code=400, detail="Неверный формат файла. Ожидается .xlsx")

    new_items = []
    errors = []
    
    # Словари для хранения последних номеров по типам
    last_numbers = {
        models.NeedType.GOODS: 0,
        models.NeedType.WORKS: 0,
        models.NeedType.SERVICES: 0
    }
    
    # Инициализируем счетчики из БД
    for need_type in last_numbers.keys():
        last_item = db.query(models.PlanItemVersion).filter(
            models.PlanItemVersion.version_id == active_version.id,
            models.PlanItemVersion.need_type == need_type
        ).order_by(desc(models.PlanItemVersion.item_number)).first()
        if last_item:
            last_numbers[need_type] = last_item.item_number

    def extract_code(val):
        if val is None: return None
        val_str = str(val).strip()
        if not val_str: return None
        if " - " in val_str:
            return val_str.split(" - ")[0].strip()
        return val_str

    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # Проверяем, пустая ли строка
        is_empty = True
        for cell in row:
            if cell is not None and str(cell).strip():
                is_empty = False
                break
        
        if is_empty:
            continue

        # Приводим строку к фиксированной длине (16 колонок)
        row_data = list(row) + [None] * max(0, 16 - len(row))

        trucode_val = row_data[1]
        if not trucode_val or not str(trucode_val).strip():
            errors.append({"row": row_idx, "message": "Не указан код ЕНС ТРУ"})
            continue
        trucode = str(trucode_val).strip()

        # Валидация в БД
        enstru = db.query(models.Enstru).filter(models.Enstru.code == trucode).first()
        if not enstru:
            errors.append({"row": row_idx, "message": f"Не найден ЕНС ТРУ {trucode}"})
            continue

        # Маппинг type_name на NeedType
        type_name_upper = enstru.type_name.upper() if enstru.type_name else 'GOODS'
        need_type_map = {
            'GOOD': models.NeedType.GOODS,
            'GOODS': models.NeedType.GOODS,
            'WORK': models.NeedType.WORKS,
            'WORKS': models.NeedType.WORKS,
            'SERVICE': models.NeedType.SERVICES,
            'SERVICES': models.NeedType.SERVICES
        }
        need_type = need_type_map.get(type_name_upper, models.NeedType.GOODS)

        specs_val = row_data[3]
        if not specs_val or not str(specs_val).strip():
             errors.append({"row": row_idx, "message": "Доп. характеристика (рус) обязательна"})
             continue
        additional_specs = str(specs_val).strip()
        
        specs_kz_val = row_data[4]
        if not specs_kz_val or not str(specs_kz_val).strip():
             errors.append({"row": row_idx, "message": "Доп. характеристика (каз) обязательна"})
             continue
        additional_specs_kz = str(specs_kz_val).strip()

        unit_id = None
        if need_type == models.NeedType.GOODS:
            unit_code = extract_code(row_data[5])
            if not unit_code:
                errors.append({"row": row_idx, "message": "Не указан код ед. изм. (обязательно для товаров)"})
                continue
            unit = db.query(models.Mkei).filter(models.Mkei.code == unit_code).first()
            if not unit:
                errors.append({"row": row_idx, "message": f"Не найден код ед. изм. {unit_code}"})
                continue
            unit_id = unit.id

        qty_val = row_data[6]
        price_val = row_data[7]
        
        if qty_val is None:
             errors.append({"row": row_idx, "message": "Не указано количество"})
             continue
        if price_val is None:
             errors.append({"row": row_idx, "message": "Не указана цена"})
             continue

        try:
            quantity = Decimal(str(qty_val))
            price = Decimal(str(price_val))
        except Exception:
             errors.append({"row": row_idx, "message": "Некорректный формат числа (кол-во или цена)"})
             continue
            
        if quantity <= 0:
             errors.append({"row": row_idx, "message": "Количество должно быть больше 0"})
             continue
             
        if price < 0:
             errors.append({"row": row_idx, "message": "Цена не может быть отрицательной"})
             continue

        kato_p_code = extract_code(row_data[9])
        kato_d_code = extract_code(row_data[10])
        
        if not kato_p_code or not kato_d_code:
             errors.append({"row": row_idx, "message": "Не указаны коды КАТО"})
             continue

        expense_code = extract_code(row_data[11])
        source_code = extract_code(row_data[12])
        
        if not expense_code or not source_code:
             errors.append({"row": row_idx, "message": "Не указана статья затрат или источник"})
             continue

        try:
            expense_id = int(expense_code)
            source_id = int(source_code)
        except ValueError:
            errors.append({"row": row_idx, "message": "ID статьи или источника должен быть числом"})
            continue

        agsk_code_from_file = str(row_data[13]).strip() if (row_data[13] and str(row_data[13]).strip()) else None
        agsk_code = None

        if agsk_code_from_file:
            if agsk_code_from_file.lower() == "прайс-лист":
                agsk_code = None
            else:
                agsk_exists = db.query(models.Agsk).filter(models.Agsk.code == agsk_code_from_file).first()
                if not agsk_exists:
                    errors.append({"row": row_idx, "message": f"Код АГСК '{agsk_code_from_file}' не найден в базе данных."})
                    continue
                agsk_code = agsk_code_from_file

        kato_purchase = db.query(models.Kato).filter(models.Kato.code == kato_p_code).first()
        if not kato_purchase:
            errors.append({"row": row_idx, "message": f"Не найден КАТО закупки {kato_p_code}"})
            continue

        kato_delivery = db.query(models.Kato).filter(models.Kato.code == kato_d_code).first()
        if not kato_delivery:
            errors.append({"row": row_idx, "message": f"Не найден КАТО поставки {kato_d_code}"})
            continue

        expense_item = db.query(models.Cost_Item).filter(models.Cost_Item.id == expense_id).first()
        if not expense_item:
            errors.append({"row": row_idx, "message": f"Не найдена статья затрат {expense_id}"})
            continue
            
        if "смр" in expense_item.name_ru.lower() and agsk_code is None and (not agsk_code_from_file or agsk_code_from_file.lower() != "прайс-лист"):
            errors.append({"row": row_idx, "message": "Для статьи затрат 'СМР' обязательно укажите код АГСК или 'Прайс-лист'"})
            continue

        # Обработка доли местного содержания
        resident_share_val = row_data[14]
        non_resident_reason = str(row_data[15]).strip() if row_data[15] else None
        
        resident_share = Decimal(100)
        
        if need_type == models.NeedType.GOODS:
            resident_share = Decimal(100)
            non_resident_reason = None # Для товаров всегда 100% и нет обоснования
        else:
            if resident_share_val is not None:
                try:
                    resident_share = Decimal(str(resident_share_val))
                except:
                    errors.append({"row": row_idx, "message": "Некорректный формат доли местного содержания"})
                    continue
                
                if resident_share < 0 or resident_share > 100:
                    errors.append({"row": row_idx, "message": "Доля местного содержания должна быть от 0 до 100"})
                    continue
                
                if resident_share < 100 and not non_resident_reason:
                    errors.append({"row": row_idx, "message": "Обоснование нерезидентства обязательно, если доля < 100%"})
                    continue
            else:
                resident_share = Decimal(100) # По умолчанию 100

        total_amount = quantity * price
        
        is_ktp = False
        min_dvc = Decimal(0)
        
        if need_type == models.NeedType.GOODS:
            reestr_record = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.enstru_code == trucode).first()
            if reestr_record:
                is_ktp = True
                min_dvc = Decimal(str(reestr_record.dvc_percent)) if reestr_record.dvc_percent is not None else 0
        else:
            # Для работ и услуг min_dvc равен resident_share
            min_dvc = resident_share

        # Увеличиваем счетчик для соответствующего типа
        last_numbers[need_type] += 1
        item_number = last_numbers[need_type]

        new_item = models.PlanItemVersion(
            version_id=active_version.id,
            item_number=item_number,
            need_type=need_type,
            trucode=trucode,
            unit_id=unit_id,
            expense_item_id=expense_id,
            funding_source_id=source_id,
            agsk_id=agsk_code,
            kato_purchase_id=kato_purchase.id,
            kato_delivery_id=kato_delivery.id,
            additional_specs=additional_specs,
            additional_specs_kz=additional_specs_kz,
            quantity=quantity,
            price_per_unit=price,
            total_amount=total_amount,
            is_ktp=is_ktp,
            is_deleted=False,
            root_item_id=None,
            source_version_id=active_version.id,
            revision_number=0,
            min_dvc_percent=min_dvc,
            resident_share=resident_share,
            non_resident_reason=non_resident_reason
        )
        
        new_items.append(new_item)

    if errors:
        error_file = generate_error_report(errors)
        return StreamingResponse(
            io.BytesIO(error_file),
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': 'attachment; filename="import_errors.xlsx"'}
        )

    if not new_items:
        raise HTTPException(status_code=400, detail="Файл пуст или не содержит корректных данных")

    db.add_all(new_items)
    db.flush()
    
    for item in new_items:
        item.root_item_id = item.id
    
    db.commit()
    
    plan_service._recalculate_version_metrics(db, active_version.id)
    
    return JSONResponse(content={"message": f"Успешно импортировано {len(new_items)} позиций"})
