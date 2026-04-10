from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc, and_, update, case
from decimal import Decimal
from fastapi import HTTPException, status
from ..models import models
from ..schemas import plan as plan_schema
from ..utils.helpers import get_need_type_by_typename


# ========= Вспомогательные функции для версий =========

def _get_active_version(db: Session, plan_id: int, lock: bool = False) -> models.ProcurementPlanVersion | None:
    """Получает активную версию плана."""
    query = db.query(models.ProcurementPlanVersion).filter(
        models.ProcurementPlanVersion.plan_id == plan_id,
        models.ProcurementPlanVersion.is_active == True
    )
    if lock:
        query = query.with_for_update()
    return query.first()


def _recalculate_version_metrics(db: Session, version_id: int):
    """
    Пересчитывает общую сумму и другие метрики для конкретной версии плана.
    Оптимизировано: использует SQL для массового обновления и агрегации.
    """
    version = db.query(models.ProcurementPlanVersion).filter(models.ProcurementPlanVersion.id == version_id).first()
    if not version:
        return

    # 1. Массовое обновление min_dvc_percent и vc_amount для ТОВАРОВ
    trucodes = [r[0] for r in db.query(models.PlanItemVersion.trucode).filter(
        models.PlanItemVersion.version_id == version_id,
        models.PlanItemVersion.need_type == models.NeedType.GOODS,
        models.PlanItemVersion.is_deleted == False
    ).distinct().all()]

    if trucodes:
        ktp_map = {}
        ktp_results = db.query(
            models.Reestr_KTP.enstru_code,
            func.min(models.Reestr_KTP.dvc_percent)
        ).filter(
            models.Reestr_KTP.enstru_code.in_(trucodes)
        ).group_by(models.Reestr_KTP.enstru_code).all()

        for code, dvc in ktp_results:
            ktp_map[code] = Decimal(str(dvc)) if dvc is not None else Decimal(0)

        for code, dvc in ktp_map.items():
            db.query(models.PlanItemVersion).filter(
                models.PlanItemVersion.version_id == version_id,
                models.PlanItemVersion.trucode == code,
                models.PlanItemVersion.need_type == models.NeedType.GOODS
            ).update({
                models.PlanItemVersion.min_dvc_percent: dvc,
                models.PlanItemVersion.vc_amount: models.PlanItemVersion.total_amount * (dvc / 100)
            }, synchronize_session=False)

        db.query(models.PlanItemVersion).filter(
            models.PlanItemVersion.version_id == version_id,
            models.PlanItemVersion.need_type == models.NeedType.GOODS,
            models.PlanItemVersion.trucode.notin_(ktp_map.keys())
        ).update({
            models.PlanItemVersion.min_dvc_percent: 0,
            models.PlanItemVersion.vc_amount: 0
        }, synchronize_session=False)

    # 2. Массовое обновление для РАБОТ и УСЛУГ (min_dvc = resident_share)
    db.query(models.PlanItemVersion).filter(
        models.PlanItemVersion.version_id == version_id,
        models.PlanItemVersion.need_type != models.NeedType.GOODS,
        models.PlanItemVersion.is_deleted == False
    ).update({
        models.PlanItemVersion.min_dvc_percent: models.PlanItemVersion.resident_share,
        models.PlanItemVersion.vc_amount: models.PlanItemVersion.total_amount * (
                    models.PlanItemVersion.resident_share / 100)
    }, synchronize_session=False)

    db.flush()  # Применяем изменения перед агрегацией

    # 3. Агрегация сумм через SQL
    metrics = db.query(
        func.sum(models.PlanItemVersion.total_amount),
        func.sum(models.PlanItemVersion.vc_amount),
        func.sum(models.PlanItemVersion.executed_amount),
        func.sum(models.PlanItemVersion.executed_vc_amount)
    ).filter(
        models.PlanItemVersion.version_id == version_id,
        models.PlanItemVersion.is_deleted == False
    ).first()

    total_amount = metrics[0] or Decimal(0)
    vc_amount_total = metrics[1] or Decimal(0)
    executed_amount_total = metrics[2] or Decimal(0)
    executed_vc_amount_total = metrics[3] or Decimal(0)

    if total_amount > 0:
        import_percentage = ((total_amount - vc_amount_total) / total_amount) * 100
        vc_percentage = (vc_amount_total / total_amount) * 100
    else:
        import_percentage = Decimal('0.00')
        vc_percentage = Decimal('0.00')

    if executed_amount_total > 0:
        executed_vc_percentage = (executed_vc_amount_total / executed_amount_total) * 100
    else:
        executed_vc_percentage = Decimal('0.00')

    version.total_amount = total_amount
    version.import_percentage = import_percentage
    version.vc_percentage = vc_percentage
    version.vc_amount = vc_amount_total
    version.executed_vc_amount = executed_vc_amount_total
    version.executed_vc_percentage = executed_vc_percentage

    db.commit()
    db.refresh(version)


# ========= Сервисы для Смет Закупок (ProcurementPlan) =========

def create_plan(db: Session, plan_in: plan_schema.ProcurementPlanCreate, user: models.User) -> models.ProcurementPlan:
    db_plan = models.ProcurementPlan(
        plan_name=plan_in.plan_name,
        year=plan_in.year,
        created_by=user.id
    )
    db.add(db_plan)
    db.flush()

    initial_version = models.ProcurementPlanVersion(
        plan_id=db_plan.id,
        version_number=1,
        status=models.PlanStatus.DRAFT,
        is_active=True,
        created_by=user.id
    )
    db.add(initial_version)
    db.commit()
    db.refresh(db_plan)
    return db_plan


def get_plan_with_active_version(db: Session, plan_id: int) -> models.ProcurementPlan | None:
    return db.query(models.ProcurementPlan).options(
        selectinload(models.ProcurementPlan.versions)
        .selectinload(models.ProcurementPlanVersion.items)
        .options(
            joinedload(models.PlanItemVersion.enstru),
            joinedload(models.PlanItemVersion.unit),
            joinedload(models.PlanItemVersion.expense_item),
            joinedload(models.PlanItemVersion.funding_source),
            joinedload(models.PlanItemVersion.agsk),
            joinedload(models.PlanItemVersion.kato_purchase),
            joinedload(models.PlanItemVersion.kato_delivery),
            joinedload(models.PlanItemVersion.source_version),
            joinedload(models.PlanItemVersion.root_item).joinedload(models.PlanItemVersion.version)
        )
    ).filter(
        models.ProcurementPlan.id == plan_id
    ).first()


def get_plans_by_user(db: Session, user: models.User, skip: int = 0, limit: int = 100) -> list[models.ProcurementPlan]:
    return db.query(models.ProcurementPlan).options(
        selectinload(models.ProcurementPlan.versions).selectinload(models.ProcurementPlanVersion.creator)
    ).filter(
        models.ProcurementPlan.created_by == user.id
    ).order_by(desc(models.ProcurementPlan.id)).offset(skip).limit(limit).all()


def update_plan_status(db: Session, plan_id: int, new_status: models.PlanStatus,
                       user: models.User) -> models.ProcurementPlanVersion:
    active_version = _get_active_version(db, plan_id, lock=True)
    if not active_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Активная версия плана не найдена")

    current_status = active_version.status

    if current_status == models.PlanStatus.DRAFT and new_status == models.PlanStatus.PRE_APPROVED:
        active_version.status = new_status
    elif current_status == models.PlanStatus.PRE_APPROVED and new_status == models.PlanStatus.APPROVED:
        active_version.status = new_status
    elif current_status == new_status:
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Недопустимый переход статуса из {current_status.value} в {new_status.value}"
        )

    db.commit()
    db.refresh(active_version)
    return active_version


def create_new_version_for_editing(db: Session, plan_id: int, user: models.User) -> models.ProcurementPlanVersion:
    db.begin_nested()
    try:
        current_active_version = db.query(models.ProcurementPlanVersion).filter(
            models.ProcurementPlanVersion.plan_id == plan_id,
            models.ProcurementPlanVersion.is_active == True
        ).options(
            selectinload(models.ProcurementPlanVersion.items).selectinload(models.PlanItemVersion.executions)
        ).with_for_update().first()

        if not current_active_version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Активная версия не найдена.")

        if current_active_version.status == models.PlanStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Нельзя создать новую версию из черновика. Сначала одобрите текущую версию.")

        current_active_version.is_active = False
        db.add(current_active_version)

        new_version_number = current_active_version.version_number + 1
        new_version = models.ProcurementPlanVersion(
            plan_id=plan_id,
            version_number=new_version_number,
            status=models.PlanStatus.DRAFT,
            is_active=True,
            created_by=user.id,
            total_amount=current_active_version.total_amount,
            import_percentage=current_active_version.import_percentage
        )
        db.add(new_version)
        db.flush()

        new_items = []
        for item in current_active_version.items:
            if not item.is_deleted:
                new_item_data = {
                    key: getattr(item, key)
                    for key in item.__table__.columns.keys()
                    if key not in ['id', 'version_id', 'created_at']
                }
                new_item_data['version_id'] = new_version.id

                new_item_data['root_item_id'] = item.root_item_id if item.root_item_id else item.id
                new_item_data[
                    'source_version_id'] = item.source_version_id if item.source_version_id else current_active_version.id

                new_items.append(models.PlanItemVersion(**new_item_data))

                for execution in item.executions:
                    new_execution_data = {
                        key: getattr(execution, key)
                        for key in execution.__table__.columns.keys()
                        if key not in ['id', 'plan_item_id', 'created_at']
                    }
                    new_execution = models.PlanItemExecution(**new_execution_data)
                    new_execution.plan_item = new_items[-1]

        if new_items:
            db.add_all(new_items)

        db.commit()

        _recalculate_version_metrics(db, new_version.id)

        db.refresh(new_version)
        return new_version
    except Exception:
        db.rollback()
        raise


def delete_latest_version(db: Session, plan_id: int, user: models.User):
    db.begin_nested()
    try:
        active_version = _get_active_version(db, plan_id, lock=True)
        if not active_version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Активная версия не найдена.")

        if active_version.status != models.PlanStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Удалять можно только версию в статусе 'Черновик'.")

        if active_version.version_number == 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Нельзя удалить самую первую версию. Вместо этого удалите весь план.")

        previous_version = db.query(models.ProcurementPlanVersion).filter(
            models.ProcurementPlanVersion.plan_id == plan_id,
            models.ProcurementPlanVersion.version_number == active_version.version_number - 1
        ).with_for_update().first()

        if not previous_version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Предыдущая версия не найдена для восстановления.")

        db.delete(active_version)

        previous_version.is_active = True
        db.add(previous_version)

        db.commit()
        return {
            "message": f"Версия {active_version.version_number} удалена. Активной стала версия {previous_version.version_number}."}
    except Exception:
        db.rollback()
        raise


def delete_plan(db: Session, plan_id: int):
    plan_to_delete = db.query(models.ProcurementPlan).options(
        selectinload(models.ProcurementPlan.versions)
    ).filter(models.ProcurementPlan.id == plan_id).first()

    if not plan_to_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="План не найден.")

    has_approved_version = any(
        v.status in [models.PlanStatus.PRE_APPROVED, models.PlanStatus.APPROVED]
        for v in plan_to_delete.versions
    )
    if has_approved_version:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Нельзя удалить план, который уже был одобрен.")

    db.delete(plan_to_delete)
    db.commit()
    return True


# ========= Сервисы для Позиций Плана (PlanItemVersion) =========

def add_item_to_plan(db: Session, plan_id: int, item_in: plan_schema.PlanItemCreate,
                     user: models.User) -> models.PlanItemVersion:
    active_version = _get_active_version(db, plan_id)
    if not active_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Активная версия плана не найдена")
    if active_version.status != models.PlanStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Добавлять позиции можно только в черновик.")

    enstru_item = db.query(models.Enstru).filter(models.Enstru.code == item_in.trucode).first()
    if not enstru_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код ЕНС ТРУ не найден")

    # Используем хелпер
    need_type = get_need_type_by_typename(enstru_item.type_name)

    # Ищем последний номер позиции ДЛЯ ЭТОГО ТИПА
    last_item = db.query(models.PlanItemVersion).filter(
        models.PlanItemVersion.version_id == active_version.id,
        models.PlanItemVersion.need_type == need_type  # Фильтр по типу
    ).order_by(desc(models.PlanItemVersion.item_number)).first()

    item_number = (last_item.item_number + 1) if last_item else 1

    total_amount = item_in.quantity * item_in.price_per_unit

    # Если указан unit_id, сбрасываем original_unit_name
    original_unit_name = item_in.original_unit_name
    if item_in.unit_id:
        original_unit_name = None

    db_item = models.PlanItemVersion(
        **item_in.model_dump(exclude={'original_unit_name'}),
        original_unit_name=original_unit_name,
        version_id=active_version.id,
        item_number=item_number,
        total_amount=total_amount,
        need_type=need_type,
        source_version_id=active_version.id,
        revision_number=0
    )
    db.add(db_item)
    db.flush()
    db_item.root_item_id = db_item.id

    # Пересчет метрик и коммит
    _recalculate_version_metrics(db, active_version.id)

    db.refresh(db_item)
    return db_item


def compare_versions(db: Session, plan_id: int, version1_id: int, version2_id: int) -> dict:
    """
    Сравнивает две версии плана и возвращает различия.
    """
    # Загружаем версии вместе с позициями и справочником ЕНС ТРУ для названия
    v1 = db.query(models.ProcurementPlanVersion).filter(
        models.ProcurementPlanVersion.id == version1_id,
        models.ProcurementPlanVersion.plan_id == plan_id
    ).options(
        selectinload(models.ProcurementPlanVersion.items).joinedload(models.PlanItemVersion.enstru)
    ).first()

    v2 = db.query(models.ProcurementPlanVersion).filter(
        models.ProcurementPlanVersion.id == version2_id,
        models.ProcurementPlanVersion.plan_id == plan_id
    ).options(
        selectinload(models.ProcurementPlanVersion.items).joinedload(models.PlanItemVersion.enstru)
    ).first()

    if not v1 or not v2:
        raise HTTPException(status_code=404, detail="Одна из версий не найдена")

    items1 = {i.root_item_id: i for i in v1.items if not i.is_deleted}
    items2 = {i.root_item_id: i for i in v2.items if not i.is_deleted}

    added = []
    removed = []
    changed = []

    # Поиск добавленных
    for root_id, item in items2.items():
        if root_id not in items1:
            added.append({
                "id": item.id,
                "item_number": item.item_number,
                "trucode": item.trucode,
                "name": item.enstru.name_rus if item.enstru else "",
                "amount": item.total_amount
            })
        else:
            # Проверка изменений
            old_item = items1[root_id]
            changes = []

            if old_item.quantity != item.quantity:
                changes.append({"field": "quantity", "old": old_item.quantity, "new": item.quantity})
            if old_item.price_per_unit != item.price_per_unit:
                changes.append({"field": "price", "old": old_item.price_per_unit, "new": item.price_per_unit})
            if old_item.total_amount != item.total_amount:
                changes.append({"field": "total_amount", "old": old_item.total_amount, "new": item.total_amount})
            if old_item.trucode != item.trucode:
                changes.append({"field": "trucode", "old": old_item.trucode, "new": item.trucode})
            if old_item.additional_specs != item.additional_specs:
                changes.append(
                    {"field": "additional_specs", "old": old_item.additional_specs, "new": item.additional_specs})

            if changes:
                changed.append({
                    "item_id": item.id,
                    "item_number": item.item_number,
                    "root_item_id": root_id,
                    "trucode": item.trucode,
                    "name": item.enstru.name_rus if item.enstru else "",
                    "changes": changes
                })

    # Поиск удаленных
    for root_id, item in items1.items():
        if root_id not in items2:
            removed.append({
                "id": item.id,
                "item_number": item.item_number,
                "trucode": item.trucode,
                "name": item.enstru.name_rus if item.enstru else "",
                "amount": item.total_amount
            })

    # Сортировка списков по номеру позиции
    added.sort(key=lambda x: x['item_number'])
    removed.sort(key=lambda x: x['item_number'])
    changed.sort(key=lambda x: x['item_number'])

    return {
        "version1": v1.version_number,
        "version2": v2.version_number,
        "added_count": len(added),
        "removed_count": len(removed),
        "changed_count": len(changed),
        "added_items": added,
        "removed_items": removed,
        "changed_items": changed
    }
