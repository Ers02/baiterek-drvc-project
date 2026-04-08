from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..schemas import plan as plan_schema
from ..services.item_service import ItemService
from ..utils.auth import get_current_user
from ..models import models
from ..models.models import UserRole

router = APIRouter(
    prefix="/items",
    tags=["Plan Items"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/{item_id}", response_model=plan_schema.PlanItem)
def read_plan_item(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Получить позицию сметы"""
    item = ItemService.get_item(db, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    
    # Проверка прав (ООП инкапсуляция логики авторизации здесь в роутере допустима)
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and item.version.plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    return item

@router.put("/{item_id}", response_model=plan_schema.PlanItem)
def update_plan_item(item_id: int, item_in: plan_schema.PlanItemUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Обновить позицию"""
    return ItemService.update_item(db, item_id, item_in, current_user)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan_item(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Удалить позицию"""
    ItemService.delete_item(db, item_id, current_user)
    return None

@router.post("/{item_id}/revert", response_model=plan_schema.PlanItem)
def revert_plan_item(item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Откатить изменения"""
    return ItemService.revert_item(db, item_id, current_user)
