from sqlalchemy.orm import Session
from ..models import models
from typing import List, Optional, Any

class DictionaryService:
    """Сервис для управления справочниками (MKEI, Cost Items, AGSK и т.д.)"""

    @staticmethod
    def get_list(db: Session, model: Any, query: Optional[str] = None, search_fields: List[str] = None, limit: int = 50):
        """Универсальный метод получения списка с поиском"""
        db_query = db.query(model)
        if query and search_fields:
            filters = [getattr(model, field).ilike(f"%{query}%") for field in search_fields]
            db_query = db_query.filter(models.or_(*filters))
        return db_query.limit(limit).all()

    @staticmethod
    def create_item(db: Session, model: Any, data: dict):
        item = model(**data)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    @staticmethod
    def update_item(db: Session, model: Any, item_id: int, data: dict):
        item = db.query(model).filter(model.id == item_id).first()
        if item:
            for key, value in data.items():
                setattr(item, key, value)
            db.commit()
            db.refresh(item)
        return item

    @staticmethod
    def delete_item(db: Session, model: Any, item_id: int):
        item = db.query(model).filter(model.id == item_id).first()
        if item:
            db.delete(item)
            db.commit()
            return True
        return False
