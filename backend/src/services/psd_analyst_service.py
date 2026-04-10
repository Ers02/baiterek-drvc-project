from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_, String, desc, text, cast, case
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, timezone
import pandas as pd
import os
import re

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
        from .psd_analyzer.analyzer import clean_product_name, is_non_product, has_letters
        from .importers.kenml_parser import parse_kenml_file
        rows = parse_kenml_file(
            type('F', (), {
                'file': open(file_path, 'rb'),
                'filename': os.path.basename(file_path),
            })()
        )
        unique_items = {}
        for row in rows:
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
        # ── 1. Загружаем позиции документа ───────────────────────────────────
        q = db.query(PsdDocumentItem, Agsk).outerjoin(Agsk, PsdDocumentItem.code_sn == Agsk.code)
        if doc_id:
            q = q.filter(PsdDocumentItem.document_id == doc_id)
        items = q.order_by(PsdDocumentItem.id).all()

        if not items:
            return None

        agsk_codes = list({item.code_sn for item, _ in items if item.code_sn})

        # ── 2. Библиотека замен: agsk_code -> [AgskReestrKtpMatch] ───────────
        from collections import defaultdict
        library_map: dict[str, list] = defaultdict(list)
        ktp_ids_lib: set[int] = set()

        if agsk_codes:
            lib_rows = (
                db.query(AgskReestrKtpMatch)
                .filter(
                    AgskReestrKtpMatch.agsk_code.in_(agsk_codes),
                    AgskReestrKtpMatch.is_active == True,
                )
                .all()
            )
            for m in lib_rows:
                library_map[m.agsk_code].append(m)
                if m.ktp_id:
                    ktp_ids_lib.add(m.ktp_id)

        # ── 3. КТП для библиотечных записей ──────────────────────────────────
        ktp_by_id: dict[int, Reestr_KTP] = {}
        if ktp_ids_lib:
            for r in db.query(Reestr_KTP).filter(Reestr_KTP.id.in_(ktp_ids_lib)).all():
                ktp_by_id[r.id] = r

        # ── 4. Прямые КТП (auto_ktp — точное) и групповые (auto — по префиксу) ──
        direct_ktp_map: dict[str, Reestr_KTP] = {}
        group_ktp_map: dict[str, Reestr_KTP] = {}

        if agsk_codes:
            for code in agsk_codes:
                # Точное совпадение
                r = (
                    db.query(Reestr_KTP)
                    .filter(Reestr_KTP.agsk3_codes.contains([code]))
                    .first()
                )
                if r:
                    direct_ktp_map[code] = r
                    continue

                # Групповое совпадение (родительский префикс 10 символов)
                if len(code) >= 10:
                    parent = code[:10]
                    r_group = (
                        db.query(Reestr_KTP)
                        .filter(
                            text(
                                "EXISTS ("
                                "SELECT 1 FROM jsonb_array_elements_text(agsk3_codes) AS elem "
                                "WHERE elem LIKE :prefix"
                                ")"
                            ).bindparams(prefix=f"{parent}%")
                        )
                        .first()
                    )
                    if r_group:
                        group_ktp_map[code] = r_group

        # ── Хелпер: строка-основа позиции ────────────────────────────────────
        def base_row(pos_num: int, item: PsdDocumentItem, agsk: Agsk) -> dict:
            return {
                "№ позиции": pos_num,
                "Наименование позиции": item.name,
                "Код АГСК": item.code_sn,
                "Полное название АГСК": agsk.full_name if agsk else None,
                "Ед. изм.": item.unit,
                "Объем": float(item.volume) if item.volume else 0,
                "Цена": float(item.price) if item.price else 0,
                "Сумма": float(item.total_amount) if item.total_amount else 0,
                # сопоставление
                "Итог: Код ЕНС ТРУ": item.enstru_code,
                "Итог: Наим. ЕНС ТРУ": item.enstru_name,
                "Итог: Тип": item.match_type,
                "Итог: Причина": item.match_reason,
                # источник
                "Источник": None,
                # ЕДИНЫЕ столбцы для КТП/Библиотеки
                "Компания": None,
                "БИН": None,
                "Наим. товара": None,
                "ВЦ%": None,
                "Адрес": None,
                "Регион": None,
                "Коды АГСК3": None,
            }

        def fill_ktp(row: dict, ktp: Reestr_KTP):
            dvc = float(re.sub(r'[^0-9.]', '', ktp.dvc_percent)) if ktp.dvc_percent else 0
            row.update({
                "Компания": ktp.company_name,
                "БИН": ktp.bin_iin,
                "Наим. товара": ktp.product_name,
                "ВЦ%": dvc,
                "Адрес": ktp.production_address,
                "Регион": ktp.region_kato,
                "Коды АГСК3": ", ".join(ktp.agsk3_codes) if ktp.agsk3_codes else None,
            })

        def fill_lib(row: dict, m: AgskReestrKtpMatch, ktp: Reestr_KTP | None):
            """Заполняет единые столбцы из библиотечной записи"""
            dvc = float(m.dvc_percent) if m.dvc_percent else 0
            row.update({
                "Компания": ktp.company_name if ktp else None,
                "БИН": ktp.bin_iin if ktp else None,
                "Наим. товара": m.product_name_ktp,
                "ВЦ%": dvc,
                "Адрес": ktp.production_address if ktp else None,
                "Регион": ktp.region_kato if ktp else None,
                "Коды АГСК3": ", ".join(ktp.agsk3_codes) if (ktp and ktp.agsk3_codes) else None,
            })

        # ── 5. Формируем строки ───────────────────────────────────────────────
        data = []

        for pos_num, (item, agsk) in enumerate(items, start=1):
            lib_entries = library_map.get(item.code_sn or "", [])
            direct_ktp = direct_ktp_map.get(item.code_sn or "") \
                         or group_ktp_map.get(item.code_sn or "")
            match_type = item.match_type or "none"

            if match_type == "none":
                # ── Нет сопоставления: одна строка ───────────────────────────
                row = base_row(pos_num, item, agsk)
                row["Источник"] = "Нет сопоставления"
                data.append(row)

            elif match_type in ("auto_ktp", "auto"):
                # ── Только КТП (авто): одна строка ──────────────────────────
                row = base_row(pos_num, item, agsk)
                row["Источник"] = "КТП (авто)"
                if direct_ktp:
                    fill_ktp(row, direct_ktp)
                data.append(row)

            elif match_type == "manual":
                # ── Только библиотека: по одной строке на каждую запись ───────
                if lib_entries:
                    for m in lib_entries:
                        row = base_row(pos_num, item, agsk)
                        row["Источник"] = "Библиотека"
                        fill_lib(row, m, ktp_by_id.get(m.ktp_id) if m.ktp_id else None)
                        data.append(row)
                else:
                    row = base_row(pos_num, item, agsk)
                    row["Источник"] = "Библиотека"
                    data.append(row)

            elif match_type == "manual_ktp":
                # ── КТП + Библиотека: сначала строка КТП, потом строки библиотеки ──

                # Строка КТП
                row_ktp = base_row(pos_num, item, agsk)
                row_ktp["Источник"] = "КТП (авто)"

                if lib_entries:
                    first_lib_ktp = ktp_by_id.get(lib_entries[0].ktp_id) if lib_entries[0].ktp_id else None
                    if first_lib_ktp:
                        fill_ktp(row_ktp, first_lib_ktp)
                    elif direct_ktp:
                        fill_ktp(row_ktp, direct_ktp)
                elif direct_ktp:
                    fill_ktp(row_ktp, direct_ktp)

                data.append(row_ktp)

                # Строки библиотеки
                for m in lib_entries:
                    row_lib = base_row(pos_num, item, agsk)
                    row_lib["Источник"] = "Библиотека"
                    fill_lib(row_lib, m, ktp_by_id.get(m.ktp_id) if m.ktp_id else None)
                    data.append(row_lib)

            else:
                # Неизвестный тип — одна строка
                row = base_row(pos_num, item, agsk)
                row["Источник"] = match_type
                data.append(row)

        if not data:
            return None

        # ── 6. Красим Excel ───────────────────────────────────────────────────
        import openpyxl
        from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
        from openpyxl.utils import get_column_letter

        df = pd.DataFrame(data)
        os.makedirs("/tmp", exist_ok=True)
        file_path = f"/tmp/psd_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Анализ ПСД")
            ws = writer.sheets["Анализ ПСД"]

            # Цвета по типу источника
            FILL = {
                "КТП (авто)": PatternFill("solid", fgColor="D6EAF8"),  # голубой
                "Библиотека": PatternFill("solid", fgColor="D5F5E3"),  # зелёный
                "КТП + Библиотека": PatternFill("solid", fgColor="FEF9E7"),  # жёлтый
                "Нет сопоставления": PatternFill("solid", fgColor="FADBD8"),  # красный
            }
            header_fill = PatternFill("solid", fgColor="2C3E50")
            header_font = Font(bold=True, color="FFFFFF")
            thin = Side(style="thin", color="CCCCCC")
            border = Border(left=thin, right=thin, top=thin, bottom=thin)

            # Шапка
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", wrap_text=True)

            # Колонка "Источник"
            source_col_idx = df.columns.get_loc("Источник") + 1

            # Строки данных
            for row_idx, excel_row in enumerate(ws.iter_rows(min_row=2), start=2):
                source_cell = ws.cell(row=row_idx, column=source_col_idx)
                source_val = source_cell.value or ""
                fill = FILL.get(source_val, PatternFill())
                for cell in excel_row:
                    cell.fill = fill
                    cell.border = border
                    cell.alignment = Alignment(wrap_text=False, vertical="center")
                source_cell.font = Font(bold=True)

            # Ширина колонок
            for col_idx, col_name in enumerate(df.columns, start=1):
                max_len = max(len(str(col_name)), 10)
                ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 40)

            ws.freeze_panes = "A2"

        return file_path