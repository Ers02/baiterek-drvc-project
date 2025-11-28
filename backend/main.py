# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import auth, applications
from src.database.database import engine
from src.database.base import Base   # ← ВОТ ТАК!

# Создаём таблицы
Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="Байтерек — Портал заявок",
    description="Система подачи заявок с согласованием в банке",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(applications.router, prefix="/applications", tags=["applications"])

@app.get("/")
def root():
    return {"message": "Байтерек API работает!"}