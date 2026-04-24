"""
API для управления библиотекой групп/товаров (для аналитики)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from ..database.database import get_db
from ..models import models
from ..schemas import product_group as schemas
from ..utils.auth import get_current_user

router = APIRouter(
    prefix="/product-groups",
    tags=["Product Groups"],
)


@router.get("", response_model=List[schemas.ProductGroupListItem])
def list_groups(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить список всех групп/товаров"""
    groups = db.query(models.ProductGroup).all()

    result = []
    for g in groups:
        result.append(schemas.ProductGroupListItem(
            id=g.id,
            name=g.name,
            created_at=g.created_at,
            oked_count=len(g.oked_codes or []),
            kpved_count=len(g.kpved_codes or []),
            enstru_count=len(g.enstru_codes or []),
            agsk3_count=len(g.agsk3_codes or []),
            tnved_count=len(g.tnved_codes or []),
            reestr_ktp_count=len(g.reestr_ktp_codes or [])
        ))

    return result


@router.get("/{group_id}", response_model=schemas.ProductGroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить детальную информацию о группе"""
    group = db.query(models.ProductGroup).filter(
        models.ProductGroup.id == group_id
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return group


@router.post("", response_model=schemas.ProductGroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    data: schemas.ProductGroupCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Создать новую группу/товар"""

    # Данные уже в нужном формате - массивы строк
    group = models.ProductGroup(
        name=data.name,
        oked_codes=data.oked_codes,
        kpved_codes=data.kpved_codes,
        enstru_codes=data.enstru_codes,
        agsk3_codes=data.agsk3_codes,
        tnved_codes=data.tnved_codes,
        reestr_ktp_codes=data.reestr_ktp_codes,
        created_by=current_user.id
    )

    db.add(group)
    db.commit()
    db.refresh(group)

    return group


@router.put("/{group_id}", response_model=schemas.ProductGroupResponse)
def update_group(
    group_id: int,
    data: schemas.ProductGroupUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Обновить существующую группу"""
    group = db.query(models.ProductGroup).filter(
        models.ProductGroup.id == group_id
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    # Данные уже в нужном формате - массивы строк
    group.name = data.name
    group.oked_codes = data.oked_codes
    group.kpved_codes = data.kpved_codes
    group.enstru_codes = data.enstru_codes
    group.agsk3_codes = data.agsk3_codes
    group.tnved_codes = data.tnved_codes
    group.reestr_ktp_codes = data.reestr_ktp_codes

    db.commit()
    db.refresh(group)

    return group


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Удалить группу"""
    group = db.query(models.ProductGroup).filter(
        models.ProductGroup.id == group_id
    ).first()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    db.delete(group)
    db.commit()

    return {"status": "ok", "message": "Group deleted"}


# --- API для наборов групп ---

@router.get("/sets", response_model=List[schemas.ProductGroupSetListItem])
def list_group_sets(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить список наборов групп"""
    sets = db.query(
        models.ProductGroupSet.id,
        models.ProductGroupSet.name,
        models.ProductGroupSet.description,
        models.ProductGroupSet.created_at,
        func.count(models.ProductGroupSetItem.id).label("groups_count")
    ).outerjoin(models.ProductGroupSetItem).group_by(models.ProductGroupSet.id).all()

    return sets


@router.post("/sets", response_model=schemas.ProductGroupSetResponse, status_code=status.HTTP_201_CREATED)
def create_group_set(
    data: schemas.ProductGroupSetCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Создать новый набор групп"""
    group_set = models.ProductGroupSet(
        name=data.name,
        description=data.description,
        created_by=current_user.id
    )
    db.add(group_set)
    db.commit()
    db.refresh(group_set)

    # Добавляем группы в набор
    for idx, group_id in enumerate(data.group_ids):
        item = models.ProductGroupSetItem(
            set_id=group_set.id,
            group_id=group_id,
            order=idx
        )
        db.add(item)

    db.commit()
    db.refresh(group_set)

    return group_set
