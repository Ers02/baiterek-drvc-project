from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, text, cast, String
from typing import List, Optional
from datetime import datetime, timezone

from ..database.database import get_db
from ..models import models
from ..utils.auth import get_current_admin, get_current_user
from ..services.psd_analyst_service import PsdAnalystService
from ..services.agsk_enstru_matcher import AgskEnstruMatcher
from ..schemas.psd import ManualMatchCreate, ExternalDocumentSchema
from ..utils.text_utils import tokenize, score_pair # Импортируем score_pair из text_utils

router = APIRouter(
    prefix="/psd-analyst",
    tags=["PSD Analyst"],
    dependencies=[Depends(get_current_admin)]
)

psd_service = PsdAnalystService()

@router.get("/documents", response_model=List[ExternalDocumentSchema])
def get_psd_documents(
    doc_status: Optional[str] = Query(None, alias="status"),
    assigned_to_me: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.ExternalDocument).filter(models.ExternalDocument.doc_type == "PSD")
    if doc_status:
        query = query.filter(models.ExternalDocument.status == doc_status)
    if assigned_to_me:
        query = query.filter(models.ExternalDocument.assigned_to == current_user.id)
    return query.order_by(models.ExternalDocument.received_at.desc()).all()

@router.post("/documents/{doc_id}/assign", response_model=ExternalDocumentSchema)
def assign_document_to_me(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Документ не найден")
    doc.assigned_to = current_user.id
    doc.assigned_at = datetime.now(timezone.utc)
    doc.status = "ASSIGNED"
    db.commit()
    db.refresh(doc)
    return doc

@router.get("/document-items/{doc_id}")
def get_document_items(doc_id: int, only_unmatched: bool = Query(False), search: Optional[str] = Query(None), skip: int = Query(0), limit: int = Query(50), db: Session = Depends(get_db)):
    return psd_service.get_document_items_with_matches(db, doc_id, only_unmatched, search, skip, limit)

@router.post("/documents/{doc_id}/parse")
def parse_psd_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Документ не найден")
    psd_service.parse_psd_file(db, doc_id, str(doc.file_path))
    return {"message": "Парсинг завершен"}

@router.post("/manual-match")
def create_manual_match(match_data: ManualMatchCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return psd_service.create_manual_match(db=db, agsk_code=match_data.agsk_code, enstru_code=match_data.enstru_code, analyst_id=current_user.id, doc_id=match_data.doc_id, ktp_id=match_data.ktp_id, dvc_percent=match_data.dvc_percent, product_name_ktp=match_data.product_name_ktp)

@router.get("/agsk-library/{agsk_code}")
def get_agsk_library(agsk_code: str, db: Session = Depends(get_db)):
    return psd_service.get_agsk_library(db, agsk_code)

@router.delete("/agsk-library/{match_id}")
def remove_from_library(match_id: int, db: Session = Depends(get_db)):
    return psd_service.remove_from_library(db, match_id)

@router.get("/search-enstru-reestr")
def search_enstru_reestr(query: str = Query(...), limit: int = Query(20), db: Session = Depends(get_db)):
    return psd_service.search_enstru_in_reestr(db, query, limit)

@router.get("/suggest-enstru-for-agsk")
def suggest_enstru_for_agsk(agsk_code: str = Query(...), limit: int = Query(10), db: Session = Depends(get_db)):
    """Умные рекомендации: КТП + Справочник"""
    clean_agsk = agsk_code.strip()
    
    # 1. Сначала берем всё из Реестра КТП по этому коду (это лучшие кандидаты)
    ktp_results = db.query(models.Reestr_KTP).filter(
        text("agsk3_codes::text ILIKE :q").params(q=f'%"{clean_agsk}"%')
    ).all()
    
    recommendations = []
    seen_codes = set()
    
    for r in ktp_results:
        codes = r.enstru_codes or []
        names = r.enstru_names or []
        for c, n in zip(codes, names):
            if c not in seen_codes:
                recommendations.append({
                    "enstru_code": c, "enstru_name": n, "score": 95, 
                    "reason": f"Из КТП ({r.company_name})", "ktp_id": r.id, 
                    "product": r.product_name, "dvc_percent": r.dvc_percent
                })
                seen_codes.add(c)

    # 2. Если мало рекомендаций, ищем по названию в справочнике
    if len(recommendations) < limit:
        item = db.query(models.PsdDocumentItem).filter(models.PsdDocumentItem.code_sn == clean_agsk).first()
        if item:
            tokens = tokenize(item.name)
            if tokens:
                search_q = or_(*[models.Enstru.name_rus.ilike(f"%{t}%") for t in tokens[:2]])
                catalog = db.query(models.Enstru).filter(search_q).limit(20).all()
                agsk_dict = {"full_name": item.name}
                for e in catalog:
                    if e.code not in seen_codes:
                        agsk_for_score = {"full_name": item.name, "name_ru": item.name, "standart": ""}
                        enstru_for_score = {"name_rus": e.name_rus, "detail_rus": e.detail_rus, "standard": e.standard}
                        
                        sc, _ = score_pair(agsk_for_score, enstru_for_score)
                        recommendations.append({
                            "enstru_code": e.code, "enstru_name": e.name_rus, 
                            "score": sc, "reason": "Похожее название", "source": "catalog",
                            "detail": e.detail_rus, "standard": e.standard
                        })
                        seen_codes.add(e.code)

    recommendations.sort(key=lambda x: x["score"], reverse=True)
    return recommendations[:limit]
