from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..utils.auth import authenticate_user, create_access_token, get_current_user
from ..database.database import get_db
from ..models.models import UserRole, User

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/login")
def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = authenticate_user(db, iin=form_data.username, password=form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный ИИН или пароль"
        )

    is_admin = user.role == UserRole.ADMIN
    # Добавляем роль и флаг админа в payload токена
    access_token = create_access_token(data={"sub": user.iin, "is_admin": is_admin, "role": user.role.value})

    return {"access_token": access_token, "token_type": "bearer", "is_admin": is_admin}


@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Возвращает информацию о текущем авторизованном пользователе."""
    # Проверяем, является ли пользователь директором или имеет делегированные права
    is_director = current_user.role in [UserRole.ADMIN, UserRole.DIRECTOR_DRVC]

    # Проверка делегирования: есть ли директор, который делегировал права текущему пользователю
    if not is_director:
        now = datetime.now(timezone.utc)
        delegator = db.query(User).filter(
            User.role == UserRole.DIRECTOR_DRVC,
            User.delegated_to_id == current_user.id,
            User.delegation_start <= now,
            User.delegation_end >= now
        ).first()
        is_director = delegator is not None

    return {
        "id": current_user.id,
        "iin": current_user.iin,
        "full_name": current_user.full_name,
        "role": current_user.role.value if current_user.role else None,
        "is_active": current_user.is_active,
        "email": current_user.email,
        "phone": current_user.phone,
        "bin": current_user.bin,
        "org_name": current_user.org_name,
        "is_director": is_director  # Флаг для фронтенда
    }
