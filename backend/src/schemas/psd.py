from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Any
from datetime import datetime
from decimal import Decimal


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

class ManualMatchStatusSchema(BaseModel):
    id: int
    enstru_code: str
    status: str  # 'pending' | 'approved' | 'rejected'
    matched_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

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
    not_in_ktp_registry: bool = False
    agsk_name_ru: Optional[str] = None
    agsk_full_name: Optional[str] = None
    item_type: Optional[str] = "GOODS"
    current_manual_match: Optional[Any] = None
    model_config = ConfigDict(from_attributes=True)

class PsdItemsResponse(BaseModel):
    items: List[PsdDocumentItemSchema]
    total: int
    skip: int
    limit: int
    pending_match_count: int = 0

class SaveMatchRequest(BaseModel):
    enstru_code: str

class AgskEnstruMatchSchema(BaseModel):
    id: int
    agsk_code: str
    enstru_code: str
    doc_id: Optional[int] = None
    item_id: Optional[int] = None
    item_name: Optional[str] = None
    matched_by: int
    analyst_name: Optional[str] = None
    matched_at: Optional[datetime] = None
    is_approved: bool
    is_active: bool
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    status: str  # 'pending' | 'approved' | 'rejected'

class AgskEnstruMatchesResponse(BaseModel):
    items: List[AgskEnstruMatchSchema]
    total: int
