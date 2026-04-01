from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Plan(BaseModel):
    id: int
    plan_name: str
    year: int
    created_at: datetime

    class Config:
        from_attributes = True

class UserBase(BaseModel):
    iin: str
    full_name: str
    bin: Optional[str] = None
    org_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class UserCreate(UserBase):
    hashed_password: str

class UserLogin(BaseModel):
    iin: str
    password: str

class User(UserBase):
    id: int
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    plans: List[Plan] = []

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool

class TokenData(BaseModel):
    iin: Optional[str] = None
