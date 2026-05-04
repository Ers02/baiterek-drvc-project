from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import auth, plans, items, lookups, kato_router, execution_router, admin, psd_analyst, external, product_groups
from src.database.database import engine
from src.database.base import Base

# Создаём таблицы в БД (если их нет)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Байтерек — Портал Смет Закупок",
    description="Система для формирования смет закупок",
    version="2.1.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # URL вашего фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
api_router = FastAPI()
api_router.include_router(auth.router,include_in_schema=False)
api_router.include_router(plans.router,include_in_schema=False)
api_router.include_router(items.router,include_in_schema=False)
api_router.include_router(lookups.router,include_in_schema=False)
api_router.include_router(kato_router.router, prefix="/kato", tags=["kato"],include_in_schema=False)
api_router.include_router(execution_router.router,include_in_schema=False)
api_router.include_router(admin.router,include_in_schema=False) # Подключаем админку
api_router.include_router(psd_analyst.router,include_in_schema=False) # Подключаем аналитика ПСД
api_router.include_router(external.router) # API для дочерних организаций
api_router.include_router(product_groups.router,include_in_schema=False) # Библиотека групп/товаров

app.mount("/api", api_router)

@app.get("/")
def root():
    return {"message": "Байтерек API v2.1 работает!"}
