from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Form
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
from ..utils.auth import get_current_admin, get_current_user
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
    query = query.filter(models.ExternalDocument.doc_type == "PSD")
    
    if doc_status:
        query = query.filter(models.ExternalDocument.status == doc_status)
    
    if assigned_to_me:
        query = query.filter(models.ExternalDocument.assigned_to == current_user.id)
    
    # Фильтр по тестовым проектам
    if is_test is not None:
        query = query.filter(models.ExternalDocument.is_test == is_test)
    else:
        query = query.filter(models.ExternalDocument.is_test == False)
        
    docs = query.order_by(models.ExternalDocument.received_at.desc()).all()
    
    # Формируем ответ вручную, чтобы передать имя пользователя
    result = []
    for doc in docs:
        doc_dict = {c.name: getattr(doc, c.name) for c in doc.__table__.columns}
        doc_dict["assigned_user_name"] = doc.assigned_user.full_name if doc.assigned_user else None
        # Добавляем completed_at если он есть
        result.append(doc_dict)
        
    return result

@router.delete("/documents/{doc_id}")
def delete_psd_document(doc_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    if doc.file_path and os.path.exists(doc.file_path):
        try:
            os.remove(doc.file_path)
        except:
            pass

    db.delete(doc)
    db.commit()
    return {"status": "success"}

@router.post("/upload-test", response_model=ExternalDocumentSchema)
async def upload_test_psd(
    file: UploadFile = File(...),
    project_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Загрузка тестового файла. Сохраняется как один файл (zip или kenml).
    """
    upload_dir = os.path.abspath(os.path.join(settings.UPLOAD_DIR, "psd_test"))
    os.makedirs(upload_dir, exist_ok=True)
    
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.kenml', '.zip']:
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .kenml и .zip")
        
    unique_filename = f"test_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Сохраняем ОДИН файл (архив или kenml)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Создаем запись в БД
    doc = models.ExternalDocument(
        doc_type="PSD",
        bank_name=f"[ТЕСТ] {project_name}",
        received_at=datetime.now(timezone.utc),
        file_path=file_path,
        status="NEW",
        is_test=True,
        assigned_to=current_user.id,
        assigned_at=datetime.now(timezone.utc),
        notes=f"Тестовый проект. Оригинальный файл: {file.filename}"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    # Запускаем парсинг (сервис теперь сам разберется, ZIP это или KENML)
    try:
        psd_service.parse_psd_file(db, doc.id, file_path)
        return doc
    except Exception as e:
        doc.status = "ERROR"
        doc.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")

@router.post("/documents/{doc_id}/assign", response_model=ExternalDocumentSchema)
def assign_document_to_me(doc_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Документ не найден")
    doc.assigned_to = current_user.id
    doc.assigned_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(doc)
    return doc

@router.post("/documents/{doc_id}/finish")
async def finish_document_analysis(
    doc_id: int, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Завершить анализ и подготовить данные для отправки."""
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    doc.status = "COMPLETED"
    doc.completed_at = datetime.now(timezone.utc)
    
    # Генерация финального отчета
    report_path = psd_service.export_full_analysis_report(db, doc_id)
    doc.result_file_path = report_path
    
    db.commit()
    
    # Если есть callback_url, запускаем фоновую задачу для отправки
    if doc.callback_url:
        background_tasks.add_task(send_callback_to_external_system, doc.id, doc.callback_url, report_path)
        return {"status": "success", "message": "Анализ завершен. Результат будет отправлен по API."}
        
    return {"status": "success", "message": "Анализ успешно завершен."}

async def send_callback_to_external_system(doc_id: int, url: str, file_path: str):
    """Логика отправки результата внешней организации по API."""
    try:
        async with httpx.AsyncClient() as client:
            with open(file_path, "rb") as f:
                files = {'file': (os.path.basename(file_path), f)}
                data = {'document_id': doc_id, 'status': 'completed'}
                response = await client.post(url, data=data, files=files, timeout=60.0)
                
                if response.status_code == 200:
                    logger.info(f"Successfully sent result for doc {doc_id} to {url}")
                else:
                    logger.error(f"Failed to send result for doc {doc_id} to {url}. Code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending callback for doc {doc_id}: {str(e)}")

@router.get("/existing-matches", response_model=List[AgskLibraryItemSchema])
def get_all_existing_matches(db: Session = Depends(get_db)):
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
    return psd_service.search_enstru_in_reestr(db, query=query, limit=limit, search_mode=search_mode)

@router.get("/suggest-enstru-for-agsk")
def suggest_enstru_for_agsk(agsk_code: str = Query(...), limit: int = Query(10), db: Session = Depends(get_db)):
    return psd_service.get_recommendations_for_agsk(db, agsk_code, limit)

@router.get("/export-full-report")
def export_full_analysis_report(
    doc_id: Optional[int] = Query(None, description="Optional document ID to filter the report"),
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
