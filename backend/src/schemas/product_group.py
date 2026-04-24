from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class ProductGroupBase(BaseModel):
    """Базовая схема для группы/товара"""
    name: str  # Название группы/товара

    # Коды справочников - только массив строк
    oked_codes: List[str] = []      # ["A.01.11.1", "A.01.12.0"]
    kpved_codes: List[str] = []     # ["01.11.11", "01.12.12"]
    enstru_codes: List[str] = []    # ["001.001.001"]
    agsk3_codes: List[str] = []     # ["10001000"]
    tnved_codes: List[str] = []     # ["0101.21.001"]

    # Коды product_code из реестра КТП - массив строк для связи
    reestr_ktp_codes: List[str] = []  # ["PRD-001", "PRD-002"]


class ProductGroupCreate(ProductGroupBase):
    """Схема для создания группы"""
    pass


class ProductGroupUpdate(ProductGroupBase):
    """Схема для обновления группы"""
    pass


class ProductGroupResponse(ProductGroupBase):
    """Схема для ответа с группой"""
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    class Config:
        from_attributes = True


class ProductGroupListItem(BaseModel):
    """Краткая информация о группе для списка"""
    id: int
    name: str
    created_at: Optional[datetime] = None

    # Количество кодов по каждому справочнику и КТП
    oked_count: int = 0
    kpved_count: int = 0
    enstru_count: int = 0
    agsk3_count: int = 0
    tnved_count: int = 0
    reestr_ktp_count: int = 0

    class Config:
        from_attributes = True


# --- Схемы для наборов групп ---

class ProductGroupSetItemBase(BaseModel):
    """Элемент набора групп"""
    group_id: int
    order: int = 0


class ProductGroupSetItemCreate(ProductGroupSetItemBase):
    pass


class ProductGroupSetItemResponse(ProductGroupSetItemBase):
    id: int
    group: Optional[ProductGroupResponse] = None

    class Config:
        from_attributes = True


class ProductGroupSetBase(BaseModel):
    """Базовая схема для набора групп"""
    name: str
    description: Optional[str] = None


class ProductGroupSetCreate(ProductGroupSetBase):
    """Схема для создания набора с группами"""
    group_ids: List[int] = []


class ProductGroupSetResponse(ProductGroupSetBase):
    """Схема для ответа с набором"""
    id: int
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None
    items: List[ProductGroupSetItemResponse] = []

    class Config:
        from_attributes = True


class ProductGroupSetListItem(BaseModel):
    """Краткая информация о наборе для списка"""
    id: int
    name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    groups_count: int = 0

    class Config:
        from_attributes = True
