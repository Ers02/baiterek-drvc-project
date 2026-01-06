from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException, status
from ..models import models
from ..schemas import execution_schema

def _recalculate_item_execution_status(db: Session, item_id: int):
    """
    Пересчитывает исполненное количество и сумму для позиции плана.
    """
    item = db.query(models.PlanItemVersion).filter(models.PlanItemVersion.id == item_id).first()
    if not item:
        return

    contracted_quantity = db.query(func.sum(models.PlanItemExecution.contract_quantity)).filter(
        models.PlanItemExecution.plan_item_id == item_id
    ).scalar() or 0
    
    contracted_amount = db.query(func.sum(models.PlanItemExecution.contract_sum)).filter(
        models.PlanItemExecution.plan_item_id == item_id
    ).scalar() or 0
    
    item.executed_quantity = contracted_quantity
    item.executed_amount = contracted_amount
    db.commit()

def _check_and_update_plan_execution_status(db: Session, version_id: int):
    """
    Проверяет, полностью ли исполнен план (все позиции закрыты отчетами).
    Если да, устанавливает is_executed = True.
    """
    version = db.query(models.ProcurementPlanVersion).filter(models.ProcurementPlanVersion.id == version_id).first()
    if not version:
        return

    # Получаем все НЕ удаленные позиции плана
    items = db.query(models.PlanItemVersion).filter(
        models.PlanItemVersion.version_id == version_id,
        models.PlanItemVersion.is_deleted == False
    ).all()

    if not items:
        version.is_executed = False
        db.commit()
        return

    all_items_executed = True
    for item in items:
        # Используем уже обновленное поле executed_quantity
        if item.executed_quantity < item.quantity:
            all_items_executed = False
            break
    
    version.is_executed = all_items_executed
    db.commit()

def create_execution(db: Session, execution_in: execution_schema.ExecutionCreate, user: models.User) -> models.PlanItemExecution:
    # Проверяем существование позиции плана
    plan_item = db.query(models.PlanItemVersion).filter(models.PlanItemVersion.id == execution_in.plan_item_id).first()
    if not plan_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция плана не найдена")

    # Проверяем права доступа
    if plan_item.version.plan.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав для добавления отчета к этой позиции")

    # Проверяем статус плана
    if plan_item.version.status != models.PlanStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Отчеты можно добавлять только к утвержденным планам")

    # --- ВАЛИДАЦИЯ ЦЕНЫ ЗА ЕДИНИЦУ ---
    if execution_in.contract_price_per_unit > plan_item.price_per_unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Цена за единицу ({execution_in.contract_price_per_unit}) превышает плановую ({plan_item.price_per_unit})"
        )

    # --- ВАЛИДАЦИЯ КОЛИЧЕСТВА ---
    total_contracted_quantity = db.query(func.sum(models.PlanItemExecution.contract_quantity)).filter(
        models.PlanItemExecution.plan_item_id == execution_in.plan_item_id
    ).scalar() or 0

    new_total_quantity = total_contracted_quantity + execution_in.contract_quantity

    if new_total_quantity > plan_item.quantity:
        remaining_quantity = plan_item.quantity - total_contracted_quantity
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Превышено плановое количество. Осталось: {remaining_quantity}, вы пытаетесь добавить: {execution_in.contract_quantity}"
        )
    
    # Рассчитываем сумму текущего договора
    current_contract_sum = execution_in.contract_quantity * execution_in.contract_price_per_unit

    # --- ВАЛИДАЦИЯ СУММЫ ---
    total_contracted_sum = db.query(func.sum(models.PlanItemExecution.contract_sum)).filter(
        models.PlanItemExecution.plan_item_id == execution_in.plan_item_id
    ).scalar() or 0

    new_total_sum = total_contracted_sum + current_contract_sum

    if new_total_sum > plan_item.total_amount:
        remaining_sum = plan_item.total_amount - total_contracted_sum
        if new_total_sum - plan_item.total_amount > 0.01:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Превышена плановая сумма. Осталось: {remaining_sum}, вы пытаетесь добавить: {current_contract_sum}"
            )
    # --- КОНЕЦ ВАЛИДАЦИИ ---

    db_execution = models.PlanItemExecution(
        **execution_in.model_dump(),
        contract_sum=current_contract_sum
    )
    db.add(db_execution)
    db.commit()
    db.refresh(db_execution)
    
    # Обновляем статус исполнения позиции
    _recalculate_item_execution_status(db, plan_item.id)
    
    # Обновляем статус исполнения плана
    _check_and_update_plan_execution_status(db, plan_item.version_id)
    
    return db_execution

def get_executions_by_item(db: Session, plan_item_id: int, user: models.User) -> list[models.PlanItemExecution]:
    plan_item = db.query(models.PlanItemVersion).filter(models.PlanItemVersion.id == plan_item_id).first()
    if not plan_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Позиция плана не найдена")
    
    if plan_item.version.plan.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав для просмотра отчетов этой позиции")

    return db.query(models.PlanItemExecution).filter(models.PlanItemExecution.plan_item_id == plan_item_id).all()

def delete_execution(db: Session, execution_id: int, user: models.User):
    execution = db.query(models.PlanItemExecution).filter(models.PlanItemExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Запись об исполнении не найдена")

    if execution.plan_item.version.plan.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет прав для удаления этого отчета")

    version_id = execution.plan_item.version_id
    plan_item_id = execution.plan_item_id
    
    db.delete(execution)
    db.commit()
    
    # Обновляем статус исполнения позиции
    _recalculate_item_execution_status(db, plan_item_id)
    
    # Обновляем статус исполнения плана
    _check_and_update_plan_execution_status(db, version_id)
    
    return True
