from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, text, cast, String
from typing import List, Optional

from ..database.database import get_db
from ..schemas import lookup as lookup_schema
from ..models import models
from ..utils.auth import get_current_admin
from ..services.dictionary_service import DictionaryService

router = APIRouter(
    prefix="/lookups",
    tags=["Lookups"],
)

@router.get("/mkei", response_model=List[lookup_schema.Mkei])
def get_mkei_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    return DictionaryService.get_list(db, models.Mkei, q, ["code", "name_ru", "name_kz"])

@router.get("/kato", response_model=List[lookup_schema.Kato])
def get_kato_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    return DictionaryService.get_list(db, models.Kato, q, ["code", "name_ru", "name_kz"])

@router.get("/agsk", response_model=List[lookup_schema.Agsk])
def get_agsk_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    return DictionaryService.get_list(db, models.Agsk, q, ["code", "name_ru", "full_name"])

@router.get("/cost-items", response_model=List[lookup_schema.CostItem])
def get_cost_item_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    return DictionaryService.get_list(db, models.Cost_Item, q, ["name_ru", "name_kz"])

@router.get("/source-funding", response_model=List[lookup_schema.SourceFunding])
def get_source_funding_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    return DictionaryService.get_list(db, models.Source_Funding, q, ["name_ru", "name_kz"])

@router.get("/enstru", response_model=List[lookup_schema.Enstru])
def get_enstru_list(q: Optional[str] = None, db: Session = Depends(get_db)):
    return DictionaryService.get_list(db, models.Enstru, q, ["code", "name_rus", "name_kaz"])

@router.get("/check-ktp/{enstru_code}")
def check_ktp_by_enstru(enstru_code: str, db: Session = Depends(get_db)):
    exists = db.query(models.Reestr_KTP).filter(
        cast(models.Reestr_KTP.enstru_codes, String).ilike(f'%"%{enstru_code}%"%')
    ).first()
    return {"is_ktp": exists is not None}

@router.get("/ktp-suppliers/{enstru_code}", response_model=List[lookup_schema.KtpSupplier])
def get_ktp_suppliers(enstru_code: str, db: Session = Depends(get_db)):
    suppliers = db.query(models.Reestr_KTP).filter(
        cast(models.Reestr_KTP.enstru_codes, String).ilike(f'%"%{enstru_code}%"%')
    ).all()
    
    result = []
    for s in suppliers:
        dvc = 0.0
        if s.dvc_percent:
            try: dvc = float(str(s.dvc_percent).replace(',', '.'))
            except: pass
            
        result.append(lookup_schema.KtpSupplier(
            id=s.id, bin_iin=s.bin_iin, company_name=s.company_name,
            enstru_code=enstru_code, dvc_percent=dvc,
            product_name=s.product_name, production_address=s.production_address,
            email=s.email, phone=s.phone
        ))
    return result
