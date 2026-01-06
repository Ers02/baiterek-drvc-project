from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal

class ExecutionBase(BaseModel):
    supplier_name: str = Field(..., max_length=500)
    supplier_bin: str = Field(..., max_length=12)
    residency_code: str = Field(..., max_length=50)
    origin_code: str = Field(..., max_length=50)
    
    contract_number: str = Field(..., max_length=100)
    contract_date: date
    
    contract_quantity: Decimal = Field(..., gt=0)
    contract_price_per_unit: Decimal = Field(..., gt=0)
    
    supply_volume_physical: Decimal = Field(..., gt=0)
    supply_volume_value: Decimal = Field(..., gt=0)

class ExecutionCreate(ExecutionBase):
    plan_item_id: int

class Execution(ExecutionBase):
    id: int
    plan_item_id: int
    contract_sum: Decimal

    class Config:
        from_attributes = True
