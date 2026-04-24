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
    sender_phone: str = None,
    external_id: str = None,
    callback_url: str = None
):
    """
    Загружает документ в систему (без запуска анализа).
    Если есть документ с таким же bank_name + external_id и назначенный аналитик,
    новый документ автоматически назначается тому же аналитику.
    """
    try:
        file_path = save_upload_file(file)

        # Проверяем, есть ли уже документ с таким bank_name + external_id
        # у которого есть назначенный аналитик
        assigned_analyst_id = None
        deadline_days = None
        if external_id and bank_name:
            existing_doc = db.query(models.ExternalDocument).filter(
                models.ExternalDocument.bank_name == bank_name,
                models.ExternalDocument.external_id == external_id,
                models.ExternalDocument.assigned_to.isnot(None)
            ).order_by(models.ExternalDocument.assigned_at.desc()).first()

            if existing_doc:
                assigned_analyst_id = existing_doc.assigned_to
                deadline_days = existing_doc.deadline_days
                logger.info(f"Auto-assigning to analyst {assigned_analyst_id} based on existing document {existing_doc.id}")

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
            sender_phone=sender_phone,
            external_id=external_id,
            callback_url=callback_url
        )

        # Авто-назначение если найден существующий документ
        if assigned_analyst_id:
            doc.assigned_to = assigned_analyst_id
            doc.assigned_at = func.now()
            doc.deadline_days = deadline_days
            if deadline_days:
                from datetime import timedelta
                current_date = datetime.now()
                added_days = 0
                while added_days < deadline_days:
                    current_date += timedelta(days=1)
                    if current_date.weekday() < 5:  # 0-4 это Пн-Пт
                        added_days += 1
                doc.deadline_at = current_date
            doc.status = "ASSIGNED_TO_ANALYST"

        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc
    except Exception as e:
        logger.error(f"Error uploading external doc: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сохранения файла")


def get_external_documents(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ExternalDocument).order_by(models.ExternalDocument.id.desc()).offset(skip).limit(limit).all()


import httpx

async def send_result_to_callback(db: Session, doc_id: int):
    """
    Отправляет результат (ZIP архив) в ДО через callback_url.
    Доступно только для директора после утверждения документа.
    """
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    if not doc.callback_url:
        raise HTTPException(status_code=400, detail="Callback URL не указан для этого документа")

    if doc.status not in ["APPROVED", "COMPLETED"]:
        raise HTTPException(status_code=400, detail="Документ должен быть утвержден перед отправкой в ДО")

    if not doc.result_file_path or not os.path.exists(doc.result_file_path):
        raise HTTPException(status_code=400, detail="ZIP архив с результатом не найден. Сначала утвердите документ.")

    try:
        # Подготовка файла для отправки
        with open(doc.result_file_path, "rb") as f:
            files = {"file": (f"Result_{doc.external_id or doc.id}.zip", f, "application/zip")}
            data = {
                "external_id": doc.external_id,
                "bank_name": doc.bank_name,
                "doc_type": doc.doc_type,
                "status": "COMPLETED",
                "message": "Анализ завершен успешно"
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(doc.callback_url, files=files, data=data)
                response.raise_for_status()

        # Обновляем статус после успешной отправки
        doc.status = "SENT"
        doc.completed_at = func.now()
        db.commit()

        logger.info(f"Result sent to callback for document {doc_id}, external_id: {doc.external_id}")
        return {"message": "Результат успешно отправлен в ДО", "callback_url": doc.callback_url}

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error sending result to callback: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=502, detail=f"Ошибка при отправке в ДО: HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Request error sending result to callback: {e}")
        raise HTTPException(status_code=502, detail=f"Ошибка соединения с ДО: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending result to callback: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при отправке результата: {str(e)}")


def send_response_for_document(db: Session, doc_id: int):
    """
    Меняет статус документа на 'SENT' и фиксирует время завершения.
    (Legacy метод для внутреннего использования)
    """
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    doc.status = "SENT"
    doc.completed_at = func.now()
    db.commit()

    logger.info(f"Response marked as sent for external document {doc_id}")
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
