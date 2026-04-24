from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Form, Body
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Literal
from datetime import datetime, timezone
from fastapi.responses import FileResponse
import os
import shutil
import uuid
import httpx

from ..database.database import get_db
from ..models import models
from ..services.psd_analyst_service import PsdAnalystService
from ..utils.auth import get_current_admin, get_current_user, get_current_director_or_admin
from ..schemas.psd import ManualMatchCreate, ExternalDocumentSchema, PsdItemsResponse, AgskLibraryItemSchema
from ..core.config import settings
from ..core.logger import logger

router = APIRouter(
    prefix="/psd-analyst",
    tags=["PSD Analyst"],
    dependencies=[Depends(get_current_admin)]
)

psd_service = PsdAnalystService()

@router.get("/documents")
def get_psd_documents(
    doc_status: Optional[str] = Query(None, alias="status"),
    assigned_to_me: bool = Query(False),
    is_test: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.ExternalDocument).options(joinedload(models.ExternalDocument.assigned_user))
    # Показываем все документы: PSD и SMETA

    if doc_status:
        query = query.filter(models.ExternalDocument.status == doc_status)
    
    if assigned_to_me:
        query = query.filter(models.ExternalDocument.assigned_to == current_user.id)
    
    if is_test is not None:
        query = query.filter(models.ExternalDocument.is_test == is_test)
    else:
        query = query.filter(models.ExternalDocument.is_test == False)
        
    docs = query.order_by(models.ExternalDocument.received_at.desc()).all()
    
    result = []
    for doc in docs:
        doc_dict = {c.name: getattr(doc, c.name) for c in doc.__table__.columns}
        doc_dict["assigned_user_name"] = doc.assigned_user.full_name if doc.assigned_user else None
        result.append(doc_dict)
        
    return result

@router.post("/documents/{doc_id}/assign-analyst")
def assign_to_analyst(
    doc_id: int,
    analyst_id: int = Query(...),
    days: int = Query(5, ge=1, le=10, description="Срок в рабочих днях (1-10)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """Директор назначает аналитика и срок выполнения."""
    if days < 1 or days > 10:
        raise HTTPException(status_code=400, detail="Срок выполнения должен быть от 1 до 10 рабочих дней")
    try:
        doc = psd_service.assign_to_analyst(db, doc_id, analyst_id, days)
        return {"status": "success", "deadline": doc.deadline_at}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/documents/{doc_id}/submit-approval")
def submit_for_approval(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Аналитик отправляет на утверждение директору."""
    try:
        psd_service.submit_for_approval(db, doc_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/documents/{doc_id}/approve")
def approve_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """Директор утверждает документ. Генерируется финальный ZIP."""
    try:
        psd_service.approve_document(db, doc_id, current_user)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/documents/{doc_id}/reject")
def reject_document(
    doc_id: int, 
    comment: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """Директор возвращает на доработку с комментарием."""
    try:
        psd_service.reject_document(db, doc_id, comment)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/delegate")
def delegate_authority(
    to_user_id: int = Query(...),
    days: int = Query(14),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """Директор делегирует права другому пользователю."""
    try:
        psd_service.delegate_authority(db, current_user.id, to_user_id, days)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analysts", response_model=List[dict])
def get_analysts_list(db: Session = Depends(get_db)):
    """Список аналитиков для назначения."""
    users = db.query(models.User).filter(models.User.role == models.UserRole.ANALYST_DRVC).all()
    return [{"id": u.id, "full_name": u.full_name} for u in users]

@router.get("/document-items/{doc_id}", response_model=PsdItemsResponse)
def get_document_items(doc_id: int, only_unmatched: bool = False, search: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return psd_service.get_document_items_with_matches(db, doc_id, only_unmatched, search, skip, limit)

@router.post("/manual-match", response_model=AgskLibraryItemSchema)
def create_manual_match(match_data: ManualMatchCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return psd_service.create_manual_match(db, **match_data.model_dump(), analyst_id=current_user.id)

@router.get("/documents/{doc_id}/download-result")
def download_result_zip(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc or not doc.result_file_path or not os.path.exists(doc.result_file_path):
        raise HTTPException(status_code=404, detail="Файл результата не найден")

    return FileResponse(
        path=doc.result_file_path,
        filename=f"Analysis_Result_{doc_id}.zip",
        media_type="application/zip"
    )

@router.get("/existing-matches", response_model=List[AgskLibraryItemSchema])
def get_all_existing_matches(db: Session = Depends(get_db)):
    return db.query(models.AgskReestrKtpMatch).filter(models.AgskReestrKtpMatch.is_active == True).all()

@router.post("/documents/{doc_id}/parse")
def parse_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Выбираем парсер в зависимости от типа документа
    if doc.doc_type == "SMETA":
        psd_service.parse_smeta_file(db, doc_id, str(doc.file_path))
    elif doc.doc_type == "PSD":
        psd_service.parse_psd_file(db, doc_id, str(doc.file_path))
    else:
        raise HTTPException(status_code=400, detail=f"Неизвестный тип документа: {doc.doc_type}")

    return {"status": "success", "doc_type": doc.doc_type}

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
    return psd_service.search_enstru_in_reestr(db, query=query, limit=limit, search_mode=search_mode)

@router.get("/suggest-enstru-for-agsk")
def suggest_enstru_for_agsk(agsk_code: str = Query(...), limit: int = Query(10), db: Session = Depends(get_db)):
    return psd_service.get_recommendations_for_agsk(db, agsk_code, limit)

@router.get("/export-full-report")
def export_full_analysis_report(
    doc_id: int = Query(..., description="Document ID to export"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
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
    file_path = psd_service.generate_psd_conclusion_docx(db, doc_id, current_user)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Не удалось сгенерировать заключение")

    file_name = f"Conclusion_PSD_{doc_id}.docx"
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@router.post("/documents/{doc_id}/send-to-do")
async def send_result_to_do(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """
    Отправляет результат анализа (ZIP архив) в дочернюю организацию через callback_url.
    Доступно только директору после утверждения документа.
    """
    from ..services.external_service import send_result_to_callback
    result = await send_result_to_callback(db, doc_id)
    return result
