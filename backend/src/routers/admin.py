from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import urllib.parse
from ..database.database import get_db
from ..models import models
from ..models.api_key import ApiKey
from ..schemas import user as user_schema
from ..utils.auth import get_current_admin, get_current_director_or_admin
from ..services import external_service
from ..core.config import settings
import secrets
import hashlib

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


# --- Внешние документы ---

@router.post("/external/upload")
def upload_external_doc(
        file: UploadFile = File(...),
        doc_type: str = Form(...),  # PSD или SMETA
        bank_name: str = Form(...),
        received_at: datetime = Form(...),
        notes: Optional[str] = Form(None),
        sender_first_name: Optional[str] = Form(None),
        sender_last_name: Optional[str] = Form(None),
        sender_patronymic: Optional[str] = Form(None),
        sender_email: Optional[str] = Form(None),
        sender_phone: Optional[str] = Form(None),
        external_id: Optional[str] = Form(None),
        db: Session = Depends(get_db)
):
    """Загрузить внешний документ (от банка)."""
    return external_service.upload_external_document(
        db, file, doc_type, bank_name, received_at, notes,
        sender_first_name=sender_first_name,
        sender_last_name=sender_last_name,
        sender_patronymic=sender_patronymic,
        sender_email=sender_email,
        sender_phone=sender_phone,
        external_id=external_id
    )


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


# --- Управление API-ключами ---

@router.get("/api-keys")
def get_all_api_keys(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_admin),
        skip: int = 0,
        limit: int = 100
):
    """Получить список всех API-ключей."""
    return db.query(ApiKey).offset(skip).limit(limit).all()


@router.post("/api-keys")
def create_api_key(
        organization_name: str = Form(...),
        description: Optional[str] = Form(None),
        expires_at: Optional[str] = Form(None),  # Строка ISO 8601 или null
        db: Session = Depends(get_db),
        current_user=Depends(get_current_admin)
):
    """
    Создать новый API-ключ для дочерней организации.

    Возвращает ключ только один раз — сохраните его!

    - expires_at: дата в формате ISO 8601 (2024-12-31T23:59:59) или не передавайте для бессрочного ключа
    """
    # Конвертируем строку в datetime если передано
    expires_dt: Optional[datetime] = None
    if expires_at and expires_at.lower() != "null":
        try:
            expires_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400,
                                detail="Неверный формат expires_at. Используйте ISO 8601 (2024-12-31T23:59:59)")

    # Генерируем уникальный ключ (64 символа)
    raw_key = secrets.token_urlsafe(48)
    # Хешируем для хранения в БД
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()[:64]

    api_key = ApiKey(
        key=key_hash,
        organization_name=organization_name,
        description=description,
        expires_at=expires_dt,
        created_by=current_user.id if hasattr(current_user, 'id') else None,
        is_active=True
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return {
        "id": api_key.id,
        "key": raw_key,  # Показываем только один раз!
        "organization_name": api_key.organization_name,
        "description": api_key.description,
        "is_active": api_key.is_active,
        "expires_at": api_key.expires_at,
        "created_at": api_key.created_at,
        "warning": "Сохраните этот ключ! Он будет показан только один раз."
    }


@router.delete("/api-keys/{key_id}")
def revoke_api_key(
        key_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_admin)
):
    """Отозвать (деактивировать) API-ключ."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API-ключ не найден")

    api_key.is_active = False
    db.commit()

    return {"message": f"API-ключ для '{api_key.organization_name}' деактивирован"}


@router.get("/api-keys/{key_id}/stats")
def get_api_key_stats(
        key_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_admin)
):
    """Получить статистику использования API-ключа."""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API-ключ не найден")

    return {
        "id": api_key.id,
        "organization_name": api_key.organization_name,
        "is_active": api_key.is_active,
        "request_count": api_key.request_count,
        "last_used_at": api_key.last_used_at,
        "created_at": api_key.created_at,
        "expires_at": api_key.expires_at
    }
