from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from ..database.base import Base


class ApiKey(Base):
    """Модель для хранения API-ключей дочерних организаций."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    organization_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Статус ключа
    is_active = Column(Boolean, default=True)
    
    # Ограничения (опционально)
    allowed_ips = Column(Text, nullable=True)  # JSON список IP
    
    # Статистика использования
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    request_count = Column(Integer, default=0)
    
    # Даты
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, nullable=True)  # ID администратора, создавшего ключ
