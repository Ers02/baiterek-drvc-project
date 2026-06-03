import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database.base import Base

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"                           # Супер-администратор, может всё включая справочники
    DIRECTOR_DRVC = "DIRECTOR_DRVC"           # Директор ДРВЦ
    ANALYST_DRVC = "ANALYST_DRVC"             # Аналитик ДРВЦ
    ANALYST_MANAGER = "ANALYST_MANAGER"       # Менеджер аналитиков — утверждает сопоставления
    USER = "USER"                             # Обычный пользователь

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
    
    # Поля для делегирования полномочий
    delegated_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    delegation_start = Column(DateTime(timezone=True), nullable=True)
    delegation_end = Column(DateTime(timezone=True), nullable=True)

    plans = relationship("ProcurementPlan", back_populates="creator")
    delegated_user = relationship("User", remote_side=[id], foreign_keys=[delegated_to_id])
