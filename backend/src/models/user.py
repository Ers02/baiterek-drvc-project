import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"               # Супер-администратор, может всё включая справочники
    ANALYST_DRVC = "analyst_drvc" # Аналитик ДРВЦ
    USER = "user"                 # Обычный пользователь

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    iin = Column(String(12), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    
    bin = Column(String(12), index=True)
    org_name = Column(String(500))
    email = Column(String(255))
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    plans = relationship("ProcurementPlan", back_populates="creator")
