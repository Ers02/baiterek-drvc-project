from pydantic import BaseModel, ConfigDict
from typing import Optional

class KatoSchema(BaseModel):
    id: int
    parent_id: Optional[int] = 0
    code: str
    name_kz: str
    name_ru: str
    has_children: bool

    model_config = ConfigDict(from_attributes=True)
