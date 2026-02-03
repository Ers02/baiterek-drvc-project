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
    exists = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.enstru_code == enstru_code).first()
    return {"is_ktp": exists is not None}

@router.get("/ktp-suppliers/{enstru_code}", response_model=List[lookup_schema.KtpSupplier])
def get_ktp_suppliers(enstru_code: str, db: Session = Depends(get_db)):
    """Получить список поставщиков КТП по коду ЕНС ТРУ."""
    suppliers = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.enstru_code == enstru_code).all()
    return suppliers

@router.get("/supplier-by-bin/{bin_iin}", response_model=List[lookup_schema.KtpSupplier])
def get_supplier_by_bin(bin_iin: str, enstru_code: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Ищет поставщика по БИН.
    Возвращает список всех найденных сертификатов.
    """
    if enstru_code:
        # 1. Ищем все точные совпадения
        exact_matches = db.query(models.Reestr_KTP).filter(
            models.Reestr_KTP.bin_iin == bin_iin,
            models.Reestr_KTP.enstru_code == enstru_code
        ).all()
        
        if exact_matches:
            return exact_matches

    # 2. Если точных нет или enstru_code не передан, ищем просто по БИН (чтобы узнать название)
    any_match = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.bin_iin == bin_iin).first()
    
    if any_match:
        # Возвращаем один "виртуальный" объект с нулевым ВЦ и БЕЗ названия продукта
        return [lookup_schema.KtpSupplier(
            id=any_match.id,
            bin_iin=any_match.bin_iin,
            company_name=any_match.company_name,
            enstru_code=enstru_code if enstru_code else any_match.enstru_code,
            dvc_percent=0.0,
            product_name=None, # Исправлено: не возвращаем чужой продукт
            production_address=any_match.production_address,
            email=any_match.email,
            phone=any_match.phone
        )]
        
    return []

@router.get("/mkei", response_model=List[lookup_schema.Mkei])
def get_mkei_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Mkei)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(
            models.Mkei.code.ilike(search_term),
            models.Mkei.name_ru.ilike(search_term),
            models.Mkei.name_kz.ilike(search_term)
        ))
    
    result = query.limit(50).all()
    return result

@router.get("/kato", response_model=List[lookup_schema.Kato])
def get_kato_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Kato)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(
            models.Kato.code.ilike(search_term),
            models.Kato.name_ru.ilike(search_term),
            models.Kato.name_kz.ilike(search_term)
        ))
    
    result = query.limit(50).all()
    return result

@router.get("/agsk", response_model=List[lookup_schema.Agsk])
def get_agsk_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Agsk)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(
            models.Agsk.group.ilike(search_term),
            models.Agsk.code.ilike(search_term),
            models.Agsk.name_ru.ilike(search_term)
        ))
    
    result = query.limit(50).all()
    return result

@router.get("/cost-items", response_model=List[lookup_schema.CostItem])
def get_cost_item_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Cost_Item)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(
            models.Cost_Item.name_ru.ilike(search_term),
            models.Cost_Item.name_kz.ilike(search_term)
        ))
    
    result = query.limit(50).all()
    return result

@router.get("/source-funding", response_model=List[lookup_schema.SourceFunding])
def get_source_funding_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Source_Funding)
    if q:
        search_term = f"%{q}%"
        query = query.filter(or_(
            models.Source_Funding.name_ru.ilike(search_term),
            models.Source_Funding.name_kz.ilike(search_term)
        ))
    
    result = query.limit(50).all()
    return result

@router.get("/enstru", response_model=List[lookup_schema.Enstru])
def get_enstru_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Enstru)
    if q:
        search_term = f"%{q}%"
        query = query.filter(
            or_(
                models.Enstru.code.ilike(search_term),
                models.Enstru.name_rus.ilike(search_term),
                models.Enstru.name_kaz.ilike(search_term),
            )
        )
    
    result = query.limit(50).all()
    return result
