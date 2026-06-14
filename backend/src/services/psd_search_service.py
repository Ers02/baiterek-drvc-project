"""Поиск поставщиков в реестре КТП + авто-сопоставление АГСК→ЕНСТРУ для документа.

Используется как миксин в PsdAnalystService. Не импортирует главный класс,
обращается к helpers через `self` (разрешается через MRO).
"""
import re
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy import String, and_, cast, case, or_, text
from sqlalchemy.orm import Session

from ..models.models import (
    Agsk, AgskEnstruMatch, Enstru, Kpved, Oked, PsdDocumentItem,
    Reestr_KTP, Tnved,
)
from ..utils.text_utils import score_pair, tokenize

SearchMode = Literal["all", "agsk", "name"]


class PsdSearchMixin:
    @staticmethod
    def _enstru_codes_with_active_supplier(db: Session, enstru_codes) -> set:
        """Возвращает множество ЕНСТРУ-кодов из заданного списка, для которых
        в реестре КТП есть хотя бы один активный поставщик с валидным ДВС (>0).

        Используется чтобы НЕ ставить «💡 Подсказка», если её нельзя реализовать
        (поиск на UI всё равно ничего не найдёт). Фильтр совпадает с поиском
        в search_enstru_in_reestr.
        """
        codes = list({c for c in enstru_codes if c}) if enstru_codes else []
        if not codes:
            return set()
        valid_dvc = text("NULLIF(REGEXP_REPLACE(dvc_percent, '[^0-9.]', '', 'g'), '')::numeric > 0")
        rows = db.query(Reestr_KTP.enstru_codes).filter(
            Reestr_KTP.is_active.isnot(False),
            valid_dvc,
            or_(*[Reestr_KTP.enstru_codes.contains([c]) for c in codes]),
        ).all()
        result: set = set()
        codes_set = set(codes)
        for (ec_list,) in rows:
            for c in (ec_list or []):
                if c in codes_set:
                    result.add(c)
        return result

    @staticmethod
    def _reestr_to_result(r: Reestr_KTP, enstru_code: str, enstru_name: str) -> Dict:
        dvc_val = float(re.sub(r'[^0-9.]', '', r.dvc_percent)) if r.dvc_percent else 0
        return {
            "ktp_id": r.id,
            "enstru_code": enstru_code,
            "enstru_name": enstru_name or "—",
            "company": r.company_name,
            "bin": r.bin_iin,
            "product": r.product_name,
            "dvc_percent": dvc_val,
            "address": r.production_address,
            "registry_date": r.registry_inclusion_date.strftime('%d.%m.%Y') if r.registry_inclusion_date else None,
            "source": "reestr_ktp",
            "region": r.region_kato,
            "agsk3_codes": r.agsk3_codes or [],
            "agsk3_names": r.agsk3_names or [],
            "oked_codes": r.oked_codes or [],
            "oked_names": r.oked_names or [],
            "kpved_codes": r.kpved_codes or [],
            "kpved_names": r.kpved_names or [],
            "tnved_codes": r.tnved_codes or [],
        }

    def _run_auto_matching_for_document(self, db: Session, doc_id: int):
        items = db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id).all()
        agsk_codes = list({it.code_sn for it in items if it.code_sn})

        # ── Bulk-1: точное совпадение кода АГСК в jsonb agsk3_codes реестра КТП ──
        # Это основа АВТО-сопоставления: код АГСК из ПСД 1-в-1 присутствует
        # в активной записи реестра. Один запрос вместо тысяч per-item.
        agsk_exact_map: Dict[str, Any] = {}
        if agsk_codes:
            ktp_rows = db.query(Reestr_KTP).filter(
                Reestr_KTP.is_active.isnot(False),
                or_(*[Reestr_KTP.agsk3_codes.contains([c]) for c in agsk_codes]),
            ).order_by(Reestr_KTP.id).all()
            agsk_set = set(agsk_codes)
            for ktp in ktp_rows:
                for ac in (ktp.agsk3_codes or []):
                    if ac in agsk_set and ac not in agsk_exact_map:
                        agsk_exact_map[ac] = ktp

        # ── Bulk-2: утверждённая библиотека (для АГСК без прямого совпадения) ──
        approved_map: Dict[str, AgskEnstruMatch] = {}
        if agsk_codes:
            approved_rows = db.query(AgskEnstruMatch).filter(
                AgskEnstruMatch.agsk_code.in_(agsk_codes),
                AgskEnstruMatch.is_approved == True,
                AgskEnstruMatch.is_active == True,
            ).order_by(AgskEnstruMatch.created_at.asc()).all()
            for m in approved_rows:
                approved_map[m.agsk_code] = m

        # ── Bulk-3: имена ЕНСТРУ из справочника (для авто и библиотеки) ────────
        enstru_codes_needed: set = {m.enstru_code for m in approved_map.values()}
        for ktp in agsk_exact_map.values():
            if ktp.enstru_codes:
                enstru_codes_needed.add(ktp.enstru_codes[0])
        enstru_name_map: Dict[str, str] = {}
        if enstru_codes_needed:
            enstru_name_map = {
                e.code: e.name_rus
                for e in db.query(Enstru).filter(Enstru.code.in_(enstru_codes_needed)).all()
            }

        # Какие ЕНСТРУ (из библиотеки и из самих позиций) реально имеют активного
        # поставщика в реестре КТП. «💡 Подсказку» ставим ТОЛЬКО для них.
        candidate_enstru = {m.enstru_code for m in approved_map.values()}
        for it in items:
            if it.enstru_code:
                candidate_enstru.add(it.enstru_code)
        enstru_in_ktp = self._enstru_codes_with_active_supplier(db, candidate_enstru)

        for item in items:
            # ── ПРИОРИТЕТ 1: точное совпадение АГСК в реестре КТП → АВТО ────────
            ktp = agsk_exact_map.get(item.code_sn) if item.code_sn else None
            if ktp is not None:
                enstru_code = ktp.enstru_codes[0] if ktp.enstru_codes else None
                if enstru_code:
                    item.enstru_code = enstru_code
                    item.enstru_name = (
                        enstru_name_map.get(enstru_code)
                        or (ktp.enstru_names[0] if ktp.enstru_names else None)
                    )
                item.match_type = "auto_ktp"
                item.match_score = 100
                dvc = ktp.dvc_percent or "0"
                item.match_reason = f"Точное совпадение кода АГСК в реестре КТП (Завод: {ktp.company_name}, ДВС: {dvc}%)"
                continue

            # ── ПРИОРИТЕТ 2: утверждённая библиотека → подсказка ───────────────
            approved = approved_map.get(item.code_sn) if item.code_sn else None
            if approved and approved.enstru_code in enstru_in_ktp:
                item.enstru_code = approved.enstru_code
                item.enstru_name = enstru_name_map.get(approved.enstru_code)
                item.match_type = "suggested"
                item.match_score = 100
                item.match_reason = "Подсказка из библиотеки — выберите поставщика из реестра КТП"
                continue

            # ── ПРИОРИТЕТ 3: ЕНСТРУ-подсказка из сметы ─────────────────────────
            if item.enstru_code and item.enstru_code in enstru_in_ktp:
                item.match_type = "suggested"
                item.match_reason = "ЕНСТРУ из сметы — выберите поставщика из реестра КТП"
                continue

            # ── Иначе — не сопоставлено ────────────────────────────────────────
            item.match_type = "none"
            if item.enstru_code:
                item.match_reason = "ЕНСТРУ из сметы, но в реестре КТП нет активных поставщиков"

        db.commit()

    def search_enstru_in_reestr(self, db: Session, query: str, limit: int = 20, search_mode: SearchMode = "all") -> List[Dict]:
        q = query.strip()
        if not q or len(q) < 2:
            return []
        base_filter = text("NULLIF(REGEXP_REPLACE(dvc_percent, '[^0-9.]', '', 'g'), '')::numeric > 0")
        if search_mode == "agsk":
            mode_filter = text("agsk3_codes::text ILIKE :agsk_prefix").bindparams(agsk_prefix=f'%"{q}%')
        elif search_mode == "name":
            mode_filter = or_(
                Reestr_KTP.product_name.ilike(f"%{q}%"),
                Reestr_KTP.company_name.ilike(f"%{q}%"),
                cast(Reestr_KTP.enstru_names, String).ilike(f"%{q}%"),
            )
        else:
            mode_filter = or_(
                Reestr_KTP.product_name.ilike(f"%{q}%"),
                Reestr_KTP.company_name.ilike(f"%{q}%"),
                cast(Reestr_KTP.enstru_codes, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.enstru_names, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.agsk3_codes, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.oked_codes, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.kpved_codes, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.tnved_codes, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.oked_names, String).ilike(f"%{q}%"),
                cast(Reestr_KTP.kpved_names, String).ilike(f"%{q}%"),
            )
        sort_expr = case((Reestr_KTP.product_name.ilike(f"%{q}%"), 1), else_=2)
        active_filter = Reestr_KTP.is_active.isnot(False)
        rows = db.query(Reestr_KTP).filter(and_(base_filter, active_filter, mode_filter)).order_by(sort_expr).all()

        # Bulk-lookup всех кодов из наших справочников
        all_enstru_codes: set = set()
        all_agsk3_codes: set = set()
        all_oked_codes: set = set()
        all_kpved_codes: set = set()
        all_tnved_codes: set = set()
        for r in rows:
            for c in (r.enstru_codes or []):
                if c: all_enstru_codes.add(str(c))
            for c in (r.agsk3_codes or []):
                if c: all_agsk3_codes.add(str(c))
            for c in (r.oked_codes or []):
                if c: all_oked_codes.add(str(c))
            for c in (r.kpved_codes or []):
                if c: all_kpved_codes.add(str(c))
            for c in (r.tnved_codes or []):
                if c: all_tnved_codes.add(str(c))

        enstru_map: Dict[str, Any] = {e.code: e for e in db.query(Enstru).filter(Enstru.code.in_(all_enstru_codes)).all()} if all_enstru_codes else {}
        agsk_map: Dict[str, Any] = {a.code: a for a in db.query(Agsk).filter(Agsk.code.in_(all_agsk3_codes)).all()} if all_agsk3_codes else {}
        oked_map: Dict[str, Any] = {o.code: o for o in db.query(Oked).filter(Oked.code.in_(all_oked_codes)).all()} if all_oked_codes else {}
        kpved_map: Dict[str, Any] = {k.code: k for k in db.query(Kpved).filter(Kpved.code.in_(all_kpved_codes)).all()} if all_kpved_codes else {}
        tnved_map: Dict[str, Any] = {t.code: t for t in db.query(Tnved).filter(Tnved.code.in_(all_tnved_codes)).all()} if all_tnved_codes else {}

        matches: List[Dict] = []
        seen: set = set()
        for r in rows:
            codes = r.enstru_codes or []
            names = r.enstru_names or []
            if not codes:
                codes = [""]
                names = [""]

            dvc_val = float(re.sub(r'[^0-9.]', '', r.dvc_percent)) if r.dvc_percent else 0
            agsk3_codes = r.agsk3_codes or []
            oked_codes = r.oked_codes or []
            kpved_codes = r.kpved_codes or []
            tnved_codes = r.tnved_codes or []

            for i in range(max(len(codes), len(names))):
                c = codes[i] if i < len(codes) else None
                n = names[i] if i < len(names) else None
                if search_mode == "all":
                    q_lower = q.lower()
                    relevant = (
                        (c and q_lower in str(c).lower()) or (n and q_lower in n.lower())
                        or (r.product_name and q_lower in r.product_name.lower())
                        or (r.company_name and q_lower in r.company_name.lower())
                        or (r.agsk3_codes and q_lower in str(r.agsk3_codes).lower())
                        or (r.oked_codes and q_lower in str(r.oked_codes).lower())
                        or (r.kpved_codes and q_lower in str(r.kpved_codes).lower())
                        or (r.tnved_codes and q_lower in str(r.tnved_codes).lower())
                        or (r.oked_names and q_lower in str(r.oked_names).lower())
                        or (r.kpved_names and q_lower in str(r.kpved_names).lower())
                    )
                    if not relevant:
                        continue
                enstru_obj = enstru_map.get(c) if c else None
                key = (c or "", r.company_name, r.product_name, r.id)
                if key not in seen:
                    matches.append({
                        "ktp_id": r.id,
                        "enstru_code": c or "",
                        "enstru_name": n or "—",
                        "enstru_name_rus": enstru_obj.name_rus if enstru_obj else None,
                        "enstru_detail_rus": enstru_obj.detail_rus if enstru_obj else None,
                        "enstru_standard": enstru_obj.standard if enstru_obj else None,
                        "company": r.company_name,
                        "bin": r.bin_iin,
                        "product": r.product_name,
                        "dvc_percent": dvc_val,
                        "address": r.production_address,
                        "registry_date": r.registry_inclusion_date.strftime('%d.%m.%Y') if r.registry_inclusion_date else None,
                        "source": "reestr_ktp",
                        "region": r.region_kato,
                        "agsk3_codes": agsk3_codes,
                        "agsk3_names": [agsk_map[c2].name_ru if c2 in agsk_map else "" for c2 in agsk3_codes],
                        "oked_codes": oked_codes,
                        "oked_names": [oked_map[c2].name_ru if c2 in oked_map else "" for c2 in oked_codes],
                        "kpved_codes": kpved_codes,
                        "kpved_names": [kpved_map[c2].name_ru if c2 in kpved_map else "" for c2 in kpved_codes],
                        "tnved_codes": tnved_codes,
                        "tnved_names": [tnved_map[c2].name if c2 in tnved_map else "" for c2 in tnved_codes],
                    })
                    seen.add(key)
            if len(matches) >= limit:
                break
        return matches[:limit]

    def _tmp_delete_me(self, db: Session, agsk_code: str, limit: int = 10) -> List[Dict]:
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
                        "enstru_code": c, "enstru_name": n, "score": score, "reason": reason,
                        "ktp_id": r.id, "product": r.product_name, "dvc_percent": dvc_val,
                        "agsk3_codes": r.agsk3_codes or [], "agsk3_names": r.agsk3_names or [],
                    })
                    seen.add((c, r.id))

        for r in db.query(Reestr_KTP).filter(text("agsk3_codes::text ILIKE :q").params(q=f'%"{clean_agsk}"%')).all():
            _add_from_ktp(r, 100, f"Точный код АГСК в КТП ({r.company_name})")
        if len(recs) < limit and len(clean_agsk) >= 7:
            parent = clean_agsk[:7]
            for r in db.query(Reestr_KTP).filter(text("agsk3_codes::text ILIKE :q").params(q=f'"{parent}%"')).all():
                _add_from_ktp(r, 80, f"По родительскому коду {parent} в КТП")
        if len(recs) < limit:
            item = db.query(PsdDocumentItem).filter(PsdDocumentItem.code_sn == clean_agsk).first()
            if item:
                tokens = tokenize(item.name)
                if tokens:
                    for r in db.query(Reestr_KTP).filter(or_(*[Reestr_KTP.product_name.ilike(f"%{t}%") for t in tokens[:2]])).all():
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
                                    "enstru_code": c, "enstru_name": n, "score": sc,
                                    "reason": "Похожее название товара в КТП", "ktp_id": r.id,
                                    "product": r.product_name, "dvc_percent": dvc_val,
                                    "agsk3_codes": r.agsk3_codes or [], "agsk3_names": r.agsk3_names or [],
                                })
                                seen.add((c, r.id))
        # NB: оригинал возвращал None — поведение сохранено.
