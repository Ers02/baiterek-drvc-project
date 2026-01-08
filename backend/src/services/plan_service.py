from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func, desc, and_
from decimal import Decimal
from fastapi import HTTPException, status
import io
import openpyxl
import statistics
from ..models import models
from ..schemas import plan as plan_schema

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
    """Пересчитывает общую сумму и другие метрики для конкретной версии плана."""
    version = db.query(models.ProcurementPlanVersion).filter(models.ProcurementPlanVersion.id == version_id).first()
    if not version:
        return

    # Получаем все не удаленные позиции
    items = db.query(models.PlanItemVersion).filter(
        models.PlanItemVersion.version_id == version_id,
        models.PlanItemVersion.is_deleted == False
    ).all()

    total_amount = Decimal('0.00')
    ktp_amount = Decimal('0.00')
    
    vc_values = [] # Список значений ВЦ для расчета медианы и среднего
    vc_amount_total = Decimal('0.00')

    for item in items:
        total_amount += item.total_amount
        if item.is_ktp:
            ktp_amount += item.total_amount
        
        # Поиск минимального dvc_percent в реестре КТП
        # Ищем по коду ЕНС ТРУ (trucode)
        # Если записей несколько, берем минимальный процент
        min_dvc = db.query(func.min(models.Reestr_KTP.dvc_percent)).filter(
            models.Reestr_KTP.enstru_code == item.trucode
        ).scalar()
        
        # Если в реестре нет данных, считаем 0
        # Используем str() для безопасного преобразования float в Decimal
        item_dvc_percent = Decimal(str(min_dvc)) if min_dvc is not None else Decimal('0.00')
        
        # Сохраняем найденный процент в позицию
        item.min_dvc_percent = item_dvc_percent
        
        # Для расчета общих показателей ВЦ:
        # ВЦ позиции = Сумма позиции * (Процент ВЦ / 100)
        item_vc_amount = item.total_amount * (item_dvc_percent / Decimal('100.00'))
        vc_amount_total += item_vc_amount
        
        # Собираем проценты для статистики (только если сумма > 0, чтобы не искажать среднее пустыми строками)
        if item.total_amount > 0:
             vc_values.append(float(item_dvc_percent))

    # Расчет процентов КТП/Импорт
    if total_amount > 0:
        ktp_percentage = (ktp_amount / total_amount * 100)
        import_percentage = Decimal('100.00') - ktp_percentage
    else:
        ktp_percentage = Decimal('0.00')
        import_percentage = Decimal('0.00')

    # Расчет статистики ВЦ
    if vc_values:
        vc_mean = Decimal(str(statistics.mean(vc_values)))
        vc_median = Decimal(str(statistics.median(vc_values)))
    else:
        vc_mean = Decimal('0.00')
        vc_median = Decimal('0.00')

    version.total_amount = total_amount
    version.ktp_percentage = ktp_percentage
    version.import_percentage = import_percentage
    
    version.vc_mean = vc_mean
    version.vc_median = vc_median
    version.vc_amount = vc_amount_total

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


def update_plan_status(db: Session, plan_id: int, new_status: models.PlanStatus, user: models.User) -> models.ProcurementPlanVersion:
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
            selectinload(models.ProcurementPlanVersion.items)
        ).with_for_update().first()

        if not current_active_version:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Активная версия не найдена.")

        if current_active_version.status == models.PlanStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя создать новую версию из черновика. Сначала одобрите текущую версию.")

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
            ktp_percentage=current_active_version.ktp_percentage,
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
                new_item_data['source_version_id'] = item.source_version_id if item.source_version_id else current_active_version.id
                
                # revision_number копируется автоматически, так как он есть в new_item_data
                
                new_items.append(models.PlanItemVersion(**new_item_data))

        if new_items:
            db.bulk_save_objects(new_items)

        db.commit()
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
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Удалять можно только версию в статусе 'Черновик'.")

        if active_version.version_number == 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя удалить самую первую версию. Вместо этого удалите весь план.")

        previous_version = db.query(models.ProcurementPlanVersion).filter(
            models.ProcurementPlanVersion.plan_id == plan_id,
            models.ProcurementPlanVersion.version_number == active_version.version_number - 1
        ).with_for_update().first()

        if not previous_version:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Предыдущая версия не найдена для восстановления.")

        db.query(models.PlanItemVersion).filter(
            models.PlanItemVersion.version_id == active_version.id
        ).delete(synchronize_session=False)

        db.delete(active_version)

        previous_version.is_active = True
        db.add(previous_version)

        db.commit()
        return {"message": f"Версия {active_version.version_number} удалена. Активной стала версия {previous_version.version_number}."}
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нельзя удалить план, который уже был одобрен.")

    db.delete(plan_to_delete)
    db.commit()
    return True

# ========= Сервисы для Позиций Плана (PlanItemVersion) =========

def add_item_to_plan(db: Session, plan_id: int, item_in: plan_schema.PlanItemCreate, user: models.User) -> models.PlanItemVersion:
    active_version = _get_active_version(db, plan_id)
    if not active_version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Активная версия плана не найдена")
    if active_version.status != models.PlanStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Добавлять позиции можно только в черновик.")

    enstru_item = db.query(models.Enstru).filter(models.Enstru.code == item_in.trucode).first()
    if not enstru_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код ЕНС ТРУ не найден")

    last_item = db.query(models.PlanItemVersion).filter(
        models.PlanItemVersion.version_id == active_version.id
    ).order_by(desc(models.PlanItemVersion.item_number)).first()
    
    item_number = (last_item.item_number + 1) if last_item else 1

    total_amount = item_in.quantity * item_in.price_per_unit

    db_item = models.PlanItemVersion(
        **item_in.model_dump(),
        version_id=active_version.id,
        item_number=item_number,
        total_amount=total_amount,
        need_type=models.NeedType(enstru_item.type_ru),
        source_version_id=active_version.id,
        revision_number=0 # Новая позиция, редакция 0
    )
    db.add(db_item)
    db.flush()
    db_item.root_item_id = db_item.id
    db.commit()

    _recalculate_version_metrics(db, active_version.id)

    db.refresh(db_item)
    return db_item

def export_plan_to_excel(db: Session, plan_id: int, version_id: int = None) -> bytes:
    if version_id:
        version = db.query(models.ProcurementPlanVersion).filter(models.ProcurementPlanVersion.id == version_id).first()
    else:
        version = _get_active_version(db, plan_id)

    if not version:
        raise HTTPException(status_code=404, detail="Версия сметы не найдена")

    version_with_items = db.query(models.ProcurementPlanVersion).options(
        selectinload(models.ProcurementPlanVersion.items).options(
            joinedload(models.PlanItemVersion.enstru),
            joinedload(models.PlanItemVersion.unit)
        ),
        joinedload(models.ProcurementPlanVersion.plan)
    ).filter(models.ProcurementPlanVersion.id == version.id).one()


    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Смета {version_with_items.plan.id} v{version_with_items.version_number}"

    headers = [
        "№", "Код ЕНС ТРУ", "Наименование", "Ед. изм.",
        "Кол-во", "Цена за ед.", "Общая сумма", "КТП", "Резидент"
    ]
    ws.append(headers)

    for item in version_with_items.items:
        row = [
            item.item_number,
            item.trucode,
            item.enstru.name_ru if item.enstru else "",
            item.unit.name_ru if item.unit else "",
            item.quantity,
            item.price_per_unit,
            item.total_amount,
            "Да" if item.is_ktp else "Нет",
            "Да" if item.is_resident else "Нет",
        ]
        ws.append(row)

    virtual_workbook = io.BytesIO()
    wb.save(virtual_workbook)
    return virtual_workbook.getvalue()
