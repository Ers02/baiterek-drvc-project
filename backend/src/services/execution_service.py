from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from ..models import models
from ..schemas import execution_schema
from .plan_service import PlanService

class ExecutionService:
    """Сервис для управления исполнением планов закупок (отчетность)"""

    @staticmethod
    def _recalculate_item_status(db: Session, item_id: int):
        """Пересчет исполненных показателей для позиции"""
        item = db.query(models.PlanItemVersion).filter(models.PlanItemVersion.id == item_id).first()
        if not item: return

        stats = db.query(
            func.sum(models.PlanItemExecution.supply_volume_physical),
            func.sum(models.PlanItemExecution.supply_volume_value),
            func.sum(models.PlanItemExecution.fact_vc_amount)
        ).filter(models.PlanItemExecution.plan_item_id == item_id).first()

        item.executed_quantity = stats[0] or 0
        item.executed_amount = stats[1] or 0
        item.executed_vc_amount = stats[2] or 0
        db.commit()

    @staticmethod
    def _check_plan_completion(db: Session, version_id: int):
        """Проверка полной реализации плана"""
        version = db.query(models.ProcurementPlanVersion).filter(models.ProcurementPlanVersion.id == version_id).first()
        if not version: return

        items = db.query(models.PlanItemVersion).filter(
            models.PlanItemVersion.version_id == version_id,
            models.PlanItemVersion.is_deleted == False
        ).all()

        if not items:
            version.is_executed = False
        else:
            # План исполнен, если все позиции закрыты по количеству
            version.is_executed = all(i.executed_quantity >= i.quantity for i in items)
        
        db.commit()

    @classmethod
    def create_execution(cls, db: Session, execution_in: execution_schema.ExecutionCreate, user: models.User):
        item = db.query(models.PlanItemVersion).filter(models.PlanItemVersion.id == execution_in.plan_item_id).first()
        if not item or item.version.plan.created_by != user.id:
            raise HTTPException(status_code=403, detail="Доступ запрещен")

        if item.version.status != models.PlanStatus.APPROVED:
            raise HTTPException(status_code=400, detail="План не утвержден")

        # Валидация цен
        if execution_in.contract_price_per_unit > item.price_per_unit:
            raise HTTPException(status_code=400, detail="Цена превышает плановую")

        # Создание записи
        fact_vc_amount = execution_in.supply_volume_value * (execution_in.fact_vc_percentage / 100)
        db_exec = models.PlanItemExecution(
            **execution_in.model_dump(exclude={'fact_vc_amount'}),
            contract_sum=execution_in.contract_quantity * execution_in.contract_price_per_unit,
            fact_vc_amount=fact_vc_amount
        )
        db.add(db_exec)
        db.commit()
        db.refresh(db_exec)

        # Синхронизация статусов
        cls._recalculate_item_status(db, item.id)
        cls._check_plan_completion(db, item.version_id)
        PlanService.recalculate_metrics(db, item.version_id)

        return db_exec

    @staticmethod
    def get_executions_by_item(db: Session, item_id: int, user: models.User):
        return db.query(models.PlanItemExecution).filter(models.PlanItemExecution.plan_item_id == item_id).all()

    @classmethod
    def delete_execution(cls, db: Session, execution_id: int, user: models.User):
        db_exec = db.query(models.PlanItemExecution).filter(models.PlanItemExecution.id == execution_id).first()
        if not db_exec: return False
        
        item_id = db_exec.plan_item_id
        version_id = db_exec.plan_item.version_id
        
        db.delete(db_exec)
        db.commit()

        cls._recalculate_item_status(db, item_id)
        cls._check_plan_completion(db, version_id)
        PlanService.recalculate_metrics(db, version_id)
        return True
