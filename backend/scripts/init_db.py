import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.database import SessionLocal
from src.models import models
from src.utils.auth import get_password_hash
from src.core.config import settings

def create_first_admin():
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже админ
        admin = db.query(models.User).filter(models.User.role == models.UserRole.ADMIN).first()
        
        if admin:
            print("Администратор уже существует.")
            return

        # Если нет, создаем
        print("Создание первого администратора...")
        
        hashed_password = get_password_hash(settings.ADMIN_PASSWORD)
        
        new_admin = models.User(
            iin=settings.ADMIN_USERNAME,
            full_name="Administrator",
            hashed_password=hashed_password,
            role=models.UserRole.ADMIN,
            is_active=True
        )
        
        db.add(new_admin)
        db.commit()
        
        print(f"Администратор создан. Логин: {settings.ADMIN_USERNAME}, Пароль: {settings.ADMIN_PASSWORD}")

    finally:
        db.close()

if __name__ == "__main__":
    create_first_admin()
