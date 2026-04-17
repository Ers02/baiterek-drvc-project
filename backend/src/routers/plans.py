import io
from typing import List, Union
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database.database import get_db
from ..schemas import plan as plan_schema
from ..services import plan_service, import_service
from ..services.exporters import plan_exporter
from ..utils.auth import get_current_user
from ..models import models
from ..models.models import UserRole

router = APIRouter(
    prefix="/plans",
    tags=["Procurement Plans & Versions"]
)


@router.post("/", response_model=plan_schema.ProcurementPlan, status_code=status.HTTP_201_CREATED)
def create_procurement_plan(
        plan_in: plan_schema.ProcurementPlanCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Аналитик ДРВЦ может создавать планы
    # if current_user.role == UserRole.ANALYST_DRVC:
    #     raise HTTPException(status_code=403, detail="Администратор не может создавать планы")

    return plan_service.create_plan(db=db, plan_in=plan_in, user=current_user)


@router.get("/", response_model=List[plan_schema.ProcurementPlanWithVersions])
def read_user_procurement_plans(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    if current_user.role == UserRole.ANALYST_DRVC:
        # Аналитик ДРВЦ видит все планы
        return plan_service.get_all_plans(db, skip=skip, limit=limit)

    plans = plan_service.get_plans_by_user(db, user=current_user, skip=skip, limit=limit)
    return plans


@router.get("/{plan_id}", response_model=plan_schema.ProcurementPlanWithFullActiveVersion)
def read_procurement_plan_with_active_version(
        plan_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_plan = plan_service.get_plan_with_active_version(db, plan_id=plan_id)
    if db_plan is None:
        raise HTTPException(status_code=404, detail="План не найден")

    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and db_plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для доступа к этому плану")

    return db_plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_procurement_plan(
        plan_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_plan = plan_service.get_plan_with_active_version(db, plan_id=plan_id)
    if db_plan is None:
        raise HTTPException(status_code=404, detail="План не найден")

    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and db_plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для удаления этого плана")

    plan_service.delete_plan(db=db, plan_id=plan_id)
    return {"ok": True}


@router.post("/{plan_id}/versions", response_model=plan_schema.ProcurementPlanVersion)
def create_new_version(
        plan_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Аналитик ДРВЦ может создавать версии
    # if current_user.role == UserRole.ANALYST_DRVC:
    #      raise HTTPException(status_code=403, detail="Администратор не может создавать версии")

    db_plan = plan_service.get_plan_with_active_version(db, plan_id=plan_id)
    # Аналитик ДРВЦ может работать с любыми планами
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and db_plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для создания новой версии")

    return plan_service.create_new_version_for_editing(db=db, plan_id=plan_id, user=current_user)


@router.patch("/{plan_id}/versions/active/status", response_model=plan_schema.ProcurementPlanVersion)
def update_active_version_status(
        plan_id: int,
        status_in: plan_schema.ProcurementPlanStatusUpdate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_plan = plan_service.get_plan_with_active_version(db, plan_id=plan_id)

    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and db_plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для изменения статуса")

    return plan_service.update_plan_status(db=db, plan_id=plan_id, new_status=status_in.status, user=current_user)


@router.delete("/{plan_id}/versions/latest", status_code=status.HTTP_200_OK)
def delete_latest_plan_version(
        plan_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_plan = plan_service.get_plan_with_active_version(db, plan_id=plan_id)

    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and db_plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для удаления версии")

    return plan_service.delete_latest_version(db=db, plan_id=plan_id, user=current_user)


@router.get("/{plan_id}/versions/{version_id}/export-excel")
def export_version_to_excel(
        plan_id: int,
        version_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_plan = plan_service.get_plan_with_active_version(db, plan_id=plan_id)

    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and db_plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для экспорта")

    excel_data = plan_exporter.export_plan_to_excel(db, plan_id, version_id)

    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="plan_{plan_id}_v{version_id}.xlsx"'}
    )


@router.get("/{plan_id}/compare", tags=["Versions"])
def compare_plan_versions(
        plan_id: int,
        v1_id: int,
        v2_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    db_plan = plan_service.get_plan_with_active_version(db, plan_id=plan_id)

    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and db_plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для просмотра этого плана")

    return plan_service.compare_versions(db, plan_id, v1_id, v2_id)


@router.post("/{plan_id}/items", response_model=plan_schema.PlanItem, status_code=status.HTTP_201_CREATED)
def create_plan_item_for_active_version(
        plan_id: int,
        item_in: plan_schema.PlanItemCreate,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Аналитик ДРВЦ может добавлять позиции
    # if current_user.role == UserRole.ANALYST_DRVC:
    #      raise HTTPException(status_code=403, detail="Администратор не может добавлять позиции")

    db_plan = plan_service.get_plan_with_active_version(db, plan_id=plan_id)
    # Аналитик ДРВЦ может работать с любыми планами
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST_DRVC] and db_plan.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав для добавления в эту смету")

    return plan_service.add_item_to_plan(db=db, plan_id=plan_id, item_in=item_in, user=current_user)


@router.get("/template/download", tags=["Import"])
def download_import_template(db: Session = Depends(get_db)):
    excel_data = import_service.generate_import_template(db)
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="import_template.xlsx"'}
    )


@router.post("/{plan_id}/import", tags=["Import"])
def import_items_from_file(
        plan_id: int,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    # Аналитик ДРВЦ может импортировать данные
    # if current_user.role == UserRole.ANALYST_DRVC:
    #      raise HTTPException(status_code=403, detail="Администратор не может импортировать данные")

    return import_service.process_import_file(db=db, plan_id=plan_id, file=file, user=current_user,
                                              background_tasks=background_tasks)


@router.post("/import-kenml-template", tags=["Import"])
def import_kenml_and_generate_template(
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user)
):
    excel_data = import_service.process_kenml_import(db=db, file=file)
    return StreamingResponse(
        io.BytesIO(excel_data),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment; filename="filled_import_template.xlsx"'}
    )
