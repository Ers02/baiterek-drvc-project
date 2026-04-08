from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from ..models import models
from ..schemas import plan as plan_schema
from .plan_service import PlanService

class ItemService:
    """Сервис для управления отдельными позициями плана закупок"""

    @staticmethod
    def get_item(db: Session, item_id: int) -> Optional[models.PlanItemVersion]:
        """Получает конкретную позицию плана по ее ID, если она не удалена."""
        return db.query(models.PlanItemVersion).options(
            joinedload(models.PlanItemVersion.version).joinedload(models.ProcurementPlanVersion.plan),
            joinedload(models.PlanItemVersion.enstru),
            joinedload(models.PlanItemVersion.unit),
            joinedload(models.PlanItemVersion.expense_item),
            joinedload(models.PlanItemVersion.funding_source),
            joinedload(models.PlanItemVersion.agsk),
            joinedload(models.PlanItemVersion.kato_purchase),
            joinedload(models.PlanItemVersion.kato_delivery)
        ).filter(
            models.PlanItemVersion.id == item_id,
            models.PlanItemVersion.is_deleted == False
        ).first()

    @classmethod
    def update_item(cls, db: Session, item_id: int, item_in: plan_schema.PlanItemUpdate, user: models.User) -> models.PlanItemVersion:
        """Обновляет позицию плана."""
        db_item = cls.get_item(db, item_id)
        if not db_item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция не найдена")

        version = db_item.version
        if version.status != models.PlanStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Редактирование запрещено, версия не в статусе 'Черновик'.")

        if version.plan.created_by != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав для редактирования.")

        update_data = item_in.model_dump(exclude_unset=True)

        # Инкапсулированная логика проверки АГСК/СМР
        expense_item_id = update_data.get('expense_item_id')
        if expense_item_id:
            expense_item = db.query(models.Cost_Item).filter(models.Cost_Item.id == expense_item_id).first()
            if expense_item and "смр" not in expense_item.name_ru.lower():
                update_data['agsk_id'] = None

        # Применение обновлений
        for key, value in update_data.items():
            setattr(db_item, key, value)

        if 'quantity' in update_data or 'price_per_unit' in update_data:
            db_item.total_amount = Decimal(db_item.quantity or 0) * Decimal(db_item.price_per_unit or 0)

        if 'trucode' in update_data:
            enstru_item = db.query(models.Enstru).filter(models.Enstru.code == update_data['trucode']).first()
            if enstru_item:
                need_type_map = {
                    'GOODS': models.NeedType.GOODS,
                    'WORK': models.NeedType.WORKS,
                    'SERVICE': models.NeedType.SERVICES
                }
                db_item.need_type = need_type_map.get(enstru_item.type_name, models.NeedType.GOODS)
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Код ЕНС ТРУ '{update_data['trucode']}' не найден.")

        if db_item.source_version_id != version.id:
            db_item.revision_number += 1
            db_item.source_version_id = version.id

        db.commit()
        PlanService.recalculate_metrics(db, version.id)
        db.refresh(db_item)
        return db_item

    @classmethod
    def delete_item(cls, db: Session, item_id: int, user: models.User) -> bool:
        """Мягкое удаление позиции"""
        db_item = cls.get_item(db, item_id)
        if not db_item or db_item.version.status != models.PlanStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Удаление невозможно")

        if db_item.version.plan.created_by != user.id:
            raise HTTPException(status_code=403, detail="Нет прав")

        db_item.is_deleted = True
        db.commit()
        PlanService.recalculate_metrics(db, db_item.version_id)
        return True

    @classmethod
    def revert_item(cls, db: Session, item_id: int, user: models.User) -> models.PlanItemVersion:
        """Откат к предыдущей редакции"""
        db_item = cls.get_item(db, item_id)
        if not db_item or db_item.version.status != models.PlanStatus.DRAFT:
            raise HTTPException(status_code=400, detail="Откат невозможен")

        # Поиск истории
        previous_item = db.query(models.PlanItemVersion).join(
            models.ProcurementPlanVersion,
            models.PlanItemVersion.version_id == models.ProcurementPlanVersion.id
        ).filter(
            models.PlanItemVersion.root_item_id == db_item.root_item_id,
            models.ProcurementPlanVersion.plan_id == db_item.version.plan_id,
            models.ProcurementPlanVersion.version_number < db_item.version.version_number,
            models.PlanItemVersion.is_deleted == False
        ).order_by(desc(models.ProcurementPlanVersion.version_number)).first()

        if not previous_item:
            raise HTTPException(status_code=404, detail="История не найдена")

        # Копирование полей (ООП подход черезgetattr/setattr)
        fields = ['trucode', 'unit_id', 'expense_item_id', 'funding_source_id', 'agsk_id', 'quantity', 'price_per_unit', 'total_amount', 'need_type']
        for f in fields:
            setattr(db_item, f, getattr(previous_item, f))

        db.commit()
        PlanService.recalculate_metrics(db, db_item.version_id)
        db.refresh(db_item)
        return db_item
