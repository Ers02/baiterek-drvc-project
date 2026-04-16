from decimal import Decimal

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_, String, desc, text, cast, case
from typing import List, Optional, Dict, Any, Literal, Union
from datetime import datetime, timezone
import pandas as pd
import os
import re
import zipfile
import shutil
import uuid
import io
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

from ..models.models import (
    AgskReestrKtpMatch, PsdDocumentItem,
    ExternalDocument, Reestr_KTP, Agsk, Enstru, PsdAnalysisSession, User
)
from ..utils.text_utils import tokenize, score_pair

# Тип режима поиска — соответствует SearchMode на фронтенде
SearchMode = Literal["all", "agsk", "name"]


class PsdAnalystService:
    """Сервис для работы аналитика ПСД: КТП-центричная модель"""

    # ─────────────────────────────────────────────────────────────────────────
    # Вспомогательный: формирует dict из Reestr_KTP + пары (code, name)
    # ─────────────────────────────────────────────────────────────────────────
    @staticmethod
    def _reestr_to_result(r: Reestr_KTP, enstru_code: str, enstru_name: str) -> Dict:
        dvc_val = float(re.sub(r'[^0-9.]', '', r.dvc_percent)) if r.dvc_percent else 0
        return {
            "ktp_id":        r.id,
            "enstru_code":   enstru_code,
            "enstru_name":   enstru_name or "—",
            "company":       r.company_name,
            "bin":           r.bin_iin,
            "product":       r.product_name,
            "dvc_percent":   dvc_val,
            "address":       r.production_address,
            "registry_date": r.registry_inclusion_date.strftime('%d.%m.%Y')
                             if r.registry_inclusion_date else None,
            "source":        "reestr_ktp",
            "region":        r.region_kato,
            "agsk3_codes":   r.agsk3_codes or [],
            "agsk3_names":   r.agsk3_names or [],
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Обновить все позиции с данным АГСК во всех документах
    # ─────────────────────────────────────────────────────────────────────────
    def _apply_library_to_all_documents(self, db: Session, agsk_code: str):
        """
        После добавления/удаления записи в библиотеке — пересчитывает
        match_type/enstru_code для всех PsdDocumentItem с этим АГСК-кодом.
        Использует AgskEnstruMatcher для каскадного поиска (Библиотека -> Реестр).
        """
        from .agsk_enstru_matcher import AgskEnstruMatcher
        matcher = AgskEnstruMatcher(db)
        best = matcher.get_match_for_agsk(agsk_code)
        
        update_data = {
            "enstru_code":  best["enstru_code"]  if best else None,
            "enstru_name":  best["enstru_name"]  if best else None,
            "match_type":   best["match_type"]   if best else "none",
            "match_score":  best["score"]        if best else None,
            "match_reason": best["reason"]       if best else None,
        }
        db.query(PsdDocumentItem).filter(
            PsdDocumentItem.code_sn == agsk_code
        ).update(update_data, synchronize_session=False)
        db.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # Авто-сопоставление при парсинге документа
    # ─────────────────────────────────────────────────────────────────────────
    def _run_auto_matching_for_document(self, db: Session, doc_id: int):
        """
        Для каждой позиции документа ищет сопоставление через AgskEnstruMatcher.
        Логика: Библиотека замен -> Точное совпадение АГСК в КТП -> Совпадение по группе АГСК.
        """
        from .agsk_enstru_matcher import AgskEnstruMatcher
        matcher = AgskEnstruMatcher(db)
        
        items = (
            db.query(PsdDocumentItem)
            .filter(PsdDocumentItem.document_id == doc_id)
            .all()
        )
        for item in items:
            if not item.code_sn:
                continue
            
            best = matcher.get_match_for_agsk(item.code_sn)
            if best:
                item.enstru_code  = best["enstru_code"]
                item.enstru_name  = best["enstru_name"]
                item.match_type   = best["match_type"]
                item.match_score  = best["score"]
                item.match_reason = best["reason"]
            else:
                item.match_type = "none"
        db.commit()

    # ─────────────────────────────────────────────────────────────────────────
    # Поиск в реестре КТП с поддержкой режимов
    # ─────────────────────────────────────────────────────────────────────────
    def search_enstru_in_reestr(
        self,
        db: Session,
        query: str,
        limit: int = 20,
        search_mode: SearchMode = "all",
    ) -> List[Dict]:
        q = query.strip()
        if not q or len(q) < 2:
            return []

        base_filter = and_(
            Reestr_KTP.enstru_codes.isnot(None),
            text("jsonb_array_length(enstru_codes) > 0"),
            text("NULLIF(REGEXP_REPLACE(dvc_percent, '[^0-9.]', '', 'g'), '')::numeric > 0"),
        )

        if search_mode == "agsk":
            # Префиксный поиск: 541-801 найдёт 541-801-2066-58 и т.д.
            mode_filter = text("agsk3_codes::text ILIKE :agsk_prefix").bindparams(
                agsk_prefix=f'%"{q}%'
            )

        elif search_mode == "name":
            mode_filter = or_(
                Reestr_KTP.product_name.ilike(f"%{q}%"),
                Reestr_KTP.company_name.ilike(f"%{q}%"),
                cast(Reestr_KTP.enstru_names, String).ilike(f"%{q}%"),
            )

        else:  # "all"
            mode_filter = or_(
                Reestr_KTP.product_name.ilike(f"%{q}%"),
                Reestr_KTP.company_name.ilike(f"%{q}%"),
                cast(Reestr_KTP.enstru_codes, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.enstru_names, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.agsk3_codes, String).ilike(f"%{q}%"),
            )

        sort_expr = case(
            (Reestr_KTP.product_name.ilike(f"%{q}%"), 1),
            else_=2,
        )

        rows = (
            db.query(Reestr_KTP)
            .filter(and_(base_filter, mode_filter))
            .order_by(sort_expr)
            .all()
        )

        matches: List[Dict] = []
        seen: set = set()

        for r in rows:
            codes = r.enstru_codes or []
            names = r.enstru_names or []
            for i in range(max(len(codes), len(names))):
                c = codes[i] if i < len(codes) else None
                n = names[i] if i < len(names) else None
                if not c:
                    continue

                if search_mode == "all":
                    q_lower = q.lower()
                    relevant = (
                        q_lower in str(c).lower()
                        or (n and q_lower in n.lower())
                        or (r.product_name and q_lower in r.product_name.lower())
                        or (r.company_name and q_lower in r.company_name.lower())
                        or (r.agsk3_codes and q_lower in str(r.agsk3_codes).lower())
                    )
                    if not relevant:
                        continue

                key = (c, r.company_name, r.product_name)
                if key not in seen:
                    matches.append(self._reestr_to_result(r, c, n or "—"))
                    seen.add(key)

            if len(matches) >= limit:
                break

        return matches[:limit]

    # ─────────────────────────────────────────────────────────────────────────
    # Рекомендации для АГСК-кода
    # ─────────────────────────────────────────────────────────────────────────
    def get_recommendations_for_agsk(
        self, db: Session, agsk_code: str, limit: int = 10
    ) -> List[Dict]:
        clean_agsk = agsk_code.strip()
        recs: List[Dict] = []
        seen: set = set()

        def _add_from_ktp(r: Reestr_KTP, score: int, reason: str):
            codes = r.enstru_codes or []
            names = r.enstru_names or []
            dvc_val = float(re.sub(r'[^0-9.]', '', r.dvc_percent)) if r.dvc_percent else 0
            for c, n in zip(codes, names):
                if (c, r.id) not in seen:
                    recs.append({
                        "enstru_code": c,
                        "enstru_name": n,
                        "score":       score,
                        "reason":      reason,
                        "ktp_id":      r.id,
                        "product":     r.product_name,
                        "dvc_percent": dvc_val,
                        "agsk3_codes": r.agsk3_codes or [],
                        "agsk3_names": r.agsk3_names or [],
                    })
                    seen.add((c, r.id))

        # 1. Точный АГСК-код в КТП
        for r in db.query(Reestr_KTP).filter(
            text("agsk3_codes::text ILIKE :q").params(q=f'%"{clean_agsk}"%')
        ).all():
            _add_from_ktp(r, 100, f"Точный код АГСК в КТП ({r.company_name})")

        # 2. Родительский код (первые 7 символов)
        if len(recs) < limit and len(clean_agsk) >= 7:
            parent = clean_agsk[:7]
            for r in db.query(Reestr_KTP).filter(
                text("agsk3_codes::text ILIKE :q").params(q=f'"{parent}%"')
            ).all():
                _add_from_ktp(r, 80, f"По родительскому коду {parent} в КТП")

        # 3. Семантический поиск по названию
        if len(recs) < limit:
            item = db.query(PsdDocumentItem).filter(
                PsdDocumentItem.code_sn == clean_agsk
            ).first()
            if item:
                tokens = tokenize(item.name)
                if tokens:
                    for r in db.query(Reestr_KTP).filter(
                        or_(*[Reestr_KTP.product_name.ilike(f"%{t}%") for t in tokens[:2]])
                    ).all():
                        codes = r.enstru_codes or []
                        names = r.enstru_names or []
                        dvc_val = float(re.sub(r'[^0-9.]', '', r.dvc_percent)) if r.dvc_percent else 0
                        for c, n in zip(codes, names):
                            if (c, r.id) not in seen:
                                sc, _ = score_pair(
                                    {"full_name": item.name, "name_ru": item.name, "standart": ""},
                                    {"name_rus": n, "detail_rus": r.product_name, "standard": ""},
                                )
                                recs.append({
                                    "enstru_code": c,
                                    "enstru_name": n,
                                    "score":       sc,
                                    "reason":      "Похожее название товара в КТП",
                                    "ktp_id":      r.id,
                                    "product":     r.product_name,
                                    "dvc_percent": dvc_val,
                                    "agsk3_codes": r.agsk3_codes or [],
                                    "agsk3_names": r.agsk3_names or [],
                                })
                                seen.add((c, r.id))

        recs.sort(key=lambda x: x["score"], reverse=True)
        return recs[:limit]

    # ─────────────────────────────────────────────────────────────────────────
    # CRUD
    # ─────────────────────────────────────────────────────────────────────────
    def get_document_items_with_matches(
        self, db: Session, doc_id: int,
        only_unmatched: bool = False,
        search: Optional[str] = None,
        skip: int = 0, limit: int = 50,
    ):
        query = db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id)
        if search:
            q = search.strip()
            query = query.filter(or_(
                PsdDocumentItem.name.ilike(f"%{q}%"),
                PsdDocumentItem.code_sn.ilike(f"%{q}%"),
            ))
        if only_unmatched:
            query = query.filter(PsdDocumentItem.match_type == "none")

        # Сортировка: сначала несопоставленные, затем по росту качества (match_score)
        query = query.order_by(
            desc(PsdDocumentItem.match_type == "none"),
            PsdDocumentItem.match_score.asc(),
            PsdDocumentItem.id.asc()
        )

        total_count = query.count()
        items = query.offset(skip).limit(limit).all()

        # Оптимизация: загружаем все нужные АГСК одним запросом
        agsk_codes = [it.code_sn for it in items if it.code_sn]
        agsk_map = {}
        if agsk_codes:
            agsk_data = db.query(Agsk).filter(Agsk.code.in_(agsk_codes)).all()
            agsk_map = {a.code: a for a in agsk_data}

        result = []
        for item in items:
            agsk_info = agsk_map.get(item.code_sn)
            result.append({
                "id":             item.id,
                "item_id":        item.id,
                "document_id":    item.document_id,
                "position_number": item.position_number,
                "name":           item.name,
                "code_sn":        item.code_sn,
                "unit":           item.unit,
                "volume":         float(item.volume) if item.volume else 0,
                "price":          float(item.price) if item.price else 0,
                "total_amount":   float(item.total_amount) if item.total_amount else 0,
                "enstru_code":    item.enstru_code,
                "enstru_name":    item.enstru_name,
                "match_type":     item.match_type,
                "match_score":    item.match_score,
                "match_reason":   item.match_reason,
                "can_edit":       True,
                "agsk_name_ru":   agsk_info.name_ru   if agsk_info else None,
                "agsk_full_name": agsk_info.full_name if agsk_info else None,
            })
        return {"items": result, "total": total_count, "skip": skip, "limit": limit}

    def create_manual_match(
        self, db: Session, agsk_code: str, enstru_code: str, analyst_id: int,
        doc_id: Optional[int] = None, ktp_id: Optional[int] = None,
        dvc_percent: Optional[float] = None, product_name_ktp: Optional[str] = None,
        source: str = "manual",
    ):
        clean_agsk = str(agsk_code).strip()
        agsk = db.query(Agsk).filter(Agsk.code == clean_agsk).first()
        enstru_name = db.query(Enstru.name_rus).filter(Enstru.code == enstru_code).scalar() or "—"

        match = db.query(AgskReestrKtpMatch).filter(
            AgskReestrKtpMatch.agsk_code == clean_agsk,
            AgskReestrKtpMatch.enstru_code == enstru_code,
            AgskReestrKtpMatch.ktp_id == ktp_id,
        ).first()
        if match:
            match.is_active = True
            match.dvc_percent = dvc_percent
            match.product_name_ktp = product_name_ktp
            match.updated_at = func.now()
        else:
            match = AgskReestrKtpMatch(
                agsk_code=clean_agsk, enstru_code=enstru_code, ktp_id=ktp_id,
                agsk_name_ru=agsk.name_ru if agsk else "Неизвестный АГСК",
                enstru_name_ru=enstru_name, product_name_ktp=product_name_ktp,
                dvc_percent=dvc_percent, created_by=analyst_id,
                psd_document_id=doc_id,
            )
            db.add(match)
        db.commit()
        self._apply_library_to_all_documents(db, clean_agsk)
        return match

    def get_agsk_library(self, db: Session, agsk_code: str) -> List[AgskReestrKtpMatch]:
        return db.query(AgskReestrKtpMatch).filter(
            AgskReestrKtpMatch.agsk_code == agsk_code.strip(),
            AgskReestrKtpMatch.is_active == True,
        ).all()

    def remove_from_library(self, db: Session, match_id: int):
        match = db.query(AgskReestrKtpMatch).filter(AgskReestrKtpMatch.id == match_id).first()
        if match:
            agsk_code = match.agsk_code
            match.is_active = False
            db.commit()
            self._apply_library_to_all_documents(db, agsk_code)
        return {"status": "ok"}

    def parse_psd_file(self, db: Session, doc_id: int, file_path: str):
        """
        Парсинг файла .kenml или архива .zip с .kenml файлами внутри.
        """
        from .psd_analyzer.analyzer import clean_product_name, is_non_product, has_letters
        from .importers.kenml_parser import parse_kenml_file
        
        all_rows = []
        
        if file_path.lower().endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as z:
                for name in z.namelist():
                    if name.lower().endswith('.kenml'):
                        with z.open(name) as f:
                            # Читаем содержимое файла в буфер
                            content = f.read()
                            # kenml_parser ожидает объект с атрибутами 'file' и 'filename'
                            fake_file = type('F', (), {
                                'file': io.BytesIO(content),
                                'filename': name,
                            })()
                            rows = parse_kenml_file(fake_file)
                            all_rows.extend(rows)
        else:
            # Одиночный kenml
            rows = parse_kenml_file(
                type('F', (), {
                    'file': open(file_path, 'rb'),
                    'filename': os.path.basename(file_path),
                })()
            )
            all_rows.extend(rows)
            
        unique_items = {}
        for row in all_rows:
            try:
                amount = float(row.get('Сумма', 0))
                if amount <= 0.01:
                    continue
            except Exception:
                continue
            name    = str(row.get('Наименование', '')).strip()
            code_sn = str(row.get('КодСНБ', '')).strip()
            cat     = str(row.get('Категория', '')).lower()
            if cat != '' and not any(x in cat for x in ['товар', 'материал', 'оборудование']):
                continue
            if is_non_product(name) or (code_sn != '' and has_letters(code_sn)):
                continue
            key = (name, code_sn)
            if key not in unique_items:
                unique_items[key] = {
                    "№": str(row.get('№', '')), "name": name, "agsk": code_sn,
                    "clean": clean_product_name(name),
                    "unit": str(row.get('Ед. изм.', '')), "vol": 0.0, "total": 0.0,
                }
            unique_items[key]['vol']   += float(row.get('Объем', 0))
            unique_items[key]['total'] += amount

        db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id).delete()
        for i in unique_items.values():
            db.add(PsdDocumentItem(
                document_id=doc_id, position_number=i['№'], name=i['name'],
                code_sn=i['agsk'], unit=i['unit'], volume=i['vol'],
                price=i['total'] / i['vol'] if i['vol'] else 0,
                total_amount=i['total'], clean_name=i['clean'], is_product=True,
            ))
        db.commit()
        doc = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()
        if doc:
            doc.status = "PARSED"
            db.commit()
        self._run_auto_matching_for_document(db, doc_id)

    def export_matches_to_excel(self, db: Session, format_type: str = "full"):
        matches = db.query(AgskReestrKtpMatch).filter(AgskReestrKtpMatch.is_active == True).all()
        data = [{
            "Код АГСК":             m.agsk_code,
            "Наименование АГСК":    m.agsk_name_ru,
            "Код ЕНС ТРУ":          m.enstru_code,
            "Наименование ЕНС ТРУ": m.enstru_name_ru,
            "Продукт":              m.product_name_ktp,
            "ДВС%":                 m.dvc_percent,
        } for m in matches]
        path = f"/tmp/export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        pd.DataFrame(data).to_excel(path, index=False)
        return {"file_path": path}

    def export_full_analysis_report(self, db: Session, doc_id: Optional[int] = None) -> Optional[str]:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils import get_column_letter
        from decimal import Decimal
        from datetime import datetime
        import os
        import re
        from collections import defaultdict

        # ── 1. Загружаем позиции документа ───────────────────────────────────
        q = db.query(PsdDocumentItem, Agsk).outerjoin(Agsk, PsdDocumentItem.code_sn == Agsk.code)
        if doc_id:
            q = q.filter(PsdDocumentItem.document_id == doc_id)
        items_data = q.order_by(PsdDocumentItem.id).all()

        if not items_data:
            return None

        doc = None
        if doc_id:
            doc = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()

        agsk_codes = list({item.code_sn for item, _ in items_data if item.code_sn})
        enstru_codes_set = list({item.enstru_code for item, _ in items_data if item.enstru_code})

        # ── 2. Библиотека замен ───────────────────
        library_map = defaultdict(list)
        if agsk_codes:
            lib_rows = db.query(AgskReestrKtpMatch).filter(
                AgskReestrKtpMatch.agsk_code.in_(agsk_codes),
                AgskReestrKtpMatch.is_active == True,
            ).all()
            for m in lib_rows:
                library_map[m.agsk_code].append(m)

        # ── 3. Все поставщики для найденных ЕНС ТРУ ──────────────────
        suppliers_by_enstru = defaultdict(list)
        if enstru_codes_set:
            for code in enstru_codes_set:
                all_s = db.query(Reestr_KTP).filter(Reestr_KTP.enstru_codes.contains([code])).all()
                suppliers_by_enstru[code] = all_s

        # ── 4. Прямые КТП и групповые для summary ──
        direct_ktp_map = {}
        group_ktp_map = {}
        if agsk_codes:
            for code in agsk_codes:
                r = db.query(Reestr_KTP).filter(Reestr_KTP.agsk3_codes.contains([code])).first()
                if r:
                    direct_ktp_map[code] = r
                    continue
                if len(code) >= 10:
                    parent = code[:10]
                    r_group = db.query(Reestr_KTP).filter(
                        text("EXISTS (SELECT 1 FROM jsonb_array_elements_text(agsk3_codes) AS elem WHERE elem LIKE :prefix)")
                    ).params(prefix=f"{parent}%").first()
                    if r_group: group_ktp_map[code] = r_group

        wb = openpyxl.Workbook()
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1B5E20", end_color="1B5E20", fill_type="solid")
        sub_header_fill = PatternFill(start_color="E8F5E9", end_color="E8F5E9", fill_type="solid")
        border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
        
        # ЛИСТ 1: СМЕТА
        ws1 = wb.active
        ws1.title = "Смета"
        ws1.merge_cells('A1:Q1')
        ws1['A1'] = "СМЕТА ЗАКУПОК"
        ws1['A1'].font = Font(size=16, bold=True)
        ws1['A1'].alignment = Alignment(horizontal='center')
        if doc:
            ws1.merge_cells('A2:Q2')
            ws1['A2'] = f"Наименование проекта: {doc.bank_name}"
            ws1['A2'].font = Font(bold=True, size=12)

        columns1 = [
            "№", "Код по ЕНС ТРУ", "Наименование закупаемых товаров услуг работ",
            "Краткая характеристика", "Дополнительная характеристика",
            "Единица измерения(МКЕИ)", "Количество, объём", "Цена за единицу тенге(без НДС)",
            "Сумма планируемая для закупок ТРУ", "Место закупки(КАТО)", "Место поставки(КАТО)",
            "Статья затрат", "Источник финансирования", "КОД АГСК для смр", "КТП", "ВЦ %", "Сумма ВЦ тенге без НДС"
        ]
        for col_idx, col_name in enumerate(columns1, 1):
            cell = ws1.cell(row=5, column=col_idx, value=col_name)
            cell.font = header_font; cell.fill = header_fill; cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        ws1.row_dimensions[5].height = 45

        ws1.merge_cells('A6:Q6')
        ws1['A6'] = "1. Товары"; ws1['A6'].font = Font(bold=True, size=12); ws1['A6'].fill = sub_header_fill
        
        curr_row = 7; total_sum = Decimal('0'); total_vc_sum = Decimal('0')
        for idx, (item, agsk) in enumerate(items_data, 1):
            dvc_p = Decimal('0')
            if item.match_type in ('auto_ktp', 'auto'):
                r = direct_ktp_map.get(item.code_sn) or group_ktp_map.get(item.code_sn)
                if r and r.dvc_percent:
                    try: dvc_p = Decimal(re.sub(r'[^0-9.]', '', r.dvc_percent).replace(',', '.'))
                    except: pass
            elif item.match_type in ('manual', 'manual_ktp'):
                lib = library_map.get(item.code_sn, [])
                if lib: dvc_p = Decimal(str(lib[0].dvc_percent or 0))

            i_total = Decimal(str(item.total_amount or 0)); vc_a = i_total * (dvc_p / 100)
            row_data = [
                f"{idx} Т", item.enstru_code or "", item.enstru_name or item.name, item.name, "", 
                item.unit or "", float(item.volume or 0), float(item.price or 0), float(i_total),
                "", "", "", "", item.code_sn or "", "Да" if item.match_type != 'none' else "Нет",
                float(dvc_p), float(vc_a)
            ]
            total_sum += i_total; total_vc_sum += vc_a
            for c_idx, val in enumerate(row_data, 1):
                cell = ws1.cell(row=curr_row, column=c_idx, value=val); cell.border = border
                if c_idx in [7, 8, 9, 16, 17]: cell.number_format = '#,##0.00'
            curr_row += 1

        ws1.merge_cells(f'A{curr_row}:H{curr_row}')
        ws1.cell(row=curr_row, column=1, value="Итого по товарам:").font = Font(bold=True)
        ws1.cell(row=curr_row, column=1).alignment = Alignment(horizontal='right')
        ws1.cell(row=curr_row, column=9, value=float(total_sum)).font = Font(bold=True); ws1.cell(row=curr_row, column=9).number_format = '#,##0.00'
        avg_vc = (total_vc_sum / total_sum * 100) if total_sum > 0 else 0
        ws1.cell(row=curr_row, column=16, value=f"{avg_vc:.2f}%").font = Font(bold=True)
        ws1.cell(row=curr_row, column=17, value=float(total_vc_sum)).font = Font(bold=True); ws1.cell(row=curr_row, column=17).number_format = '#,##0.00'

        # ЛИСТ 2: АНАЛИЗ ПСД
        ws2 = wb.create_sheet("Анализ ПСД")
        columns2 = [
            "№ позиции", "Наименование позиции", "Код АГСК", "Полное название АГСК",
            "Ед. изм.", "Объем", "Цена", "Сумма",
            "Итог: Код ЕНС ТРУ", "Итог: Наим. ЕНС ТРУ", "Итог: Тип", "Итог: Причина",
            "Источник", "Компания", "БИН", "Наим. товара", "ВЦ%", "Адрес", "Регион", "Коды АГСК3"
        ]
        for col_idx, col_name in enumerate(columns2, 1):
            cell = ws2.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font; cell.fill = PatternFill("solid", fgColor="2C3E50"); cell.border = border
            cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)

        FILL_MAP = {
            "Выбор аналитика": PatternFill("solid", fgColor="D5F5E3"), # Зеленый
            "Авто-подбор (КТП)": PatternFill("solid", fgColor="D6EAF8"), # Синий
            "Реестр (по коду ЕНС)": PatternFill("solid", fgColor="FEF9E7"), # Желтый
            "Нет сопоставления": PatternFill("solid", fgColor="FADBD8"), # Красный
        }
        
        curr_row2 = 2
        for pos_idx, (item, agsk) in enumerate(items_data, 1):
            base = [
                pos_idx, item.name, item.code_sn, agsk.full_name if agsk else "",
                item.unit, float(item.volume or 0), float(item.price or 0), float(item.total_amount or 0),
                item.enstru_code, item.enstru_name, item.match_type, item.match_reason,
            ]
            
            rows_to_add = []
            selected_ktp_ids = set()
            
            # Собираем то что "Выбрано"
            lib_entries = library_map.get(item.code_sn or "", [])
            for m in lib_entries:
                selected_ktp_ids.add(m.ktp_id)
                dvc = float(m.dvc_percent or 0)
                rk = db.query(Reestr_KTP).filter(Reestr_KTP.id == m.ktp_id).first()
                rows_to_add.append(base + [
                    "Выбор аналитика", rk.company_name if rk else None, rk.bin_iin if rk else None, 
                    m.product_name_ktp, dvc, rk.production_address if rk else None, 
                    rk.region_kato if rk else None, ", ".join(rk.agsk3_codes) if (rk and rk.agsk3_codes) else None
                ])

            # Авто-подбор
            auto_ktp = direct_ktp_map.get(item.code_sn) or group_ktp_map.get(item.code_sn)
            if auto_ktp and auto_ktp.id not in selected_ktp_ids:
                dvc = float(re.sub(r'[^0-9.]', '', auto_ktp.dvc_percent).replace(',', '.')) if auto_ktp.dvc_percent else 0
                rows_to_add.append(base + [
                    "Авто-подбор (КТП)", auto_ktp.company_name, auto_ktp.bin_iin, auto_ktp.product_name, 
                    dvc, auto_ktp.production_address, auto_ktp.region_kato, 
                    ", ".join(auto_ktp.agsk3_codes) if auto_ktp.agsk3_codes else ""
                ])
                selected_ktp_ids.add(auto_ktp.id)

            # Реестр
            if item.enstru_code:
                all_suppliers = suppliers_by_enstru.get(item.enstru_code, [])
                for s in all_suppliers:
                    if s.id not in selected_ktp_ids:
                        dvc = float(re.sub(r'[^0-9.]', '', s.dvc_percent).replace(',', '.')) if s.dvc_percent else 0
                        rows_to_add.append(base + [
                            "Реестр (по коду ЕНС)", s.company_name, s.bin_iin, s.product_name, 
                            dvc, s.production_address, s.region_kato, 
                            ", ".join(s.agsk3_codes) if s.agsk3_codes else ""
                        ])

            if not rows_to_add:
                rows_to_add.append(base + ["Нет сопоставления"] + [None]*7)

            for r_data in rows_to_add:
                src = r_data[12]; fill = FILL_MAP.get(src, PatternFill())
                for c_idx, val in enumerate(r_data, 1):
                    cell = ws2.cell(row=curr_row2, column=c_idx, value=val)
                    cell.fill = fill; cell.border = border
                    if c_idx in [6, 7, 8, 17]: cell.number_format = '#,##0.00'
                ws2.cell(row=curr_row2, column=13).font = Font(bold=True)
                curr_row2 += 1

        for ws in [ws1, ws2]:
            for i, col in enumerate(ws.columns, 1):
                m_l = 0
                for cell in col:
                    try:
                        if cell.value and len(str(cell.value)) > m_l: m_l = len(str(cell.value))
                    except: pass
                ws.column_dimensions[get_column_letter(i)].width = min(m_l + 2, 40)
        
        os.makedirs("/tmp", exist_ok=True)
        file_path = f"/tmp/psd_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        wb.save(file_path); return file_path

    def generate_psd_conclusion_docx(self, db: Session, doc_id: int, current_user: User) -> Optional[str]:
        """
        Генерирует официальное заключение аналитика по ПСД в формате DOCX.
        """
        doc_entity = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()
        if not doc_entity:
            return None

        # Собираем статистику
        total_items = db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id).count()
        matched_items = db.query(PsdDocumentItem).filter(
            PsdDocumentItem.document_id == doc_id,
            PsdDocumentItem.match_type != 'none'
        ).count()
        
        total_amount = db.query(func.sum(PsdDocumentItem.total_amount)).filter(PsdDocumentItem.document_id == doc_id).scalar() or 0
        
        # Считаем ВЦ
        items = db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id).all()
        total_vc_amount = Decimal('0')
        
        for it in items:
            dvc = Decimal('0')
            if it.match_type != 'none':
                # Пытаемся получить процент из библиотеки или КТП
                match = db.query(AgskReestrKtpMatch).filter(
                    AgskReestrKtpMatch.agsk_code == it.code_sn,
                    AgskReestrKtpMatch.is_active == True
                ).first()
                if match:
                    dvc = Decimal(str(match.dvc_percent or 0))
                else:
                    rk = db.query(Reestr_KTP).filter(Reestr_KTP.enstru_codes.contains([it.enstru_code])).first()
                    if rk and rk.dvc_percent:
                        try: dvc = Decimal(re.sub(r'[^0-9.]', '', rk.dvc_percent).replace(',', '.'))
                        except: pass
            
            total_vc_amount += Decimal(str(it.total_amount or 0)) * (dvc / 100)

        avg_vc_percent = (total_vc_amount / Decimal(str(total_amount)) * 100) if total_amount > 0 else 0

        # Создаем документ
        doc = Document()
        
        # Заголовок
        title = doc.add_heading('ЗАКЛЮЧЕНИЕ АНАЛИТИКА ПСД', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # Основная информация
        p = doc.add_paragraph()
        p.add_run('Дата формирования: ').bold = True
        p.add_run(datetime.now().strftime('%d.%m.%Y %H:%M'))
        
        p = doc.add_paragraph()
        p.add_run('Аналитик: ').bold = True
        p.add_run(f"{current_user.full_name or current_user.username}")

        p = doc.add_paragraph()
        p.add_run('Наименование проекта (Банк): ').bold = True
        p.add_run(f"{doc_entity.bank_name}")

        p = doc.add_paragraph()
        p.add_run('Статус обработки: ').bold = True
        p.add_run(f"{doc_entity.status}")

        doc.add_heading('Результаты анализа', level=1)
        
        table = doc.add_table(rows=1, cols=2)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = 'Показатель'
        hdr_cells[1].text = 'Значение'
        
        data = [
            ('Общее количество позиций', str(total_items)),
            ('Сопоставлено позиций', str(matched_items)),
            ('Процент сопоставления', f"{(matched_items/total_items*100):.1f}%" if total_items > 0 else "0%"),
            ('Общая сумма проекта', f"{float(total_amount):,.2f} тенге"),
            ('Прогнозируемая сумма ВЦ', f"{float(total_vc_amount):,.2f} тенге"),
            ('Средний процент ВЦ', f"{float(avg_vc_percent):.2f}%"),
        ]
        
        for label, value in data:
            row_cells = table.add_row().cells
            row_cells[0].text = label
            row_cells[1].text = value

        doc.add_paragraph()
        doc.add_heading('Выводы', level=1)
        conclusion_text = (
            f"В ходе анализа проектно-сметной документации '{doc_entity.bank_name}' было обработано {total_items} позиций. "
            f"Уровень внутристрановой ценности (ВЦ) по проекту оценивается в {float(avg_vc_percent):.2f}%. "
        )
        if avg_vc_percent > 50:
            conclusion_text += "Проект демонстрирует высокий потенциал использования казахстанского содержания."
        else:
            conclusion_text += "Рекомендуется дополнительный поиск отечественных производителей для увеличения доли ВЦ."
            
        doc.add_paragraph(conclusion_text)

        doc.add_paragraph().add_run('\n\n__________________________ / Подпись /').italic = True

        # Сохранение
        os.makedirs("/tmp", exist_ok=True)
        file_path = f"/tmp/conclusion_{doc_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        doc.save(file_path)
        return file_path
