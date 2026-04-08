from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..services.kato_service import KatoService
from ..schemas.kato_schema import KatoSchema

router = APIRouter()

@router.get("/", response_model=List[KatoSchema])
def read_kato_children(parent_id: Optional[int] = 0, db: Session = Depends(get_db)):
    """Получает список КАТО (дочерние элементы для parent_id)"""
    return KatoService.get_kato_children(db, parent_id=parent_id)

@router.get("/{kato_id}", response_model=KatoSchema)
def read_kato_by_id(kato_id: int, db: Session = Depends(get_db)):
    """Получает детали одного КАТО"""
    kato = KatoService.get_kato_by_id(db, kato_id)
    if not kato:
        raise HTTPException(status_code=404, detail="Kato not found")
    return kato

@router.get("/{kato_id}/parents", response_model=List[KatoSchema])
def read_kato_parents(kato_id: int, db: Session = Depends(get_db)):
    """Получает полную цепочку родительских элементов"""
    return KatoService.get_kato_parents(db, kato_id)
