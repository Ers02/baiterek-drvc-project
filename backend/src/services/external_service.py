import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from fastapi import UploadFile, HTTPException, BackgroundTasks
from ..models import models
from ..core.config import settings
from ..core.logger import logger
from .psd_analyzer.analyzer import PSDAnalyzer


def save_upload_file(file: UploadFile) -> str:
    """Сохраняет загруженный файл на диск."""
    if not os.path.exists(settings.UPLOAD_DIR):
        os.makedirs(settings.UPLOAD_DIR)
    
    filename = f"{uuid.uuid4()}_{file.filename}"
    path = os.path.join(settings.UPLOAD_DIR, filename)
    
    with open(path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)
        
    return path


def upload_external_document(
    db: Session, 
    file: UploadFile, 
    doc_type: str, 
    bank_name: str, 
    received_at: datetime,
    notes: str = None,
    sender_first_name: str = None,
    sender_last_name: str = None,
    sender_patronymic: str = None,
    sender_email: str = None,
    sender_phone: str = None
):
    """
    Загружает документ в систему (без запуска анализа).
    """
    try:
        file_path = save_upload_file(file)
        
        doc = models.ExternalDocument(
            doc_type=doc_type,
            bank_name=bank_name,
            received_at=received_at,
            file_path=file_path,
            status="NEW",
            notes=notes,
            sender_first_name=sender_first_name,
            sender_last_name=sender_last_name,
            sender_patronymic=sender_patronymic,
            sender_email=sender_email,
            sender_phone=sender_phone
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as e:
        logger.error(f"Error uploading external doc: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения файла")


def get_external_documents(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ExternalDocument).order_by(models.ExternalDocument.id.desc()).offset(skip).limit(limit).all()


def send_response_for_document(db: Session, doc_id: int):
    """
    Меняет статус документа на 'SENT' и фиксирует время завершения.
    """
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    doc.status = "SENT"
    doc.completed_at = func.now()
    db.commit()
    
    logger.info(f"Response sent for external document {doc_id}")
    return {"message": "Ответ успешно отправлен"}


def background_analyze_wrapper(task_id: str, content: bytes, doc_id: int):
    """
    Обертка для анализатора, чтобы обновить статус ExternalDocument по завершении.
    """
    from ..database.database import SessionLocal
    
    analyzer = PSDAnalyzer(task_id)
    analyzer.run(content)
    
    db = SessionLocal()
    try:
        task = db.query(models.AdminTask).filter(models.AdminTask.id == task_id).first()
        doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
        
        if doc and task:
            if task.status == "completed":
                doc.status = "DONE"
                doc.result_file_path = os.path.join(settings.REPORT_DIR, task.result_file)
            elif task.status == "error":
                doc.status = "ERROR"
                doc.error_message = task.error_details
            db.commit()
    except Exception as e:
        logger.error(f"Error syncing external doc status: {e}")
    finally:
        db.close()


def analyze_external_psd(db: Session, doc_id: int, background_tasks: BackgroundTasks):
    """
    Запускает анализ ПСД для внешнего документа.
    """
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    if doc.doc_type != "PSD":
        raise HTTPException(status_code=400, detail="Можно анализировать только ПСД")

    task_id = f"ext_{doc.id}_{uuid.uuid4()}"
    
    doc.status = "PROCESSING"
    db.commit()

    try:
        with open(doc.file_path, "rb") as f:
            content = f.read()
            
        task = models.AdminTask(
            id=task_id,
            status="pending",
            message="Запуск анализа внешнего файла..."
        )
        db.add(task)
        db.commit()

        background_tasks.add_task(background_analyze_wrapper, task_id, content, doc.id)
        
        return {"message": "Анализ запущен", "task_id": task_id}
        
    except Exception as e:
        doc.status = "ERROR"
        doc.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ошибка запуска: {e}")
