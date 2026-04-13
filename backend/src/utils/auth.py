from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from ..database.database import get_db
from ..models.models import User, UserRole
from ..core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password, hashed_password):
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


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


def authenticate_user(db: Session, iin: str, password: str) -> Optional[User]:
    """
    Ищет пользователя по ИИН и проверяет пароль.
    """
    user = db.query(User).filter(User.iin == iin).first()
    if not user:
        return None

    if not verify_password(password, user.hashed_password):
        return None
        
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Декодирует токен и возвращает объект User из БД.
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


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Зависимость для проверки прав администратора (полный контроль).
    Теперь включает аналитика ДРВЦ для доступа к admin эндпоинтам.
    """
    if current_user.role in [UserRole.ADMIN, UserRole.ANALYST_DRVC]:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Требуются права администратора или аналитика ДРВЦ"
    )


def get_current_analyst_drvc(current_user: User = Depends(get_current_user)) -> User:
    """
    Зависимость для проверки прав аналитика ДРВЦ.
    Аналитик ДРВЦ имеет полные права на управление планами и позициями.
    """
    if current_user.role == UserRole.ANALYST_DRVC:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Требуются права аналитика ДРВЦ"
    )


def get_current_admin_or_analyst(current_user: User = Depends(get_current_user)) -> User:
    """
    Зависимость для проверки прав администратора или аналитика ДРВЦ.
    """
    if current_user.role in [UserRole.ADMIN, UserRole.ANALYST_DRVC]:
        return current_user
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Требуются права администратора или аналитика ДРВЦ"
    )
