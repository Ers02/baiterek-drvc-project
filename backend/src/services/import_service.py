import io
import os
import uuid
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, JSONResponse
from ..models import models
from ..services import plan_service
from .exporters.excel_generator import generate_import_template, generate_error_report
from .importers.excel_importer import import_items_from_excel
from .importers.kenml_parser import parse_kenml_file
from ..utils.helpers import is_smr
from ..core.config import settings
from ..database.database import SessionLocal
from ..core.logger import logger

# Экспортируем функции генерации, чтобы роутер их видел
__all__ = ['generate_import_template', 'process_import_file', 'process_kenml_import', 'process_import_background']

def save_error_report(errors: list, filename: str):
    """Сохраняет отчет об ошибках на диск."""
    if not os.path.exists(settings.REPORT_DIR):
        os.makedirs(settings.REPORT_DIR)
    
    content = generate_error_report(errors)
    path = os.path.join(settings.REPORT_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    return path

def background_import_task(plan_id: int, file_content: bytes, user_id: int):
    """
    Фоновая задача импорта.
    Создает свою сессию БД, так как основная уже закрыта.
    """
    logger.info(f"Starting background import for plan {plan_id} by user {user_id}")
    db = SessionLocal()
    try:
        # Получаем пользователя и план заново
        user = db.query(models.User).filter(models.User.id == user_id).first()
        active_version = plan_service._get_active_version(db, plan_id)
        
        if not active_version or not user:
            logger.error(f"Import failed: Plan {plan_id} or User {user_id} not found")
            return

        # Логика импорта
        new_items, errors = import_items_from_excel(db, active_version.id, file_content)

        if errors:
            # Сохраняем отчет об ошибках
            report_name = f"import_errors_{plan_id}_{uuid.uuid4()}.xlsx"
            save_error_report(errors, report_name)
            logger.warning(f"Import finished with errors. Report saved to {report_name}")
            # Можно отправить уведомление пользователю (WebSocket/Email)
            return

        if not new_items:
            logger.info("Import finished: No items found")
            return

        try:
            db.add_all(new_items)
            db.flush()
            
            for item in new_items:
                item.root_item_id = item.id
            
            plan_service._recalculate_version_metrics(db, active_version.id)
            # commit происходит внутри recalculate
            logger.info(f"Import success: {len(new_items)} items added")
            
        except Exception as e:
            db.rollback()
            logger.error(f"Import DB error: {str(e)}")
            
    except Exception as e:
        logger.error(f"Background task error: {str(e)}")
    finally:
        db.close()

def process_import_file(db: Session, plan_id: int, file: UploadFile, user: models.User, background_tasks: BackgroundTasks):
    """
    Запускает импорт в фоне.
    """
    active_version = plan_service._get_active_version(db, plan_id)
    if not active_version:
        raise HTTPException(status_code=404, detail="Активная версия плана не найдена")
    
    if active_version.status != models.PlanStatus.DRAFT:
        raise HTTPException(status_code=403, detail="Импорт возможен только в черновик")
    
    if active_version.plan.created_by != user.id:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование этого плана")

    try:
        contents = file.file.read()
    except Exception as e:
        logger.error(f"Error reading file upload: {e}")
        raise HTTPException(status_code=400, detail="Ошибка чтения файла")

    # Запускаем фоновую задачу
    background_tasks.add_task(background_import_task, plan_id, contents, user.id)
    
    return JSONResponse(content={"message": "Файл принят в обработку. Результат появится позже."})


def process_kenml_import(db: Session, file: UploadFile):
    """
    Парсит KENML/ZIP, агрегирует данные и генерирует Excel-шаблон.
    (Оставляем синхронным, так как пользователь ждет файл сразу)
    """
    try:
        all_data = parse_kenml_file(file)
    except Exception as e:
        logger.error(f"KENML parse error: {e}")
        raise

    # Фильтрация и агрегация
    goods = {}
    works_services = {}
    
    for row in all_data:
        if row['Сумма'] <= 0.01: continue
        
        cat = row['Категория']
        name = row['Наименование']
        code = row['КодСНБ']
        unit = row['Ед. изм.']
        vol = row['Объем']
        total = row['Сумма']
        
        if cat == 'Товары':
            key = (cat, name, code, unit)
            if key not in goods:
                goods[key] = {'vol': 0.0, 'total': 0.0}
            goods[key]['vol'] += vol
            goods[key]['total'] += total
        else:
            key = (cat, name, code)
            if key not in works_services:
                works_services[key] = {'total': 0.0}
            works_services[key]['total'] += total

    final_rows = []
    
    for key, val in goods.items():
        cat, name, code, unit = key
        vol = val['vol']
        total = val['total']
        price = total / vol if vol else 0
        final_rows.append({'cat': cat, 'name': name, 'code_agsk': code, 'unit': unit, 'vol': vol, 'price': price, 'total': total})
        
    for key, val in works_services.items():
        cat, name, code = key
        total = val['total']
        final_rows.append({'cat': cat, 'name': name, 'code_agsk': code, 'unit': '', 'vol': 1.0, 'price': total, 'total': total})
        
    final_rows.sort(key=lambda x: x['total'], reverse=True)
    
    # Поиск ЕНС ТРУ по АГСК
    agsk_codes = set(r['code_agsk'] for r in final_rows if r['code_agsk'] and r['code_agsk'] != "БЕЗ_КОДА")
    agsk_to_enstru = {}
    if agsk_codes:
        records = db.query(models.Reestr_KTP.agsk3_code, models.Reestr_KTP.enstru_code).filter(
            models.Reestr_KTP.agsk3_code.in_(agsk_codes)
        ).all()
        for agsk, enstru in records:
            if agsk and enstru: agsk_to_enstru[agsk] = enstru

    # Получение наименований и ВЦ
    enstru_codes = set(agsk_to_enstru.values())
    enstru_names = {}
    enstru_dvc = {}
    
    if enstru_codes:
        for code, name in db.query(models.Enstru.code, models.Enstru.name_rus).filter(models.Enstru.code.in_(enstru_codes)).all():
            enstru_names[code] = name
            
        from sqlalchemy import func
        dvc_records = db.query(models.Reestr_KTP.enstru_code, func.max(models.Reestr_KTP.dvc_percent)).filter(
            models.Reestr_KTP.enstru_code.in_(enstru_codes)
        ).group_by(models.Reestr_KTP.enstru_code).all()
        for code, dvc in dvc_records:
            enstru_dvc[code] = dvc

    # Генерация Excel
    import openpyxl
    template_bytes = generate_import_template(db)
    wb = openpyxl.load_workbook(io.BytesIO(template_bytes))
    ws = wb["Позиции для загрузки"]
    
    smr_cost_item = db.query(models.Cost_Item).filter(models.Cost_Item.id == settings.SMR_COST_ITEM_ID).first()
    smr_str = f"{smr_cost_item.id} - {smr_cost_item.name_ru}" if smr_cost_item else ""

    for idx, row in enumerate(final_rows, start=1):
        excel_row = idx + 1
        enstru_code = agsk_to_enstru.get(row['code_agsk'], "")
        
        ws.cell(row=excel_row, column=1, value=idx)
        ws.cell(row=excel_row, column=2, value=enstru_code)
        ws.cell(row=excel_row, column=3, value=enstru_names.get(enstru_code, ""))
        ws.cell(row=excel_row, column=4, value=row['name'])
        ws.cell(row=excel_row, column=5, value=row['name'])
        ws.cell(row=excel_row, column=6, value=row['unit'])
        ws.cell(row=excel_row, column=7, value=row['vol'])
        ws.cell(row=excel_row, column=8, value=row['price'])
        ws.cell(row=excel_row, column=9, value=row['total'])
        
        if smr_str: ws.cell(row=excel_row, column=12, value=smr_str)
        
        ws.cell(row=excel_row, column=14, value=row['code_agsk'])
        
        dvc_percent = enstru_dvc.get(enstru_code)
        if dvc_percent is not None:
             ws.cell(row=excel_row, column=15, value=dvc_percent)
             vc_amount = row['total'] * (float(dvc_percent) / 100.0)
             ws.cell(row=excel_row, column=17, value=vc_amount)
        
    virtual_workbook = io.BytesIO()
    wb.save(virtual_workbook)
    return virtual_workbook.getvalue()
