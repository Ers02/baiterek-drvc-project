from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class ManualMatchCreate(BaseModel):
    agsk_code: str
    enstru_code: str
    doc_id: Optional[int] = None
    ktp_id: Optional[int] = None
    source: str = "manual"
    product_name_ktp: Optional[str] = None
    dvc_percent: Optional[float] = None

class ExternalDocumentSchema(BaseModel):
    id: int
    doc_type: str
    bank_name: str
    received_at: datetime
    status: str
    file_path: str
    notes: Optional[str] = None
    assigned_to: Optional[int] = None
    assigned_at: Optional[datetime] = None

    class Config:
        from_attributes = True

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
    category: Optional[str] = None
    enstru_code: Optional[str] = None
    enstru_name: Optional[str] = None
    match_type: str
    match_score: Optional[int] = None
    match_reason: Optional[str] = None

    class Config:
        from_attributes = True
