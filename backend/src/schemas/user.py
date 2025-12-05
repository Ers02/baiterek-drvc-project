from pydantic import BaseModel
from typing import Optional
import datetime


class UserBase(BaseModel):
    iin: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    bin: Optional[str] = None
    org_name: Optional[str] = None


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime.datetime
    last_login_at: Optional[datetime.datetime] = None

    class Config:
        from_attributes = True
