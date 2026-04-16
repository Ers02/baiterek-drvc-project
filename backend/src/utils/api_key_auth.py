"""Авторизация по API-ключу для внешних организаций."""
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import hashlib
from ..database.database import get_db
from ..models.api_key import ApiKey


async def verify_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> ApiKey:
    """
    Проверяет API-ключ из заголовка X-API-Key.
    Возвращает объект ApiKey при успешной проверке.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API-ключ отсутствует. Передайте заголовок X-API-Key",
            headers={"WWW-Authenticate": "ApiKey"}
        )
    
    # Хешируем переданный ключ для сравнения с БД
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()[:64]
    
    api_key = db.query(ApiKey).filter(
        ApiKey.key == key_hash,
        ApiKey.is_active == True
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный API-ключ"
        )
    
    # Проверка срока действия
    if api_key.expires_at and api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Срок действия API-ключа истёк"
        )
    
    # Обновляем статистику использования
    api_key.last_used_at = datetime.utcnow()
    api_key.request_count += 1
    db.commit()
    
    return api_key
