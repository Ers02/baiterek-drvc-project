import io
import os
import uuid
import re
import openpyxl
import pandas as pd
import json
from datetime import datetime
from collections import defaultdict
from fastapi import UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from functools import lru_cache

from ..models import models
from .importers.kenml_parser import parse_kenml_file
from ..core.config import settings
from ..database.database import SessionLocal
from ..core.logger import logger
from ..utils.text_utils import clean_product_name, HAS_LETTERS_RE

# --- Helper Functions ---
ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010]|[\013-\014]|[\016-\037]')

def clean_text_for_excel(text, max_len=32000):
    if text is None: return ""
    text = str(text)
    text = ILLEGAL_CHARACTERS_RE.sub("", text)
    return text[:max_len] if len(text) > max_len else text

def update_task_status(task_id: str, status: str, message: str = None, result_file: str = None, error: str = None):
    db = SessionLocal()
    try:
        task = db.query(models.AdminTask).filter(models.AdminTask.id == task_id).first()
        if task:
            task.status, task.message, task.result_file, task.error_details = status, message, result_file, error
            db.commit()
    finally:
        db.close()

# --- Main Analysis Logic ---
def background_analyze_psd(task_id: str, file_content: bytes, filename: str):
    logger.info(f"Admin Task {task_id}: Starting analysis for file '{filename}'")
    update_task_status(task_id, "processing", "Инициализация...")
    
    db = SessionLocal()
    try:
        # --- 1. Parse Input File ---
        update_task_status(task_id, "processing", "Парсинг файла ПСД...")
        class MockFile:
            def __init__(self, content, name):
                self.file = io.BytesIO(content)
                self.filename = name
        try:
            all_data = parse_kenml_file(MockFile(file_content, filename))
        except Exception as e:
            raise Exception(f"Ошибка чтения KENML: {e}")

        # --- 2. Aggregate and Filter Data ---
        update_task_status(task_id, "processing", "Фильтрация и агрегация данных...")
        items_to_process, items_to_ignore = [], []
        unique_items_map = {}
        for row in all_data:
            try:
                amount = float(row.get('Сумма', 0))
                if amount <= 0.01: continue
            except (ValueError, TypeError): continue
            
            name, code_agsk = str(row.get('Наименование', '')).strip(), str(row.get('КодСНБ', '')).strip()
            key = (name, code_agsk)

            if key not in unique_items_map:
                item_data = {
                    "name": name, 
                    "agsk": code_agsk, 
                    "clean_name": clean_product_name(name), 
                    "unit": str(row.get('Ед. изм.', '')), 
                    "vol": 0.0, 
                    "total": 0.0, 
                    "found_enstru": None, 
                    "found_name": None, 
                    "similarity": None, 
                    "suppliers": [], 
                    "found_agsk_ktp": None, 
                    "found_enstru_name_ktp": None, 
                    "agsk_ref_name": None
                }
                unique_items_map[key] = item_data
                
                # Используем HAS_LETTERS_RE из text_utils
                if bool(HAS_LETTERS_RE.search(code_agsk)) or row.get('Категория') != 'Товары':
                    items_to_ignore.append(item_data)
                else:
                    items_to_process.append(item_data)
            
            try:
                unique_items_map[key]['vol'] += float(row.get('Объем', 0))
                unique_items_map[key]['total'] += amount
            except (ValueError, TypeError): pass
            
        # --- 3. Pre-fetch AGSK reference names ---
        all_agsk_codes = {item['agsk'] for item in items_to_process if item['agsk']}
        agsk_ref_map = {}
        if all_agsk_codes:
            agsk_refs = db.query(models.Agsk.code, models.Agsk.name_ru).filter(models.Agsk.code.in_(all_agsk_codes)).all()
            agsk_ref_map = {code: name for code, name in agsk_refs}
        
        for item in items_to_process:
            item['agsk_ref_name'] = agsk_ref_map.get(item['agsk'])

        # --- 4. Simplified Cascade Search ---
        if items_to_process:
            # Stage 1: Exact AGSK match
            update_task_status(task_id, "processing", "Этап 1: Точный поиск по АГСК...")
            for item in items_to_process:
                if item['found_enstru'] or not item['agsk']: continue
                res = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.agsk3_codes.op('?')(item['agsk'])).first()
                if res and res.enstru_codes:
                    item.update({
                        'found_enstru': res.enstru_codes[0], 
                        'found_name': res.product_name, 
                        'similarity': 100, 
                        'found_agsk_ktp': res.agsk3_codes, 
                        'found_enstru_name_ktp': res.enstru_names
                    })

            # Stage 2: Parent AGSK match (first 7 chars)
            update_task_status(task_id, "processing", "Этап 2: Поиск по родительскому АГСК...")
            for item in items_to_process:
                if item['found_enstru'] or not item['agsk'] or len(item['agsk']) < 7: continue
                parent_agsk = item['agsk'][:7]
                res = db.query(models.Reestr_KTP).filter(text("EXISTS (SELECT 1 FROM jsonb_array_elements_text(agsk3_codes) as code WHERE code LIKE :pattern)")).params(pattern=f"{parent_agsk}%").first()
                if res and res.enstru_codes:
                    item.update({
                        'found_enstru': res.enstru_codes[0], 
                        'found_name': res.product_name, 
                        'similarity': 95, 
                        'found_agsk_ktp': res.agsk3_codes, 
                        'found_enstru_name_ktp': res.enstru_names
                    })

        # --- 5. Gather Suppliers ---
        update_task_status(task_id, "processing", "Сбор данных о поставщиках...")
        found_enstru_codes = {item['found_enstru'] for item in items_to_process if item['found_enstru'] and item['found_enstru'] != 'NOT_FOUND'}
        suppliers_map = defaultdict(list)
        if found_enstru_codes:
            supplier_records = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.enstru_codes.isnot(None)).all()
            for s in supplier_records:
                if s.enstru_codes:
                    common_codes = set(s.enstru_codes).intersection(found_enstru_codes)
                    if common_codes:
                        info = f"{s.company_name or ''} (БИН: {s.bin_iin or ''}), Адр: {s.production_address or ''}, Тел: {s.phone or ''}"
                        for code in common_codes:
                            suppliers_map[code].append(info)
        for item in items_to_process:
            if item['found_enstru']:
                item['suppliers'] = suppliers_map.get(item['found_enstru'], [])

        # --- 6. Generate Excel Report ---
        update_task_status(task_id, "processing", "Создание отчета Excel...")
        final_items_list = items_to_process + items_to_ignore
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Анализ ПСД"
        headers = ["№", "Код ЕНС ТРУ", "Наименование (Смета)", "Наименование (Реестр КТП)", "Ед. изм.", "Кол-во", "Цена", "Сумма", "Код АГСК (ПСД)", "Наименование АГСК (Справочник)", "Схожесть (%)", "Поставщики (Реестр КТП)", "АГСК из Реестра КТП", "Наименование ЕНС ТРУ (Реестр КТП)"]
        ws.append(headers)
        for idx, item in enumerate(final_items_list, 1):
            price = item['total'] / item['vol'] if item['vol'] else 0
            suppliers_str = "[Не является товаром, исключено из поиска]" if item in items_to_ignore else ";\n".join(item['suppliers'][:10])
            if item not in items_to_ignore and len(item['suppliers']) > 10:
                suppliers_str += f"\n... и еще {len(item['suppliers']) - 10}"
            ws.append([
                idx, 
                clean_text_for_excel(item['found_enstru']), 
                clean_text_for_excel(item['name']), 
                clean_text_for_excel(item['found_name']), 
                clean_text_for_excel(item['unit']), 
                item['vol'], 
                price, 
                item['total'], 
                clean_text_for_excel(item['agsk']), 
                clean_text_for_excel(item.get('agsk_ref_name')), 
                item['similarity'], 
                clean_text_for_excel(suppliers_str), 
                json.dumps(item.get('found_agsk_ktp'), ensure_ascii=False), 
                json.dumps(item.get('found_enstru_name_ktp'), ensure_ascii=False)
            ])
        
        filename = f"analysis_{task_id}.xlsx"
        path = os.path.join(settings.REPORT_DIR, filename)
        wb.save(path)
        
        update_task_status(task_id, "completed", "Готово!", result_file=filename)
        logger.info(f"Admin Task {task_id}: Completed successfully")

    except Exception as e:
        logger.error(f"Admin Task {task_id} failed: {e}", exc_info=True)
        update_task_status(task_id, "error", f"Ошибка: {str(e)}", error=str(e))
    finally:
        db.close()

def start_admin_analysis(file: UploadFile, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    try:
        content, filename = file.file.read(), file.filename
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения: {e}")
    db = SessionLocal()
    try:
        task = models.AdminTask(id=task_id, status="pending", message="Файл в очереди...")
        db.add(task)
        db.commit()
    finally:
        db.close()
    background_tasks.add_task(background_analyze_psd, task_id, content, filename)
    return {"task_id": task_id, "message": "Анализ запущен"}

def get_admin_task_status(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(models.AdminTask).filter(models.AdminTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Задача не найдена")
        return {"status": task.status, "message": task.message, "error": task.error_details}
    finally:
        db.close()

def get_admin_task_result(task_id: str):
    db = SessionLocal()
    try:
        task = db.query(models.AdminTask).filter(models.AdminTask.id == task_id).first()
        if not task or task.status != "completed":
            raise HTTPException(status_code=400, detail="Результат не готов")
        path = os.path.join(settings.REPORT_DIR, task.result_file)
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Файл удален")
        return FileResponse(path, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', filename="analysis_result.xlsx")
    finally:
        db.close()

async def upload_estimate_template(db: Session, file: UploadFile):
    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        file_path = os.path.join(settings.UPLOAD_DIR, f"latest_estimate_template.xlsx")
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        logger.info(f"Estimate template saved to '{file_path}'")
        return {"message": "Шаблон успешно загружен"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке шаблона: {e}")

def get_estimate_analysis(db: Session):
    try:
        latest_file = os.path.join(settings.UPLOAD_DIR, "latest_estimate_template.xlsx")
        if not os.path.exists(latest_file):
            raise HTTPException(status_code=404, detail="Шаблон сметы не найден.")
        df = pd.read_excel(latest_file, sheet_name="Позиции для загрузки")
        amount_col, category_col, funding_col, lc_share_col = "Сумма планируемая для закупок ТРУ без НДС, тенге", "Статья затрат", "Источник финансирования", "Доля внутристрановой ценности (%)"
        required_cols = [amount_col, category_col, funding_col, lc_share_col]
        if not all(col in df.columns for col in required_cols):
            raise HTTPException(status_code=400, detail=f"Отсутствуют необходимые столбцы в Excel.")
        df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce')
        df[lc_share_col] = pd.to_numeric(df[lc_share_col], errors='coerce')
        df.dropna(subset=[amount_col], inplace=True)
        df[category_col], df[funding_col], df[lc_share_col] = df[category_col].fillna('Не указано').astype(str), df[funding_col].fillna('Не указано').astype(str), df[lc_share_col].fillna(0)
        total_amount, amount_with_lc = df[amount_col].sum(), df[df[lc_share_col] > 0][amount_col].sum()
        cost_item_summary, funding_summary = df.groupby(category_col)[amount_col].sum().nlargest(10), df.groupby(funding_col)[amount_col].sum()
        return {
            "summary": {
                "totalAmount": f"{total_amount:,.2f} KZT", 
                "itemCount": len(df), 
                "localContentPercentage": f"{(amount_with_lc / total_amount * 100) if total_amount > 0 else 0:.2f}%", 
                "uniqueCategories": df[category_col].nunique()
            }, 
            "costItemAnalysis": {
                "chartData": {
                    "labels": cost_item_summary.index.tolist(), 
                    "datasets": [{"label": 'Сумма по статьям', "data": cost_item_summary.values.tolist()}]
                }
            }, 
            "localContentAnalysis": {
                "chartData": {
                    "labels": ['С долей ВЦ', 'Без доли ВЦ'], 
                    "datasets": [{"data": [amount_with_lc, total_amount - amount_with_lc]}]
                }
            }, 
            "fundingSourceAnalysis": {
                "chartData": {
                    "labels": funding_summary.index.tolist(), 
                    "datasets": [{"data": funding_summary.values.tolist()}]
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {e}")
