from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Literal
from datetime import datetime, timezone
from fastapi.responses import FileResponse
import os

from ..database.database import get_db
from ..models import models
from ..services.psd_analyst_service import PsdAnalystService
from ..utils.auth import get_current_admin, get_current_user
from ..schemas.psd import ManualMatchCreate, ExternalDocumentSchema, PsdItemsResponse, AgskLibraryItemSchema

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
def assign_document_to_me(doc_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Документ не найден")
    doc.assigned_to = current_user.id
    doc.assigned_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc)
    return doc

@router.get("/existing-matches", response_model=List[AgskLibraryItemSchema])
def get_all_existing_matches(db: Session = Depends(get_db)):
    """Получить все записи из библиотеки замен (Архив)"""
    return db.query(models.AgskReestrKtpMatch).filter(models.AgskReestrKtpMatch.is_active == True).all()

@router.get("/document-items/{doc_id}", response_model=PsdItemsResponse)
def get_document_items(doc_id: int, only_unmatched: bool = False, search: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return psd_service.get_document_items_with_matches(db, doc_id, only_unmatched, search, skip, limit)

@router.post("/documents/{doc_id}/parse")
def parse_psd_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Документ не найден")
    psd_service.parse_psd_file(db, doc_id, str(doc.file_path))
    return {"status": "success"}

@router.post("/manual-match", response_model=AgskLibraryItemSchema)
def create_manual_match(match_data: ManualMatchCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return psd_service.create_manual_match(db, **match_data.model_dump(), analyst_id=current_user.id)

@router.get("/agsk-library/{agsk_code}", response_model=List[AgskLibraryItemSchema])
def get_agsk_library(agsk_code: str, db: Session = Depends(get_db)):
    return psd_service.get_agsk_library(db, agsk_code)

@router.delete("/agsk-library/{match_id}")
def remove_from_library(match_id: int, db: Session = Depends(get_db)):
    return psd_service.remove_from_library(db, match_id)

@router.get("/search-enstru-reestr")
def search_enstru_reestr(
    query: str = Query(..., min_length=1),
    search_mode: Literal["all", "agsk", "name"] = Query(default="all"),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Поиск в реестре КТП.
    search_mode: all, agsk, name
    """
    return psd_service.search_enstru_in_reestr(
        db, query=query, limit=limit, search_mode=search_mode
    )

@router.get("/suggest-enstru-for-agsk")
def suggest_enstru_for_agsk(agsk_code: str = Query(...), limit: int = Query(10), db: Session = Depends(get_db)):
    """Умные рекомендации: КТП + Справочник"""
    return psd_service.get_recommendations_for_agsk(db, agsk_code, limit)

@router.get("/export-full-report")
def export_full_analysis_report(
    doc_id: Optional[int] = Query(None, description="Optional document ID to filter the report"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Экспорт полного отчета по аналитике ПСД в Excel.
    Если doc_id указан, экспортируется отчет по конкретному документу.
    Иначе - по всем сопоставлениям.
    """
    file_path = psd_service.export_full_analysis_report(db, doc_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Не удалось сгенерировать отчет")

    file_name = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/documents/{doc_id}/conclusion")
def generate_conclusion_docx(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Генерация официального заключения аналитика в DOCX"""
    file_path = psd_service.generate_psd_conclusion_docx(db, doc_id, current_user)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Не удалось сгенерировать заключение")

    file_name = f"Conclusion_PSD_{doc_id}.docx"
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
