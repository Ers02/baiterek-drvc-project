from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from decimal import Decimal
from fastapi import HTTPException, status
from ..models import models
from ..schemas import plan as plan_schema
from .plan_service import _recalculate_version_metrics

def get_item(db: Session, item_id: int) -> models.PlanItemVersion | None:
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

def update_item(db: Session, item_id: int, item_in: plan_schema.PlanItemUpdate, user: models.User) -> models.PlanItemVersion:
    """Обновляет позицию плана."""
    db_item = get_item(db, item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция не найдена")

    version = db_item.version
    if version.status != models.PlanStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Редактирование запрещено, версия не в статусе 'Черновик'.")
    
    plan = version.plan
    if plan.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав для редактирования этой позиции.")

    update_data = item_in.model_dump(exclude_unset=True)
    
    # Проверка и очистка АГСК
    expense_item_id = update_data.get('expense_item_id')
    if expense_item_id:
        expense_item = db.query(models.Cost_Item).filter(models.Cost_Item.id == expense_item_id).first()
        # Более мягкая проверка на СМР (регистронезависимая и на вхождение)
        if expense_item and "смр" not in expense_item.name_ru.lower():
            update_data['agsk_id'] = None
    elif 'expense_item_id' not in update_data:
        # Если статья затрат не меняется, проверяем текущую
        if db_item.expense_item and "смр" not in db_item.expense_item.name_ru.lower():
             # Если текущая не СМР, но пытаются обновить agsk_id (вдруг), то сбрасываем
             if 'agsk_id' in update_data:
                 update_data['agsk_id'] = None

    for key, value in update_data.items():
        setattr(db_item, key, value)

    if 'quantity' in update_data or 'price_per_unit' in update_data:
        db_item.total_amount = (db_item.quantity or 0) * (db_item.price_per_unit or 0)

    if 'trucode' in update_data:
        enstru_item = db.query(models.Enstru).filter(models.Enstru.code == update_data['trucode']).first()
        if enstru_item:
            # Маппинг type_name на NeedType (Исправлено: WORK, SERVICE)
            need_type_map = {
                'GOODS': models.NeedType.GOODS,
                'WORK': models.NeedType.WORKS,
                'SERVICE': models.NeedType.SERVICES
            }
            db_item.need_type = need_type_map.get(enstru_item.type_name, models.NeedType.GOODS)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Код ЕНС ТРУ '{update_data['trucode']}' не найден.")

    # ЛОГИКА РЕДАКЦИЙ:
    if db_item.source_version_id != version.id:
        db_item.revision_number += 1
        db_item.source_version_id = version.id

    db.commit()
    _recalculate_version_metrics(db, version.id)
    db.refresh(db_item)
    return db_item

def delete_item(db: Session, item_id: int, user: models.User) -> bool:
    """
    Выполняет "мягкое удаление" позиции плана.
    Вместо физического удаления устанавливает флаг is_deleted = True.
    """
    db_item = get_item(db, item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция не найдена")

    version = db_item.version
    if version.status != models.PlanStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Удаление запрещено, версия не в статусе 'Черновик'.")

    plan = version.plan
    if plan.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав для удаления этой позиции.")

    db_item.is_deleted = True
    db.commit()
    
    _recalculate_version_metrics(db, version.id)
    
    return True

def revert_item(db: Session, item_id: int, user: models.User) -> models.PlanItemVersion:
    """
    Откатывает позицию к состоянию из предыдущей версии плана.
    """
    db_item = get_item(db, item_id)
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция не найдена")

    version = db_item.version
    if version.status != models.PlanStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Откат возможен только для черновика.")
    
    if version.plan.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав для изменения этой позиции.")

    # Если позиция не менялась в этой версии, откатывать нечего
    if db_item.source_version_id != version.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Эта позиция не была изменена в текущей версии.")

    # Ищем предыдущую версию этой позиции
    previous_item = db.query(models.PlanItemVersion).join(
        models.ProcurementPlanVersion,
        models.PlanItemVersion.version_id == models.ProcurementPlanVersion.id
    ).filter(
        models.PlanItemVersion.root_item_id == db_item.root_item_id,
        models.ProcurementPlanVersion.plan_id == version.plan_id,
        models.ProcurementPlanVersion.version_number < version.version_number,
        models.PlanItemVersion.is_deleted == False
    ).order_by(desc(models.ProcurementPlanVersion.version_number)).first()

    if not previous_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Предыдущая версия этой позиции не найдена.")

    # Копируем данные из предыдущей версии
    fields_to_copy = [
        'trucode', 'unit_id', 'expense_item_id', 'funding_source_id',
        'agsk_id', 'kato_purchase_id', 'kato_delivery_id',
        'additional_specs', 'additional_specs_kz',
        'quantity', 'price_per_unit', 'total_amount',
        'is_ktp', 'resident_share', 'non_resident_reason', 'need_type',
        'revision_number'
    ]
    
    for field in fields_to_copy:
        setattr(db_item, field, getattr(previous_item, field))

    # Восстанавливаем ссылку на исходную версию
    db_item.source_version_id = previous_item.source_version_id

    db.commit()
    _recalculate_version_metrics(db, version.id)
    db.refresh(db_item)
    return db_item
