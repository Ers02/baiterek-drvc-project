from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, text
from typing import List, Optional

from ..database.database import get_db
from ..schemas import lookup as lookup_schema
from ..models import models
from ..utils.auth import get_current_admin

router = APIRouter(
    prefix="/lookups",
    tags=["Lookups"],
)


@router.get("/check-ktp/{enstru_code}")
def check_ktp_by_enstru(enstru_code: str, db: Session = Depends(get_db)):
    """Проверяет, есть ли код ЕНС ТРУ в реестре КТП."""
    # Using JSONB operator @> to check if the array contains the value
    exists = db.query(models.Reestr_KTP).filter(
        models.Reestr_KTP.enstru_codes.contains([enstru_code])
    ).first()
    return {"is_ktp": exists is not None}


@router.get("/ktp-suppliers/{enstru_code}", response_model=List[lookup_schema.KtpSupplier])
def get_ktp_suppliers(enstru_code: str, db: Session = Depends(get_db)):
    """Получить список поставщиков КТП по коду ЕНС ТРУ."""
    suppliers = db.query(models.Reestr_KTP).filter(
        models.Reestr_KTP.enstru_codes.contains([enstru_code]),
        # dvc_percent is now Text, so we might need to cast or just check it's not '0' or empty if that's the logic
        # Assuming dvc_percent stores numeric values as strings based on the new schema
        # If strict > 0 check is needed, we might need to cast in SQL or filter in python
        # For simplicity, let's assume existence in registry implies capability
        # models.Reestr_KTP.dvc_percent != '0' 
    ).all()
    
    # Map to schema
    result = []
    for s in suppliers:
        # Convert text percent to float if possible, else 0
        try:
            dvc = float(s.dvc_percent.replace(',', '.')) if s.dvc_percent else 0.0
        except ValueError:
            dvc = 0.0
            
        result.append(lookup_schema.KtpSupplier(
            id=s.id,
            bin_iin=s.bin_iin,
            company_name=s.company_name,
            enstru_code=enstru_code, # Return the requested code
            dvc_percent=dvc,
            product_name=s.product_name,
            production_address=s.production_address,
            email=s.email,
            phone=s.phone
        ))
    return result


@router.get("/supplier-by-bin/{bin_iin}", response_model=List[lookup_schema.KtpSupplier])
def get_supplier_by_bin(bin_iin: str, enstru_code: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Ищет поставщика по БИН.
    Возвращает список всех найденных сертификатов.
    """
    query = db.query(models.Reestr_KTP).filter(models.Reestr_KTP.bin_iin == bin_iin)
    
    if enstru_code:
        query = query.filter(models.Reestr_KTP.enstru_codes.contains([enstru_code]))
        
    matches = query.all()
    
    result = []
    for m in matches:
        try:
            dvc = float(m.dvc_percent.replace(',', '.')) if m.dvc_percent else 0.0
        except ValueError:
            dvc = 0.0
            
        # Determine which code to return. If specific requested, return it.
        # Otherwise, maybe just the first one or leave empty?
        # The schema likely expects a single string. Let's use the requested one or the first available.
        code_to_return = enstru_code
        if not code_to_return and m.enstru_codes and len(m.enstru_codes) > 0:
            code_to_return = m.enstru_codes[0] # Take the first one as representative
            
        result.append(lookup_schema.KtpSupplier(
            id=m.id,
            bin_iin=m.bin_iin,
            company_name=m.company_name,
            enstru_code=code_to_return,
            dvc_percent=dvc,
            product_name=m.product_name,
            production_address=m.production_address,
            email=m.email,
            phone=m.phone
        ))
        
    return result


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
            models.Agsk.name_ru.ilike(search_term),
            models.Agsk.full_name.ilike(search_term) # Added full_name search
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


# ============= ADMIN ENDPOINTS FOR MANAGING DIRECTORIES =============
# Только ADMIN может управлять справочниками

@router.post("/mkei", response_model=lookup_schema.Mkei, status_code=status.HTTP_201_CREATED)
def create_mkei(
    mkei: lookup_schema.MkeiCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Создать новую единицу измерения (только ADMIN)."""
    db_mkei = models.Mkei(**mkei.dict())
    db.add(db_mkei)
    db.commit()
    db.refresh(db_mkei)
    return db_mkei


@router.put("/mkei/{mkei_id}", response_model=lookup_schema.Mkei)
def update_mkei(
    mkei_id: int,
    mkei: lookup_schema.MkeiCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Обновить единицу измерения (только ADMIN)."""
    db_mkei = db.query(models.Mkei).filter(models.Mkei.id == mkei_id).first()
    if not db_mkei:
        raise HTTPException(status_code=404, detail="Единица измерения не найдена")
    
    for key, value in mkei.dict().items():
        setattr(db_mkei, key, value)
    
    db.commit()
    db.refresh(db_mkei)
    return db_mkei


@router.delete("/mkei/{mkei_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mkei(
    mkei_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Удалить единицу измерения (только ADMIN)."""
    db_mkei = db.query(models.Mkei).filter(models.Mkei.id == mkei_id).first()
    if not db_mkei:
        raise HTTPException(status_code=404, detail="Единица измерения не найдена")
    
    db.delete(db_mkei)
    db.commit()
    return {"ok": True}


@router.post("/kato", response_model=lookup_schema.Kato, status_code=status.HTTP_201_CREATED)
def create_kato(
    kato: lookup_schema.KatoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Создать новый КАТО (только ADMIN)."""
    db_kato = models.Kato(**kato.dict())
    db.add(db_kato)
    db.commit()
    db.refresh(db_kato)
    return db_kato


@router.put("/kato/{kato_id}", response_model=lookup_schema.Kato)
def update_kato(
    kato_id: int,
    kato: lookup_schema.KatoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Обновить КАТО (только ADMIN)."""
    db_kato = db.query(models.Kato).filter(models.Kato.id == kato_id).first()
    if not db_kato:
        raise HTTPException(status_code=404, detail="КАТО не найден")
    
    for key, value in kato.dict().items():
        setattr(db_kato, key, value)
    
    db.commit()
    db.refresh(db_kato)
    return db_kato


@router.delete("/kato/{kato_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_kato(
    kato_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Удалить КАТО (только ADMIN)."""
    db_kato = db.query(models.Kato).filter(models.Kato.id == kato_id).first()
    if not db_kato:
        raise HTTPException(status_code=404, detail="КАТО не найден")
    
    db.delete(db_kato)
    db.commit()
    return {"ok": True}


@router.post("/agsk", response_model=lookup_schema.Agsk, status_code=status.HTTP_201_CREATED)
def create_agsk(
    agsk: lookup_schema.AgskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Создать новый АГСК (только ADMIN)."""
    db_agsk = models.Agsk(**agsk.dict())
    db.add(db_agsk)
    db.commit()
    db.refresh(db_agsk)
    return db_agsk


@router.put("/agsk/{agsk_id}", response_model=lookup_schema.Agsk)
def update_agsk(
    agsk_id: int,
    agsk: lookup_schema.AgskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Обновить АГСК (только ADMIN)."""
    db_agsk = db.query(models.Agsk).filter(models.Agsk.id == agsk_id).first()
    if not db_agsk:
        raise HTTPException(status_code=404, detail="АГСК не найден")
    
    for key, value in agsk.dict().items():
        setattr(db_agsk, key, value)
    
    db.commit()
    db.refresh(db_agsk)
    return db_agsk


@router.delete("/agsk/{agsk_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agsk(
    agsk_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Удалить АГСК (только ADMIN)."""
    db_agsk = db.query(models.Agsk).filter(models.Agsk.id == agsk_id).first()
    if not db_agsk:
        raise HTTPException(status_code=404, detail="АГСК не найден")
    
    db.delete(db_agsk)
    db.commit()
    return {"ok": True}


@router.post("/cost-items", response_model=lookup_schema.CostItem, status_code=status.HTTP_201_CREATED)
def create_cost_item(
    cost_item: lookup_schema.CostItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Создать новую статью затрат (только ADMIN)."""
    db_cost_item = models.Cost_Item(**cost_item.dict())
    db.add(db_cost_item)
    db.commit()
    db.refresh(db_cost_item)
    return db_cost_item


@router.put("/cost-items/{item_id}", response_model=lookup_schema.CostItem)
def update_cost_item(
    item_id: int,
    cost_item: lookup_schema.CostItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Обновить статью затрат (только ADMIN)."""
    db_cost_item = db.query(models.Cost_Item).filter(models.Cost_Item.id == item_id).first()
    if not db_cost_item:
        raise HTTPException(status_code=404, detail="Статья затрат не найдена")
    
    for key, value in cost_item.dict().items():
        setattr(db_cost_item, key, value)
    
    db.commit()
    db.refresh(db_cost_item)
    return db_cost_item


@router.delete("/cost-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cost_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Удалить статью затрат (только ADMIN)."""
    db_cost_item = db.query(models.Cost_Item).filter(models.Cost_Item.id == item_id).first()
    if not db_cost_item:
        raise HTTPException(status_code=404, detail="Статья затрат не найдена")
    
    db.delete(db_cost_item)
    db.commit()
    return {"ok": True}


@router.post("/source-funding", response_model=lookup_schema.SourceFunding, status_code=status.HTTP_201_CREATED)
def create_source_funding(
    source_funding: lookup_schema.SourceFundingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Создать новый источник финансирования (только ADMIN)."""
    db_source_funding = models.Source_Funding(**source_funding.dict())
    db.add(db_source_funding)
    db.commit()
    db.refresh(db_source_funding)
    return db_source_funding


@router.put("/source-funding/{source_id}", response_model=lookup_schema.SourceFunding)
def update_source_funding(
    source_id: int,
    source_funding: lookup_schema.SourceFundingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Обновить источник финансирования (только ADMIN)."""
    db_source_funding = db.query(models.Source_Funding).filter(models.Source_Funding.id == source_id).first()
    if not db_source_funding:
        raise HTTPException(status_code=404, detail="Источник финансирования не найден")
    
    for key, value in source_funding.dict().items():
        setattr(db_source_funding, key, value)
    
    db.commit()
    db.refresh(db_source_funding)
    return db_source_funding


@router.delete("/source-funding/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_source_funding(
    source_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    """Удалить источник финансирования (только ADMIN)."""
    db_source_funding = db.query(models.Source_Funding).filter(models.Source_Funding.id == source_id).first()
    if not db_source_funding:
        raise HTTPException(status_code=404, detail="Источник финансирования не найден")
    
    db.delete(db_source_funding)
    db.commit()
    return {"ok": True}
