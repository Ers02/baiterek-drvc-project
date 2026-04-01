from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..services import kato_service
from ..schemas.kato_schema import KatoSchema

router = APIRouter()


@router.get("/", response_model=List[KatoSchema])
def read_kato_children(parent_id: Optional[int] = 0, db: Session = Depends(get_db)):
    kato_items = kato_service.get_kato_children(db, parent_id=parent_id)
    return [KatoSchema(**kato) for kato in kato_items]


@router.get("/{kato_id}", response_model=KatoSchema)
def read_kato_by_id(kato_id: int, db: Session = Depends(get_db)):
    kato = kato_service.get_kato_by_id(db, kato_id)
    if kato is None:
        raise HTTPException(status_code=404, detail="Kato not found")
    return KatoSchema(**kato)


@router.get("/{kato_id}/parents", response_model=List[KatoSchema])
def read_kato_parents(kato_id: int, db: Session = Depends(get_db)):
    parents = kato_service.get_kato_parents(db, kato_id)
    return [KatoSchema(**parent) for parent in parents]
