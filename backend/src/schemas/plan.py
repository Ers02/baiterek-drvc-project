from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from ..models.models import NeedType, PlanStatus
from . import lookup as lookup_schema

# ========= Схемы для Версий Плана (ProcurementPlanVersion) =========

class ProcurementPlanVersionBase(BaseModel):
    status: PlanStatus
    total_amount: Decimal = Field(default=0)
    ktp_percentage: Optional[Decimal] = Field(default=0)
    import_percentage: Optional[Decimal] = Field(default=0)
    is_active: bool
    is_executed: bool = False

class ProcurementPlanVersion(ProcurementPlanVersionBase):
    id: int
    plan_id: int
    version_number: int
    created_at: datetime
    creator: Optional[lookup_schema.UserLookup] = None

    class Config:
        from_attributes = True

# ========= Схемы для Позиций Версии Плана (PlanItemVersion) =========

class PlanItemBase(BaseModel):
    trucode: str = Field(..., description="Код ЕНС ТРУ")
    unit_id: Optional[int] = None
    expense_item_id: int
    funding_source_id: int
    agsk_id: Optional[str] = None
    kato_purchase_id: Optional[int] = None
    kato_delivery_id: Optional[int] = None
    quantity: Decimal = Field(..., gt=0, description="Количество")
    price_per_unit: Decimal = Field(..., gt=0, description="Цена за единицу")
    is_ktp: bool = False
    is_resident: bool = False

class PlanItemCreate(PlanItemBase):
    pass

class PlanItemUpdate(PlanItemBase):
    trucode: Optional[str] = None
    unit_id: Optional[int] = None
    expense_item_id: Optional[int] = None
    funding_source_id: Optional[int] = None
    quantity: Optional[Decimal] = Field(None, gt=0)
    price_per_unit: Optional[Decimal] = Field(None, gt=0)
    is_ktp: Optional[bool] = None
    is_resident: Optional[bool] = None

class PlanItem(BaseModel):
    id: int
    version_id: int
    item_number: int
    need_type: NeedType
    trucode: str
    quantity: Decimal
    price_per_unit: Decimal
    total_amount: Decimal
    is_ktp: bool
    is_resident: bool
    is_deleted: bool
    created_at: datetime
    
    root_item_id: Optional[int] = None
    source_version_id: Optional[int] = None
    
    executed_quantity: Decimal = Field(default=0)
    executed_amount: Decimal = Field(default=0) # Новое поле

    enstru: Optional[lookup_schema.Enstru] = None
    unit: Optional[lookup_schema.Mkei] = None
    expense_item: Optional[lookup_schema.CostItem] = None
    funding_source: Optional[lookup_schema.SourceFunding] = None
    agsk: Optional[lookup_schema.Agsk] = None
    kato_purchase: Optional[lookup_schema.Kato] = None
    kato_delivery: Optional[lookup_schema.Kato] = None
    
    version: ProcurementPlanVersion

    class Config:
        from_attributes = True

class ProcurementPlanVersionWithItems(ProcurementPlanVersion):
    items: List[PlanItem] = []

# ========= Схемы для Плана Закупок (ProcurementPlan) =========

class ProcurementPlanBase(BaseModel):
    plan_name: str = Field(..., min_length=3, max_length=500)
    year: int

class ProcurementPlanCreate(ProcurementPlanBase):
    pass

class ProcurementPlan(ProcurementPlanBase):
    id: int
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True

# ========= Схемы для ответов API =========

class ProcurementPlanWithVersions(ProcurementPlan):
    """План со списком всех его версий (без позиций)."""
    versions: List[ProcurementPlanVersion] = []

class ProcurementPlanWithFullActiveVersion(ProcurementPlan):
    """План с полной информацией по активной версии, включая все ее позиции."""
    versions: List[ProcurementPlanVersionWithItems] = []

    def get_active_version(self) -> Optional[ProcurementPlanVersionWithItems]:
        for v in self.versions:
            if v.is_active:
                return v
        return None

# ========= Схемы для обновления статуса =========

class ProcurementPlanStatusUpdate(BaseModel):
    status: PlanStatus
