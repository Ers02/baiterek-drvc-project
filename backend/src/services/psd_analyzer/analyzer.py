import io
import re
from sqlalchemy.orm import Session
from ...database.database import SessionLocal
from ...models import models
from ...core.logger import logger
from ..importers.kenml_parser import parse_kenml_file
from .matching import Matcher
from .excel_exporter import ExcelExporter
from ...utils.text_utils import clean_product_name, is_non_product, has_letters

class PSDAnalyzer:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.db = SessionLocal()
        self.items = []

    def _update_status(self, status: str, message: str = None,
                       result_file: str = None, error: str = None):
        try:
            task = self.db.query(models.AdminTask).filter(
                models.AdminTask.id == self.task_id
            ).first()
            if task:
                task.status = status
                if message:
                    task.message = message
                if result_file:
                    task.result_file = result_file
                if error:
                    task.error_details = error
                self.db.commit()
        except Exception as e:
            logger.error(f"Failed to update task {self.task_id}: {e}")

    def _parse(self, file_content: bytes):
        class MockFile:
            def __init__(self, content):
                self.file = io.BytesIO(content)
                self.filename = "upload.zip"

        return parse_kenml_file(MockFile(file_content))

    def _aggregate(self, rows: list):
        unique_items = {}

        for row in rows:
            try:
                amount = float(row.get('Сумма', 0))
                if amount <= 0.01:
                    continue
            except (ValueError, TypeError):
                continue

            name = str(row.get('Наименование', '')).strip()
            code_agsk = str(row.get('КодСНБ', '')).strip()

            category = row.get('Категория', '')
            if category != 'Товары' or is_non_product(name):
                skip_search = True
            else:
                skip_search = has_letters(code_agsk)

            key = (name, code_agsk)
            if key not in unique_items:
                unique_items[key] = {
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
                    "skip_search": skip_search,
                }

            try:
                unique_items[key]['vol'] += float(row.get('Объем', 0))
                unique_items[key]['total'] += amount
            except (ValueError, TypeError):
                pass

        items_list = list(unique_items.values())
        items_list.sort(key=lambda x: x['total'], reverse=True)
        return items_list

    def run(self, file_content: bytes):
        logger.info(f"Analyzer started for task {self.task_id}")
        self._update_status("processing", "Инициализация...")

        try:
            self._update_status("processing", "Парсинг файла...")
            rows = self._parse(file_content)

            self._update_status("processing", f"Агрегация ({len(rows)} строк)...")
            self.items = self._aggregate(rows)

            matcher = Matcher(self.db)

            self._update_status("processing", "Поиск по АГСК...")
            matcher.match_by_agsk(self.items)

            self._update_status("processing", "Интеллектуальный поиск...")
            matcher.fuzzy_match_names(
                self.items,
                lambda i, t: self._update_status(
                    "processing", f"Умный поиск: {i}/{t}..."
                )
            )

            self._update_status("processing", "Сбор поставщиков...")
            matcher.load_suppliers(self.items)

            self._update_status("processing", "Генерация Excel...")
            exporter = ExcelExporter(self.items)
            filename = exporter.generate(self.task_id)

            self._update_status("completed", "Готово!", result_file=filename)
            logger.info(f"Analyzer finished for task {self.task_id}")

        except Exception as e:
            logger.error(f"Analyzer failed: {e}", exc_info=True)
            self._update_status("error", f"Ошибка: {str(e)}", error=str(e))
        finally:
            self.db.close()
