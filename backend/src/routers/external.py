"""Router для приёма данных от дочерних организаций через API-ключ."""
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import os

from ..database.database import get_db
from ..utils.api_key_auth import verify_api_key
from ..models.api_key import ApiKey
from ..services import external_service
from ..schemas.psd import ExternalDocumentSchema

router = APIRouter(
    prefix="/external",
    tags=["External API"],
    dependencies=[Depends(verify_api_key)]
)


@router.post("/upload", response_model=ExternalDocumentSchema)
async def upload_external_document(
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
    external_id: Optional[str] = Form(None),  # ID документа во внешней системе
    callback_url: Optional[str] = Form(None),  # URL для отправки результата
    api_key: ApiKey = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    Загрузка документа от дочерней организации.

    Требуется заголовок X-API-Key с действительным API-ключом.

    - **file**: Файл документа (.kenml, .zip для PSD или .xlsx для SMETA)
    - **doc_type**: Тип документа (PSD или SMETA)
    - **bank_name**: Наименование банка/проекта
    - **received_at**: Дата и время отправки (ISO 8601)
    - **notes**: Дополнительные примечания
    - **sender_***: Данные отправителя (имя, фамилия, email и т.д.)
    - **external_id**: ID документа в вашей системе
    - **callback_url**: URL для отправки результата анализа
    """
    # Проверка расширения файла в зависимости от типа документа
    file_ext = os.path.splitext(file.filename)[1].lower()
    doc_type_upper = doc_type.upper()

    if doc_type_upper == "PSD":
        allowed_exts = ['.kenml', '.zip']
        if file_ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат файла для PSD: {file_ext}. Поддерживаются только .kenml и .zip"
            )
    elif doc_type_upper == "SMETA":
        allowed_exts = ['.xlsx', '.xls']
        if file_ext not in allowed_exts:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат файла для SMETA: {file_ext}. Поддерживаются только .xlsx и .xls"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Неизвестный тип документа: {doc_type}. Поддерживаются PSD и SMETA"
        )
    
    # Добавляем информацию об организации в примечания
    org_info = f"[Org: {api_key.organization_name}]"
    full_notes = f"{org_info} {notes or ''}".strip()
    
    result = external_service.upload_external_document(
        db=db,
        file=file,
        doc_type=doc_type,
        bank_name=bank_name,
        received_at=received_at,
        notes=full_notes,
        sender_first_name=sender_first_name,
        sender_last_name=sender_last_name,
        sender_patronymic=sender_patronymic,
        sender_email=sender_email,
        sender_phone=sender_phone,
        external_id=external_id,
        callback_url=callback_url
    )
    
    return result


@router.get("/health")
async def health_check(api_key: ApiKey = Depends(verify_api_key)):
    """Проверка доступности API и валидности ключа."""
    return {
        "status": "ok",
        "organization": api_key.organization_name,
        "message": "API-ключ действителен"
    }
