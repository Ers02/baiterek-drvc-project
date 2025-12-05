from pydantic import BaseModel
from typing import Optional

# Этот файл содержит базовые схемы справочников,
# чтобы избежать циклических импортов.

class Mkei(BaseModel):
    id: int
    code: str
    name_kz: str
    name_ru: str
    class Config: from_attributes = True

class Kato(BaseModel):
    id: int
    code: str
    name_kz: str
    name_ru: str
    class Config: from_attributes = True

class Agsk(BaseModel):
    id: int
    code: str
    name_ru: str
    class Config: from_attributes = True

class CostItem(BaseModel):
    id: int
    name_ru: str
    name_kz: str
    class Config: from_attributes = True

class SourceFunding(BaseModel):
    id: int
    name_ru: str
    name_kz: str
    class Config: from_attributes = True

class Enstru(BaseModel):
    id: int
    code: str
    name_ru: str
    name_kz: str
    type_ru: str
    specs_ru: Optional[str] = None
    class Config: from_attributes = True

class KTPInfo(BaseModel):
    bin_iin: str
    full_name: str
    actual_address: Optional[str] = None
    product_name_ru: Optional[str] = None
    class Config: from_attributes = True
