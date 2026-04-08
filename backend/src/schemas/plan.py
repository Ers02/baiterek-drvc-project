from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from ..models.models import NeedType, PlanStatus
from . import lookup as lookup_schema

class PlanItemBase(BaseModel):
    trucode: str = Field(..., description="Код ЕНС ТРУ")
    unit_id: Optional[int] = None
    expense_item_id: int
    funding_source_id: int
    agsk_id: Optional[str] = None
    kato_purchase_id: Optional[int] = None
    kato_delivery_id: Optional[int] = None
    additional_specs: Optional[str] = None
    additional_specs_kz: Optional[str] = None
    quantity: Decimal = Field(..., gt=0, description="Количество")
    price_per_unit: Decimal = Field(..., gt=0, description="Цена за единицу")
    is_ktp: bool = False
    resident_share: Decimal = Field(default=100, ge=0, le=100)
    non_resident_reason: Optional[str] = None
    min_dvc_percent: Optional[Decimal] = Field(default=0, ge=0, le=100)
    original_unit_name: Optional[str] = None

class PlanItemCreate(PlanItemBase):
    pass

class PlanItemUpdate(PlanItemBase):
    trucode: Optional[str] = None
    unit_id: Optional[int] = None
    expense_item_id: Optional[int] = None
    funding_source_id: Optional[int] = None
    agsk_id: Optional[str] = None
    kato_purchase_id: Optional[int] = None
    kato_delivery_id: Optional[int] = None
    additional_specs: Optional[str] = None
    additional_specs_kz: Optional[str] = None
    quantity: Optional[Decimal] = Field(None, gt=0)
    price_per_unit: Optional[Decimal] = Field(None, gt=0)
    is_ktp: Optional[bool] = None
    resident_share: Optional[Decimal] = Field(None, ge=0, le=100)
    non_resident_reason: Optional[str] = None
    min_dvc_percent: Optional[Decimal] = Field(None, ge=0, le=100)
    original_unit_name: Optional[str] = None

class PlanItem(PlanItemBase):
    id: int
    version_id: int
    item_number: int
    need_type: NeedType
    total_amount: Decimal
    is_deleted: bool
    created_at: datetime
    root_item_id: Optional[int] = None
    source_version_id: Optional[int] = None
    revision_number: int = 0
    executed_quantity: Decimal = Field(default=0)
    executed_amount: Decimal = Field(default=0)
    min_dvc_percent: Decimal = Field(default=0)
    vc_amount: Decimal = Field(default=0)
    executed_vc_amount: Optional[Decimal] = Field(default=0)
    start_version_number: int
    
    enstru: Optional[lookup_schema.Enstru] = None
    unit: Optional[lookup_schema.Mkei] = None
    expense_item: Optional[lookup_schema.CostItem] = None
    funding_source: Optional[lookup_schema.SourceFunding] = None
    agsk: Optional[lookup_schema.Agsk] = None
    kato_purchase: Optional[lookup_schema.Kato] = None
    kato_delivery: Optional[lookup_schema.Kato] = None

    model_config = ConfigDict(from_attributes=True)

class ProcurementPlanVersionBase(BaseModel):
    status: PlanStatus
    total_amount: Decimal = Field(default=0)
    import_percentage: Optional[Decimal] = Field(default=0)
    vc_percentage: Optional[Decimal] = Field(default=0)
    vc_amount: Optional[Decimal] = Field(default=0)
    executed_vc_amount: Optional[Decimal] = Field(default=0)
    executed_vc_percentage: Optional[Decimal] = Field(default=0)
    is_active: bool
    is_executed: bool = False

class ProcurementPlanVersion(ProcurementPlanVersionBase):
    id: int
    plan_id: int
    version_number: int
    created_at: datetime
    creator: Optional[lookup_schema.UserLookup] = None

    model_config = ConfigDict(from_attributes=True)

class ProcurementPlanVersionWithItems(ProcurementPlanVersion):
    items: List[PlanItem] = []

class ProcurementPlanBase(BaseModel):
    plan_name: str = Field(..., min_length=3, max_length=500)
    year: int

class ProcurementPlanCreate(ProcurementPlanBase):
    pass

class PlanCreate(ProcurementPlanCreate): # Алиас для совместимости
    pass

class ProcurementPlan(ProcurementPlanBase):
    id: int
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class PlanModel(ProcurementPlan): # Алиас для совместимости
    pass

class ProcurementPlanWithVersions(ProcurementPlan):
    versions: List[ProcurementPlanVersion] = []

class ProcurementPlanWithFullActiveVersion(ProcurementPlan):
    versions: List[ProcurementPlanVersionWithItems] = []

    def get_active_version(self) -> Optional[ProcurementPlanVersionWithItems]:
        for v in self.versions:
            if v.is_active:
                return v
        return None

class ProcurementPlanStatusUpdate(BaseModel):
    status: PlanStatus

class PlanUpdate(ProcurementPlanStatusUpdate): # Алиас для совместимости
    pass
