from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc, text
from decimal import Decimal
from typing import List, Optional, Dict
from fastapi import HTTPException, status
from ..models import models
from ..schemas import plan as plan_schema
from ..utils.helpers import get_need_type_by_typename

class PlanService:
    """Сервис для управления планами закупок и их версиями"""

    @staticmethod
    def _get_active_version(db: Session, plan_id: int, lock: bool = False) -> Optional[models.ProcurementPlanVersion]:
        query = db.query(models.ProcurementPlanVersion).filter(
            models.ProcurementPlanVersion.plan_id == plan_id,
            models.ProcurementPlanVersion.is_active == True
        )
        if lock: query = query.with_for_update()
        return query.first()

    @staticmethod
    def recalculate_metrics(db: Session, version_id: int):
        """Пересчет всех метрик версии (ДВС, суммы и т.д.)"""
        version = db.query(models.ProcurementPlanVersion).filter(models.ProcurementPlanVersion.id == version_id).first()
        if not version: return

        # Логика обновления ДВС для товаров из Реестра КТП
        trucodes = [r[0] for r in db.query(models.PlanItemVersion.trucode).filter(
            models.PlanItemVersion.version_id == version_id,
            models.PlanItemVersion.need_type == models.NeedType.GOODS,
            models.PlanItemVersion.is_deleted == False
        ).distinct().all()]
        
        if trucodes:
            # Массовый поиск минимального ДВС в КТП (оптимизированный подход)
            ktp_data = db.query(models.Reestr_KTP.enstru_codes, models.Reestr_KTP.dvc_percent).filter(
                models.Reestr_KTP.enstru_codes.isnot(None),
                models.Reestr_KTP.dvc_percent.isnot(None)
            ).all()

            ktp_map = {}
            for row in ktp_data:
                try: dvc = Decimal(str(row.dvc_percent).replace(',', '.'))
                except: continue
                if dvc <= 0: continue

                for code in row.enstru_codes:
                    if code in trucodes:
                        ktp_map[code] = min(ktp_map.get(code, dvc), dvc)

            for code, dvc in ktp_map.items():
                db.query(models.PlanItemVersion).filter(
                    models.PlanItemVersion.version_id == version_id,
                    models.PlanItemVersion.trucode == code
                ).update({
                    "min_dvc_percent": dvc,
                    "vc_amount": models.PlanItemVersion.total_amount * (dvc / 100)
                }, synchronize_session=False)

        # Обновление итогов версии
        metrics = db.query(
            func.sum(models.PlanItemVersion.total_amount),
            func.sum(models.PlanItemVersion.vc_amount)
        ).filter(models.PlanItemVersion.version_id == version_id, models.PlanItemVersion.is_deleted == False).first()

        version.total_amount = metrics[0] or 0
        version.vc_amount = metrics[1] or 0
        if version.total_amount > 0:
            version.vc_percentage = (version.vc_amount / version.total_amount) * 100

        db.commit()

    @staticmethod
    def create_plan(db: Session, plan_in: plan_schema.PlanCreate, user_id: int) -> models.ProcurementPlan:
        db_plan = models.ProcurementPlan(plan_name=plan_in.plan_name, year=plan_in.year, created_by=user_id)
        db.add(db_plan)
        db.flush()
        db.add(models.ProcurementPlanVersion(plan_id=db_plan.id, version_number=1, status=models.PlanStatus.DRAFT, is_active=True, created_by=user_id))
        db.commit()
        db.refresh(db_plan)
        return db_plan

    @staticmethod
    def get_plan_with_active_version(db: Session, plan_id: int) -> Optional[models.ProcurementPlan]:
        return db.query(models.ProcurementPlan).options(
            selectinload(models.ProcurementPlan.versions).selectinload(models.ProcurementPlanVersion.items).options(
                joinedload(models.PlanItemVersion.enstru), joinedload(models.PlanItemVersion.unit),
                joinedload(models.PlanItemVersion.expense_item), joinedload(models.PlanItemVersion.funding_source)
            )
        ).filter(models.ProcurementPlan.id == plan_id).first()

    @staticmethod
    def get_user_plans(db: Session, user_id: int, is_analyst: bool = False) -> List[models.ProcurementPlan]:
        query = db.query(models.ProcurementPlan).options(selectinload(models.ProcurementPlan.versions))
        if not is_analyst:
            query = query.filter(models.ProcurementPlan.created_by == user_id)
        return query.order_by(desc(models.ProcurementPlan.id)).all()

    @staticmethod
    def delete_plan(db: Session, plan_id: int):
        plan = db.query(models.ProcurementPlan).filter(models.ProcurementPlan.id == plan_id).first()
        if plan:
            db.delete(plan)
            db.commit()
        return True
