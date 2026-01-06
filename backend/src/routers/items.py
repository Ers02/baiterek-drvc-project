from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..schemas import plan as plan_schema
from ..services import item_service
from ..utils.auth import get_current_user
from ..models import models

router = APIRouter(
    prefix="/items",
    tags=["Plan Items"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/{item_id}", response_model=plan_schema.PlanItem)
def read_plan_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить конкретную позицию сметы по ID вместе с информацией о ее версии."""
    db_item = item_service.get_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    
    # Проверка прав доступа через план
    if db_item.version.plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для доступа к этой позиции")
        
    return db_item

@router.put("/{item_id}", response_model=plan_schema.PlanItem)
def update_plan_item(
    item_id: int,
    item_in: plan_schema.PlanItemUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Обновить позицию сметы.
    Редактирование возможно только для версий в статусе DRAFT.
    """
    return item_service.update_item(db=db, item_id=item_id, item_in=item_in, user=current_user)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Удалить позицию сметы.
    Удаление возможно только для версий в статусе DRAFT.
    """
    item_service.delete_item(db=db, item_id=item_id, user=current_user)
    return {"ok": True}

@router.post("/{item_id}/revert", response_model=plan_schema.PlanItem)
def revert_plan_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Откатить изменения позиции к состоянию из предыдущей версии плана.
    """
    return item_service.revert_item(db=db, item_id=item_id, user=current_user)
