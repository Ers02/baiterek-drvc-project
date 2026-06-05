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
        if v: return v
        obj = info.data.get("__pydantic_extra__", {}).get("assigned_user") if hasattr(info, "data") else None
        return None

    model_config = ConfigDict(from_attributes=True)


class SupplierSelectionSchema(BaseModel):
    """Выбор поставщика аналитиком для конкретной позиции ПСД."""
    id: int
    item_id: int
    agsk_code: str
    enstru_code: Optional[str] = None
    ktp_id: Optional[int] = None
    product_code: Optional[str] = None
    supplier_bin: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_product: Optional[str] = None
    dvc_percent: Optional[float] = None
    selected_by: int
    selected_at: Optional[datetime] = None
    library_match_id: Optional[int] = None
    # pending | active | rejected
    status: str
    is_active: bool
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ManualMatchStatusSchema(BaseModel):
    id: int
    enstru_code: str
    status: str  # 'pending' | 'active' | 'rejected'
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
    """Запрос аналитика на выбор поставщика из Реестра КТП для позиции ПСД."""
    enstru_code: str
    ktp_id: Optional[int] = None
    product_code: Optional[str] = None
    supplier_bin: Optional[str] = None
    supplier_name: Optional[str] = None
    supplier_product: Optional[str] = None
    dvc_percent: Optional[float] = None


class AgskEnstruMatchSchema(BaseModel):
    id: int
    agsk_code: str
    agsk_full_name: Optional[str] = None
    enstru_code: str
    enstru_name_rus: Optional[str] = None
    enstru_detail_rus: Optional[str] = None
    enstru_standard: Optional[str] = None
    created_by: int
    analyst_name: Optional[str] = None
    created_at: Optional[datetime] = None
    is_approved: bool
    is_active: bool
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    status: str  # 'pending' | 'approved' | 'rejected'


class AgskEnstruMatchesResponse(BaseModel):
    items: List[AgskEnstruMatchSchema]
    total: int


class CreateAgskEnstruMatchRequest(BaseModel):
    agsk_code: str
    enstru_code: str


class CreateAgskEnstruMatchBatchRequest(BaseModel):
    agsk_code: str
    enstru_codes: List[str]
