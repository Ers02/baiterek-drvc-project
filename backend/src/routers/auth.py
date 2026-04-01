from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..utils.auth import authenticate_user, create_access_token
from ..database.database import get_db
from ..models.models import UserRole

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
