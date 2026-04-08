from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database.database import get_db
from ..schemas import execution_schema
from ..services.execution_service import ExecutionService
from ..utils.auth import get_current_user
from ..models import models

router = APIRouter(
    prefix="/executions",
    tags=["Plan Executions (Reports)"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=execution_schema.Execution, status_code=status.HTTP_201_CREATED)
def create_execution(execution_in: execution_schema.ExecutionCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Создать отчет об исполнении (договор/поставка)"""
    return ExecutionService.create_execution(db, execution_in, current_user)

@router.get("/by-item/{plan_item_id}", response_model=List[execution_schema.Execution])
def read_executions_by_item(plan_item_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """История исполнения для позиции"""
    return ExecutionService.get_executions_by_item(db, plan_item_id, current_user)

@router.delete("/{execution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_execution(execution_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Удалить отчет"""
    ExecutionService.delete_execution(db, execution_id, current_user)
    return None
