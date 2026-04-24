from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class AgskLibraryItemSchema(BaseModel):
    id: int
    agsk_code: str
    enstru_code: str
    enstru_name_ru: Optional[str] = None
    product_name_ktp: Optional[str] = None
    dvc_percent: Optional[float] = None
    is_active: bool
    
    model_config = ConfigDict(from_attributes=True)

class ManualMatchCreate(BaseModel):
    agsk_code: str
    enstru_code: str
    doc_id: Optional[int] = None
    ktp_id: Optional[int] = None
    product_name_ktp: Optional[str] = None
    dvc_percent: Optional[float] = None

class ExternalDocumentSchema(BaseModel):
    id: int
    doc_type: str
    bank_name: str
    
    # Данные отправителя
    sender_first_name: Optional[str] = None
    sender_last_name: Optional[str] = None
    sender_patronymic: Optional[str] = None
    sender_email: Optional[str] = None
    sender_phone: Optional[str] = None
    
    # Интеграция
    external_id: Optional[str] = None
    callback_url: Optional[str] = None
    
    received_at: datetime
    status: str
    file_path: str
    notes: Optional[str] = None
    
    # Назначение (Аналитик)
    assigned_to: Optional[int] = None
    assigned_at: Optional[datetime] = None
    assigned_user_name: Optional[str] = None

    # Дедлайн
    deadline_days: Optional[int] = None
    deadline_at: Optional[datetime] = None

    is_test: bool = False

    @field_validator("assigned_user_name", mode="before")
    @classmethod
    def get_assigned_user_name(cls, v, info):
        # Если значение пришло напрямую (через query join), возвращаем его
        if v: return v
        # Пытаемся достать из объекта модели через relationship
        obj = info.data.get("__pydantic_extra__", {}).get("assigned_user") if hasattr(info, "data") else None
        # В SQLAlchemy объекте при from_attributes=True мы можем получить доступ к атрибутам
        return None

    model_config = ConfigDict(from_attributes=True)

class PsdDocumentItemSchema(BaseModel):
    id: int
    document_id: int
    position_number: Optional[str] = None
    name: str
    code_sn: Optional[str] = None
    unit: Optional[str] = None
    volume: float
    price: float
    total_amount: float
    enstru_code: Optional[str] = None
    enstru_name: Optional[str] = None
    match_type: str
    match_score: Optional[int] = None
    match_reason: Optional[str] = None
    agsk_name_ru: Optional[str] = None
    agsk_full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class PsdItemsResponse(BaseModel):
    items: List[PsdDocumentItemSchema]
    total: int
    skip: int
    limit: int
