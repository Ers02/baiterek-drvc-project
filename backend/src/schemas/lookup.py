from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Схема для User (для отображения в других схемах)
class UserLookup(BaseModel):
    id: int
    full_name: str

    class Config:
        from_attributes = True

# Схема для Mkei
class Mkei(BaseModel):
    id: int
    code: str
    name_kz: str
    name_ru: str

    class Config:
        from_attributes = True

# Схема для Kato
class Kato(BaseModel):
    id: int
    code: str
    name_kz: str
    name_ru: str

    class Config:
        from_attributes = True

# Схема для Agsk
class Agsk(BaseModel):
    id: int
    group: str
    code: str
    name_ru: str
    standart: Optional[str] = None
    unit: Optional[str] = None

    class Config:
        from_attributes = True

# Схема для Cost_Item
class CostItem(BaseModel):
    id: int
    name_ru: str
    name_kz: str

    class Config:
        from_attributes = True

# Схема для Source_Funding
class SourceFunding(BaseModel):
    id: int
    name_ru: str
    name_kz: str

    class Config:
        from_attributes = True

# Схема для Enstru (Обновленная)
class Enstru(BaseModel):
    id: int
    code: str
    name_rus: Optional[str] = None
    name_kaz: Optional[str] = None
    name_eng: Optional[str] = None
    type_name: Optional[str] = None # GOODS, WORKS, SERVICES
    detail_rus: Optional[str] = None
    detail_kaz: Optional[str] = None
    detail_eng: Optional[str] = None
    uom: Optional[str] = None
    
    # Для совместимости со старым кодом (опционально, можно убрать, если везде обновим)
    @property
    def name_ru(self):
        return self.name_rus
    
    @property
    def name_kz(self):
        return self.name_kaz
        
    @property
    def type_ru(self):
        # Маппинг type_name на старый type_ru
        if self.type_name == 'GOODS': return 'Товар'
        if self.type_name == 'WORKS': return 'Работа'
        if self.type_name == 'SERVICES': return 'Услуга'
        return self.type_name

    @property
    def specs_ru(self):
        return self.detail_rus

    @property
    def specs_kz(self):
        return self.detail_kaz

    class Config:
        from_attributes = True

# --- Схемы для ответа эндпоинта редактирования ---

class InitialOptions(BaseModel):
    enstru: Optional[Enstru] = None
    kato_purchase: Optional[Kato] = None
    kato_delivery: Optional[Kato] = None
    agsk: Optional[Agsk] = None
    cost_item: Optional[CostItem] = None
    source_funding: Optional[SourceFunding] = None
    mkei: Optional[Mkei] = None
