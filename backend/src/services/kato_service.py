from sqlalchemy.orm import Session
from ..models.models import Kato
from typing import List, Optional

class KatoService:
    """Сервис для работы с КАТО (Коды административно-территориальных объектов)"""

    @staticmethod
    def get_kato_children(db: Session, parent_id: Optional[int] = 0) -> List[Kato]:
        """Получает дочерние элементы КАТО"""
        kato_items = db.query(Kato).filter(Kato.parent_id == parent_id).all()
        
        # Мы добавляем атрибут has_children динамически. 
        # В идеале это можно сделать через property в модели, но для ООП-сервиса допустимо так.
        for item in kato_items:
            item.has_children = db.query(Kato.id).filter(Kato.parent_id == item.id).first() is not None
        return kato_items

    @staticmethod
    def get_kato_by_id(db: Session, kato_id: int) -> Optional[Kato]:
        """Получает элемент КАТО по ID"""
        item = db.query(Kato).filter(Kato.id == kato_id).first()
        if item:
            item.has_children = db.query(Kato.id).filter(Kato.parent_id == item.id).first() is not None
        return item

    @classmethod
    def get_kato_parents(cls, db: Session, kato_id: int) -> List[Kato]:
        """Получает список всех родительских элементов"""
        parents = []
        current = cls.get_kato_by_id(db, kato_id)
        
        while current and current.parent_id and current.parent_id != 0:
            parent = cls.get_kato_by_id(db, current.parent_id)
            if parent:
                parents.insert(0, parent)
                current = parent
            else:
                break
        return parents
