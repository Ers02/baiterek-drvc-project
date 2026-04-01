from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import urllib.parse
from ..database.database import get_db
from ..models import models
from ..schemas import user as user_schema
from ..utils.auth import get_current_admin
from ..services import admin_service, external_service
from ..core.config import settings

router = APIRouter(
    prefix="/admin",
    tags=["Admin Panel"],
    dependencies=[Depends(get_current_admin)]
)

@router.get("/users", response_model=List[user_schema.User])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    users = db.query(models.User).offset(skip).limit(limit).all()
    return users

@router.get("/plans", response_model=List[user_schema.Plan])
def get_all_plans(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    plans = db.query(models.ProcurementPlan).order_by(models.ProcurementPlan.id.desc()).offset(skip).limit(limit).all()
    return plans

@router.post("/analyze-psd")
def analyze_psd(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    return admin_service.start_admin_analysis(file, background_tasks)

@router.get("/tasks/{task_id}")
def get_admin_task_status(task_id: str):
    return admin_service.get_admin_task_status(task_id)

@router.get("/tasks/{task_id}/result")
def get_admin_task_result(task_id: str):
    return admin_service.get_admin_task_result(task_id)

# --- Внешние документы ---

@router.post("/external/upload")
def upload_external_doc(
    file: UploadFile = File(...),
    doc_type: str = Form(...), # PSD или SMETA
    bank_name: str = Form(...),
    received_at: datetime = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Загрузить внешний документ (от банка)."""
    return external_service.upload_external_document(db, file, doc_type, bank_name, received_at, notes)

@router.get("/external/documents")
def get_external_docs(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Список внешних документов."""
    return external_service.get_external_documents(db, skip, limit)

@router.get("/external/{doc_id}/download")
def download_external_source(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Скачать исходный файл."""
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    filename = os.path.basename(doc.file_path)
    encoded_filename = urllib.parse.quote(filename)
        
    return FileResponse(
        doc.file_path, 
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{encoded_filename}"}
    )

@router.post("/external/{doc_id}/send-response")
def send_external_response(
    doc_id: int,
    db: Session = Depends(get_db)
):
    """Отправить ответ (сменить статус на SENT)."""
    return external_service.send_response_for_document(db, doc_id)

# --- Шаблоны смет и анализ ---
@router.post("/upload-estimate-template")
async def upload_estimate_template_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузка шаблона сметы для анализа."""
    return await admin_service.upload_estimate_template(db, file)

@router.get("/estimate-analysis")
async def get_estimate_analysis_endpoint(
    db: Session = Depends(get_db)
):
    """Получение данных для анализа сметы."""
    return admin_service.get_estimate_analysis(db)
