"""Главный сервис ПСД — оркестрация документов + общие DVC-helpers.

Класс PsdAnalystService собирается из доменных миксинов:
    - PsdSearchMixin   — поиск в реестре КТП + авто-сопоставление АГСК→ЕНСТРУ
    - PsdItemsMixin    — позиции документа + выборы поставщиков
    - PsdLibraryMixin  — библиотека АГСК→ЕНСТРУ (approve/reject менеджером)
    - PsdParserMixin   — парсинг XML/Excel-смет
    - PsdExportMixin   — экспорт в Excel/DOCX

Внешний API сервиса остаётся прежним: роутер вызывает `psd_service.<method>(...)`
без изменений — метод найдётся через MRO в соответствующем миксине.
"""
import os
import re
import uuid
import zipfile
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, Optional

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session

from ..models.models import ExternalDocument, Reestr_KTP, User
from .psd_export_service import PsdExportMixin
from .psd_items_service import PsdItemsMixin
from .psd_library_service import PsdLibraryMixin
from .psd_parser_service import PsdParserMixin
from .psd_search_service import PsdSearchMixin, SearchMode  # noqa: F401 (re-export)


class PsdAnalystService(
    PsdSearchMixin,
    PsdItemsMixin,
    PsdLibraryMixin,
    PsdParserMixin,
    PsdExportMixin,
):
    # ── Общие helpers (используются миксинами через self.) ──────────────────

    @staticmethod
    def _build_dvc_maps(db: Session, agsk_codes: list, enstru_codes: list):
        """Bulk-build DVC lookup maps.
        Returns (direct_ktp_map, group_ktp_map, suppliers_map, agsk_all_map).

        direct_ktp_map  — Dict[agsk_code, Reestr_KTP]        первый найденный КТП per АГСК
        group_ktp_map   — Dict[agsk_code, Reestr_KTP]        КТП по родительскому АГСК
        suppliers_map   — Dict[enstru_code, list[Reestr_KTP]] все КТП по ЕНСТРУ
        agsk_all_map    — Dict[agsk_code, list[Reestr_KTP]]   ВСЕ КТП с точным совпадением АГСК

        Все запросы учитывают только активных поставщиков (is_active IS NOT FALSE).
        """
        # is_active IS NOT FALSE — включает TRUE и NULL (NULL = ещё не проставлен, считаем активным)
        _active = Reestr_KTP.is_active.isnot(False)

        suppliers_map: Dict[str, list] = {}
        for code in enstru_codes:
            suppliers_map[code] = db.query(Reestr_KTP).filter(
                _active,
                Reestr_KTP.enstru_codes.contains([code])
            ).all()

        direct_ktp_map: Dict[str, Any] = {}
        group_ktp_map: Dict[str, Any] = {}
        agsk_all_map: Dict[str, list] = {}   # ВСЕ активные поставщики per АГСК
        if agsk_codes:
            agsk_set = set(agsk_codes)
            ktp_bulk = db.query(Reestr_KTP).filter(
                _active,
                or_(*[Reestr_KTP.agsk3_codes.contains([c]) for c in agsk_codes])
            ).order_by(Reestr_KTP.id).all()
            for ktp in ktp_bulk:
                for ac in (ktp.agsk3_codes or []):
                    if ac in agsk_set:
                        if ac not in direct_ktp_map:
                            direct_ktp_map[ac] = ktp
                        agsk_all_map.setdefault(ac, []).append(ktp)
            missing = [c for c in agsk_codes if c not in direct_ktp_map and len(c) >= 10]
            seen_parents: set = set()
            for code in missing:
                parent = code[:10]
                if parent in seen_parents:
                    continue
                seen_parents.add(parent)
                rg = db.query(Reestr_KTP).filter(
                    _active,
                    text("EXISTS (SELECT 1 FROM jsonb_array_elements_text(agsk3_codes) AS elem WHERE elem LIKE :prefix)")
                ).params(prefix=f"{parent}%").order_by(Reestr_KTP.id).first()
                if rg:
                    for c2 in missing:
                        if c2[:10] == parent:
                            group_ktp_map[c2] = rg

        return direct_ktp_map, group_ktp_map, suppliers_map, agsk_all_map

    @staticmethod
    def _calc_min_dvc(item, direct_ktp_map, group_ktp_map, suppliers_map,
                      agsk_all_map: Optional[Dict] = None,
                      selections_by_item: Optional[Dict] = None) -> Decimal:
        """Return minimum DVC% for a PsdDocumentItem.

        ВЦ% строго согласован с колонкой «КТП» листа 1 — считается ТОЛЬКО для
        реально сопоставленных позиций:
          • работы/услуги           → 100% (по типу);
          • выбор аналитика          → минимум ДВС среди выбранных поставщиков;
          • авто (АГСК прямо в КТП)  → минимум ДВС поставщиков с этим АГСК;
          • подсказка / нет совпадения (suggested/none) → 0 (КТП = Нет).

        Параметры direct_ktp_map/group_ktp_map/suppliers_map больше не участвуют
        в расчёте (оставлены для совместимости сигнатуры).
        """
        itype = item.item_type or 'GOODS'
        if itype in ('WORKS', 'SERVICES'):
            return Decimal('100')

        is_auto = getattr(item, 'match_type', None) == 'auto_ktp'
        all_vals = []

        # Выборы аналитика — берём для ЛЮБОГО типа сопоставления
        if selections_by_item and selections_by_item.get(item.id):
            for s in selections_by_item[item.id]:
                if s.dvc_percent and float(s.dvc_percent) > 0:
                    all_vals.append(float(s.dvc_percent))

        # Авто-позиции: добавляем КТП-значения к уже собранным выборам аналитика
        if is_auto and agsk_all_map is not None and item.code_sn:
            for ktp_r in agsk_all_map.get(item.code_sn, []):
                if ktp_r.dvc_percent:
                    try:
                        v = float(re.sub(r'[^0-9.]', '', str(ktp_r.dvc_percent)).replace(',', '.'))
                        if v > 0:
                            all_vals.append(v)
                    except Exception:
                        pass

        # Для не-авто позиций без выборов → КТП = Нет → ВЦ = 0
        if not all_vals:
            return Decimal('0')
        return Decimal(str(min(all_vals)))

    @staticmethod
    def _calculate_deadline(start_date: datetime, business_days: int) -> datetime:
        current_date = start_date
        added_days = 0
        while added_days < business_days:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:
                added_days += 1
        return current_date

    # ── Оркестрация документов ───────────────────────────────────────────────

    def assign_to_analyst(self, db: Session, doc_id: int, analyst_id: int, deadline_days: int):
        doc = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()
        if not doc:
            raise ValueError("Документ не найден")
        doc.assigned_to = analyst_id
        doc.assigned_at = func.now()
        doc.deadline_days = deadline_days
        doc.deadline_at = self._calculate_deadline(datetime.now(), deadline_days)
        doc.status = "ASSIGNED_TO_ANALYST"
        if doc.external_id and doc.bank_name:
            related_docs = db.query(ExternalDocument).filter(
                ExternalDocument.bank_name == doc.bank_name,
                ExternalDocument.external_id == doc.external_id,
                ExternalDocument.id != doc_id,
                ExternalDocument.assigned_to.is_(None)
            ).all()
            for related in related_docs:
                related.assigned_to = analyst_id
                related.assigned_at = func.now()
                related.deadline_days = deadline_days
                related.deadline_at = doc.deadline_at
                related.status = "ASSIGNED_TO_ANALYST"
        db.commit()
        return doc

    def submit_for_approval(self, db: Session, doc_id: int):
        doc = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()
        if not doc:
            raise ValueError("Документ не найден")
        doc.status = "FOR_APPROVAL"
        db.commit()
        return doc

    def approve_document(self, db: Session, doc_id: int, director: User):
        doc = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()
        if not doc:
            raise ValueError("Документ не найден")
        doc.status = "APPROVED"
        excel_path = self.export_full_analysis_report(db, doc_id)
        docx_path = self.generate_psd_conclusion_docx(db, doc_id, doc.assigned_user or director)
        zip_filename = f"result_{doc_id}_{uuid.uuid4().hex[:8]}.zip"
        zip_path = os.path.join("/tmp", zip_filename)
        with zipfile.ZipFile(zip_path, 'w') as zf:
            if excel_path and os.path.exists(excel_path):
                zf.write(excel_path, arcname=f"report_{doc_id}.xlsx")
            if docx_path and os.path.exists(docx_path):
                zf.write(docx_path, arcname=f"conclusion_{doc_id}.docx")
        doc.result_file_path = zip_path
        doc.status = "COMPLETED"
        doc.completed_at = func.now()
        db.commit()
        return doc

    def reject_document(self, db: Session, doc_id: int, comment: str):
        doc = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()
        if not doc:
            raise ValueError("Документ не найден")
        doc.status = "REJECTED_BY_DIRECTOR"
        doc.director_comment = comment
        db.commit()
        return doc

    def delegate_authority(self, db: Session, from_user_id: int, to_user_id: int, days: int):
        user = db.query(User).filter(User.id == from_user_id).first()
        if not user:
            raise ValueError("Пользователь не найден")
        user.delegated_to_id = to_user_id
        user.delegation_start = func.now()
        user.delegation_end = datetime.now() + timedelta(days=days)
        db.commit()
        return user
