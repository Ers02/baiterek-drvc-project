from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from ..database.database import get_db
from ..schemas import lookup as lookup_schema
from ..models import models

router = APIRouter(
    prefix="/lookups",
    tags=["Lookups"],
)

@router.get("/check-ktp/{enstru_code}")
def check_ktp_by_enstru(enstru_code: str, db: Session = Depends(get_db)):
    """Проверяет, есть ли код ЕНС ТРУ в реестре КТП."""
    exists = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.ens_tru_code == enstru_code).first()
    return {"is_ktp": exists is not None}

@router.get("/mkei", response_model=List[lookup_schema.Mkei])
def get_mkei_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Mkei)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(models.Mkei.code.ilike(search_term), models.Mkei.name_ru.ilike(search_term)))
    return query.limit(50).all()

@router.get("/kato", response_model=List[lookup_schema.Kato])
def get_kato_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Kato)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(models.Kato.code.ilike(search_term), models.Kato.name_ru.ilike(search_term)))
    return query.limit(50).all()

@router.get("/agsk", response_model=List[lookup_schema.Agsk])
def get_agsk_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Agsk)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(models.Agsk.group.ilike(search_term),
                                 models.Agsk.code.ilike(search_term),
                                 models.Agsk.name_ru.ilike(search_term)))
    return query.limit(50).all()

@router.get("/cost-items", response_model=List[lookup_schema.CostItem])
def get_cost_item_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Cost_Item)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(models.Cost_Item.name_ru.ilike(search_term),
                                 models.Cost_Item.name_kz.ilike(search_term)))
    return query.limit(50).all()

@router.get("/source-funding", response_model=List[lookup_schema.SourceFunding])
def get_source_funding_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Source_Funding)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(models.Source_Funding.name_ru.ilike(search_term), models.Source_Funding.name_kz.ilike(search_term)))
    return query.limit(50).all()

@router.get("/enstru", response_model=List[lookup_schema.Enstru])
def get_enstru_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Enstru)
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                models.Enstru.code.ilike(search_term),
                models.Enstru.name_ru.ilike(search_term),
                models.Enstru.name_kz.ilike(search_term),
            )
        )
    return query.limit(50).all()
