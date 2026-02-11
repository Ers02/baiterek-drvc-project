from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from ..database.database import get_db
from ..models.models import User
from ..core.config import settings

# --- Утилиты для паролей и токенов ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- Основные функции для аутентификации и авторизации ---

def authenticate_user(db: Session, iin: str, password: str) -> Optional[User]:
    """
    Ищет пользователя по ИИН и проверяет пароль.
    """
    user = db.query(User).filter(User.iin == iin).first()
    if not user:
        return None
        
    # Если у пользователя нет пароля (старый аккаунт), временно пускаем без пароля
    # В продакшене это нужно убрать!
    if not user.hashed_password:
        return user
        
    if not verify_password(password, user.hashed_password):
        return None
        
    return user

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Декодирует токен, извлекает ИИН пользователя и возвращает объект User из БД.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        iin: str = payload.get("sub")
        if iin is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.iin == iin).first()
    if user is None:
        raise credentials_exception
    return user
