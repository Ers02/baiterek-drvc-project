from functools import lru_cache
from sqlalchemy.orm import Session
from ..models import models
from ..database.database import SessionLocal

# Используем отдельную сессию для кэша, чтобы не зависеть от сессии запроса
# Но так как мы кэшируем простые структуры данных (dict), сессия нужна только один раз

@lru_cache(maxsize=1)
def get_mkei_map():
    """Возвращает словарь {code: id} для МКЕИ."""
    db = SessionLocal()
    try:
        items = db.query(models.Mkei.code, models.Mkei.id).all()
        return {code: id for code, id in items}
    finally:
        db.close()

@lru_cache(maxsize=1)
def get_cost_item_map():
    """Возвращает словарь {id: id} для проверки существования статьи затрат."""
    db = SessionLocal()
    try:
        items = db.query(models.Cost_Item.id).all()
        return {id: id for id, in items}
    finally:
        db.close()

@lru_cache(maxsize=1)
def get_kato_map():
    """Возвращает словарь {code: id} для КАТО."""
    db = SessionLocal()
    try:
        items = db.query(models.Kato.code, models.Kato.id).all()
        return {code: id for code, id in items}
    finally:
        db.close()

@lru_cache(maxsize=1)
def get_agsk_map():
    """Возвращает словарь {code: code} для АГСК."""
    db = SessionLocal()
    try:
        items = db.query(models.Agsk.code).all()
        return {code: code for code, in items}
    finally:
        db.close()

def clear_cache():
    """Очищает кэш (вызывать при обновлении справочников)."""
    get_mkei_map.cache_clear()
    get_cost_item_map.cache_clear()
    get_kato_map.cache_clear()
    get_agsk_map.cache_clear()
