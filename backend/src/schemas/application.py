from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApplicationBase(BaseModel):
    need_type: str
    enstru_code: Optional[str] = None
    enstru_name: Optional[str] = None
    enstru_specs: Optional[str] = None
    additional_specs: Optional[str] = None
    agsk_3: Optional[str] = None
    expense_item: Optional[str] = None
    funding_source: Optional[str] = None
    kato_purchase: Optional[str] = None
    kato_delivery: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[float] = None
    marketing_price: Optional[float] = None
    marketing_total: Optional[float] = None
    planned_total_no_vat: Optional[float] = None
    is_ktp: Optional[bool] = False
    ktp_applicable: Optional[bool] = False


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(ApplicationBase):
    pass


class ApplicationResponse(ApplicationBase):
    id: int
    number: int
    state: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True