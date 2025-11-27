# src/database/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Загружаем .env
load_dotenv()

# Больше НЕ используем Settings() для DATABASE_URL — читаем напрямую!
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./baiterek.db")

# Для SQLite — обязательно!
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()