from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..schemas import execution_schema
from ..services import execution_service
from ..utils.auth import get_current_user
from ..models import models

router = APIRouter(
    prefix="/executions",
    tags=["Plan Executions (Reports)"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=execution_schema.Execution, status_code=status.HTTP_201_CREATED)
def create_execution(
    execution_in: execution_schema.ExecutionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Создать запись об исполнении (отчет) для позиции плана."""
    return execution_service.create_execution(db=db, execution_in=execution_in, user=current_user)

@router.get("/by-item/{plan_item_id}", response_model=List[execution_schema.Execution])
def read_executions_by_item(
    plan_item_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Получить все записи об исполнении для конкретной позиции плана."""
    return execution_service.get_executions_by_item(db=db, plan_item_id=plan_item_id, user=current_user)

@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_execution(
    execution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Удалить запись об исполнении."""
    execution_service.delete_execution(db=db, execution_id=execution_id, user=current_user)
    return {"ok": True}
