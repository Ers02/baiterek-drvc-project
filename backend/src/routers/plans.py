from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database.database import get_db
from ..schemas import plan as plan_schema
from ..services.plan_service import PlanService
from ..utils.auth import get_current_user
from ..models import models
from ..models.models import UserRole

router = APIRouter(
    prefix="/plans",
    tags=["Procurement Plans"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=plan_schema.PlanModel, status_code=status.HTTP_201_CREATED)
def create_plan(plan_in: plan_schema.PlanCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Создать новый план закупок"""
    return PlanService.create_plan(db, plan_in, current_user.id)

@router.get("/", response_model=List[plan_schema.PlanModel])
def read_plans(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Получить список планов (своих или всех для аналитика)"""
    is_analyst = current_user.role in [UserRole.ADMIN, UserRole.ANALYST_DRVC]
    return PlanService.get_user_plans(db, current_user.id, is_analyst)

@router.get("/{plan_id}", response_model=plan_schema.PlanModel)
def read_plan(plan_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Детали плана с активной версией"""
    plan = PlanService.get_plan_with_active_version(db, plan_id)
    if not plan: raise HTTPException(status_code=404, detail="План не найден")
    return plan

@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(plan_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Удалить план"""
    return PlanService.delete_plan(db, plan_id)
