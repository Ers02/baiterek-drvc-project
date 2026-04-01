from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_, String, desc, text, cast, case, Numeric
from typing import List, Optional, Dict, Any
from datetime import datetime
import pandas as pd
import io
import os
import re

from ..models.models import (
    AgskEnstruExclusive, AgskEnstruManualMatch, PsdDocumentItem, 
    ExternalDocument, Reestr_KTP, Agsk, Enstru, PsdAnalysisSession
)

class PsdAnalystService:
    """Сервис для работы аналитика ПСД: Логика Библиотеки замен и парсинг KENML/ZIP"""
    
    def get_document_items_with_matches(self, db: Session, doc_id: int, only_unmatched: bool = False,
                                         search: Optional[str] = None, skip: int = 0, limit: int = 50):
        """Получить позиции из документа ПСД с информацией о сопоставлении"""
        query = db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id)
        if search:
            q = search.strip()
            query = query.filter(or_(PsdDocumentItem.name.ilike(f"%{q}%"), PsdDocumentItem.code_sn.ilike(f"%{q}%")))
        if only_unmatched:
            query = query.filter(PsdDocumentItem.match_type == "none")
        query = query.order_by(desc(PsdDocumentItem.match_type == "none"), PsdDocumentItem.match_score.asc())
        total_count = query.count()
        items = query.offset(skip).limit(limit).all()
        result = []
        for item in items:
            result.append({
                "item_id": item.id, "position_number": item.position_number, "name": item.name,
                "code_sn": item.code_sn, "unit": item.unit, "volume": float(item.volume) if item.volume else 0,
                "price": float(item.price) if item.price else 0, "total_amount": float(item.total_amount) if item.total_amount else 0,
                "enstru_code": item.enstru_code, "enstru_name": item.enstru_name, "match_type": item.match_type,
                "match_score": item.match_score, "match_reason": item.match_reason, "can_edit": True
            })
        return {"items": result, "total": total_count, "skip": skip, "limit": limit}

    def search_enstru_catalog(self, db: Session, query: str, limit: int = 20):
        """Поиск в официальном справочнике ЕНС ТРУ"""
        q = query.strip()
        if not q or len(q) < 2: return []
        results = db.query(Enstru).filter(or_(Enstru.code.ilike(f"%{q}%"), Enstru.name_rus.ilike(f"%{q}%"), Enstru.detail_rus.ilike(f"%{q}%"))).limit(limit).all()
        return [{"enstru_code": e.code, "enstru_name": e.name_rus, "detail": e.detail_rus, "standard": e.standard, "source": "enstru_catalog"} for e in results]

    def search_enstru_in_reestr(self, db: Session, query: str, limit: int = 20):
        """
        Расширенный поиск в реестре КТП (Postgres JSONB)
        - Без лимита (возвращает все записи)
        - Только записи с ДВС > 0
        """
        q = query.strip()
        if not q or len(q) < 2: return []

        # Поиск по записям, где ЕСТЬ коды ЕНСТРУ и ДВС > 0
        results = db.query(Reestr_KTP).filter(
            and_(
                Reestr_KTP.enstru_codes.isnot(None),
                text("jsonb_array_length(enstru_codes) > 0"),
                text("NULLIF(REGEXP_REPLACE(dvc_percent, '[^0-9.]', '', 'g'), '')::numeric > 0"),
                or_(
                    Reestr_KTP.product_name.ilike(f"%{q}%"),
                    Reestr_KTP.company_name.ilike(f"%{q}%"),
                    Reestr_KTP.bin_iin.ilike(f"%{q}%"),
                    cast(Reestr_KTP.enstru_codes, String).ilike(f"%{q}%"),
                    cast(Reestr_KTP.enstru_names, String).ilike(f"%{q}%")
                )
            )
        ).order_by(
            case((Reestr_KTP.product_name.ilike(f"%{q}%"), 1), else_=2)
        ).all()
        
        matches = []
        seen = set()
        for r in results:
            codes = r.enstru_codes or []
            names = r.enstru_names or []
            for i in range(max(len(codes), len(names))):
                c = codes[i] if i < len(codes) else None
                n = names[i] if i < len(names) else None
                if not c: continue
                
                if q.lower() in str(c).lower() or (n and q.lower() in n.lower()) or \
                   (r.product_name and q.lower() in r.product_name.lower()) or \
                   (r.company_name and q.lower() in r.company_name.lower()):
                    
                    key = (c, r.company_name, r.product_name)
                    if key not in seen:
                        matches.append({
                            "ktp_id": r.id, 
                            "enstru_code": c, 
                            "enstru_name": n or "—",
                            "company": r.company_name, 
                            "bin": r.bin_iin,
                            "product": r.product_name,
                            "dvc_percent": float(re.sub(r'[^0-9.]', '', r.dvc_percent)) if r.dvc_percent else 0,
                            "localization": r.localization_level,
                            "address": r.production_address,
                            "registry_date": r.registry_inclusion_date.strftime('%d.%m.%Y') if r.registry_inclusion_date else None,
                            "source": "reestr_ktp", 
                            "region": r.region_kato
                        })
                        seen.add(key)
        
        return matches

    def create_manual_match(self, db: Session, agsk_code: str, enstru_code: str, analyst_id: int, doc_id: Optional[int] = None, ktp_id: Optional[int] = None, dvc_percent: Optional[float] = None, product_name_ktp: Optional[str] = None):
        clean_agsk = str(agsk_code).strip()
        agsk = db.query(Agsk).filter(Agsk.code == clean_agsk).first()
        agsk_name = agsk.name_ru if agsk else "Неизвестный АГСК"
        match = db.query(AgskEnstruManualMatch).filter(AgskEnstruManualMatch.agsk_code == clean_agsk, AgskEnstruManualMatch.enstru_code == enstru_code, AgskEnstruManualMatch.ktp_id == ktp_id).first()
        if match:
            match.is_active = True; match.dvc_percent = dvc_percent; match.product_name_ktp = product_name_ktp; match.updated_at = datetime.utcnow()
        else:
            match = AgskEnstruManualMatch(agsk_code=clean_agsk, enstru_code=enstru_code, ktp_id=ktp_id, agsk_name_ru=agsk_name, enstru_name_ru=db.query(Enstru.name_rus).filter(Enstru.code == enstru_code).scalar(), product_name_ktp=product_name_ktp, dvc_percent=dvc_percent, created_by=analyst_id, psd_document_id=doc_id, is_active=True)
            db.add(match)
        db.commit()
        self._apply_library_to_all_documents(db, clean_agsk)
        return match

    def get_agsk_library(self, db: Session, agsk_code: str):
        return db.query(AgskEnstruManualMatch).filter(AgskEnstruManualMatch.agsk_code == agsk_code.strip(), AgskEnstruManualMatch.is_active == True).all()

    def remove_from_library(self, db: Session, match_id: int):
        match = db.query(AgskEnstruManualMatch).filter(AgskEnstruManualMatch.id == match_id).first()
        if match:
            agsk_code = match.agsk_code; match.is_active = False; db.commit()
            self._apply_library_to_all_documents(db, agsk_code)
        return {"status": "ok"}

    def _apply_library_to_all_documents(self, db: Session, agsk_code: str):
        from .agsk_enstru_matcher import AgskEnstruMatcher
        matcher = AgskEnstruMatcher(db); best = matcher.get_match_for_agsk(agsk_code)
        update_data = {"enstru_code": best["enstru_code"] if best else None, "enstru_name": best["enstru_name"] if best else None, "match_type": best["match_type"] if best else "none", "match_score": best["score"] if best else None, "match_reason": best["reason"] if best else None}
        db.query(PsdDocumentItem).filter(PsdDocumentItem.code_sn == agsk_code).update(update_data, synchronize_session=False)
        db.commit()

    def parse_psd_file(self, db: Session, doc_id: int, file_path: str):
        try:
            from .psd_analyzer.analyzer import clean_product_name, is_non_product, has_letters
            from .importers.kenml_parser import parse_kenml_file
            original_filename = os.path.basename(file_path)
            with open(file_path, 'rb') as f:
                file_content = f.read()
            class MockFile:
                def __init__(self, content, filename): self.file = io.BytesIO(content); self.filename = filename
            rows = parse_kenml_file(MockFile(file_content, original_filename))
            unique_items = {}
            for row in rows:
                try:
                    amount = float(row.get('Сумма', 0))
                    if amount <= 0.01: continue
                except: continue
                name, code_sn, category = str(row.get('Наименование', '')).strip(), str(row.get('КодСНБ', '')).strip(), str(row.get('Категория', '')).strip().lower()
                is_item = any(x in category for x in ['товар', 'материал', 'оборудование', 'изделие'])
                if category != '' and not is_item: continue
                if is_non_product(name) or (code_sn != '' and has_letters(code_sn)): continue
                key = (name, code_sn)
                if key not in unique_items:
                    unique_items[key] = {"position_number": str(row.get('№', '')).strip(), "name": name, "code_sn": code_sn, "clean_name": clean_product_name(name), "unit": str(row.get('Ед. изм.', '')).strip(), "volume": 0.0, "price": float(row.get('Цена', 0)) if row.get('Цена') else 0, "total_amount": 0.0}
                unique_items[key]['volume'] += float(row.get('Объем', 0)); unique_items[key]['total_amount'] += amount
            items_list = sorted(unique_items.values(), key=lambda x: x['total_amount'], reverse=True)
            db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id).delete()
            for item_data in items_list:
                db.add(PsdDocumentItem(document_id=doc_id, position_number=item_data.get('position_number'), name=item_data.get('name'), code_sn=item_data.get('code_sn'), unit=item_data.get('unit'), volume=item_data.get('volume'), price=item_data.get('price'), total_amount=item_data.get('total_amount'), clean_name=item_data.get('clean_name'), is_product=True, skip_search=False))
            db.commit()
            doc = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()
            if doc: doc.status = "PARSED"; db.commit()
            self._run_auto_matching_for_document(db, doc_id)
        except Exception as e:
            db.rollback(); doc = db.query(ExternalDocument).filter(ExternalDocument.id == doc_id).first()
            if doc: doc.status = "ERROR"; doc.error_message = str(e); db.commit()
            raise
    
    def _run_auto_matching_for_document(self, db: Session, doc_id: int):
        from .agsk_enstru_matcher import AgskEnstruMatcher
        matcher = AgskEnstruMatcher(db); items = db.query(PsdDocumentItem).filter(PsdDocumentItem.document_id == doc_id).all()
        for item in items:
            if item.code_sn:
                m = matcher.get_match_for_agsk(item.code_sn)
                if m: item.enstru_code, item.enstru_name, item.match_type, item.match_score, item.match_reason = m["enstru_code"], m["enstru_name"], m["match_type"], m["score"], m["reason"]
        db.commit()

    def export_matches_to_excel(self, db: Session, format_type: str = "full"):
        if format_type == "only_manual": matches = db.query(AgskEnstruManualMatch).filter(AgskEnstruManualMatch.is_active == True).all()
        elif format_type == "only_auto": matches = db.query(AgskEnstruExclusive).all()
        else: matches = list(db.query(AgskEnstruExclusive).all()) + list(db.query(AgskEnstruManualMatch).filter(AgskEnstruManualMatch.is_active == True).all())
        data = []
        for m in matches:
            created_at = getattr(m, 'created_at', None)
            if created_at and hasattr(created_at, 'tzinfo') and created_at.tzinfo: created_at = created_at.replace(tzinfo=None)
            data.append({"Код АГСК": m.agsk_code, "Наименование АГСК": getattr(m, 'agsk_name_ru', None) or getattr(m, 'agsk_name_ru', None), "Код ЕНС ТРУ": m.enstru_code, "Наименование ЕНС ТРУ": getattr(m, 'enstru_name_ru', None) or getattr(m, 'enstru_name_ru', None), "Производитель (КТП)": getattr(m, 'product_name_ktp', '—'), "ДВС %": getattr(m, 'dvc_percent', '—'), "Тип": getattr(m, 'source', 'auto'), "Дата": created_at})
        df = pd.DataFrame(data); output_path = f"/tmp/library_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df.to_excel(output_path, index=False, engine='openpyxl')
        return {"file_path": output_path, "record_count": len(data)}
