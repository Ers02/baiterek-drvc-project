from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File, Form, Body
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional, Literal
from datetime import datetime, timezone
from fastapi.responses import FileResponse
import os
import shutil
import uuid
import httpx
from ..database.database import get_db
from ..models import models
from ..services.psd_analyst_service import PsdAnalystService
from ..utils.auth import get_current_admin, get_current_user, get_current_director_or_admin, get_current_analyst_manager
from ..schemas.psd import (
    ExternalDocumentSchema, PsdItemsResponse,
    SaveMatchRequest, AgskEnstruMatchesResponse, CreateAgskEnstruMatchRequest,
    CreateAgskEnstruMatchBatchRequest,
)
from ..core.config import settings
from ..core.logger import logger

router = APIRouter(
    prefix="/psd-analyst",
    tags=["PSD Analyst"],
    dependencies=[Depends(get_current_admin)]
)

psd_service = PsdAnalystService()

@router.post("/upload-test", response_model=ExternalDocumentSchema)
async def upload_test_psd(
    file: UploadFile = File(...),
    project_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Загрузка тестового файла. Сохраняется как один файл (zip или kenml).
    """
    upload_dir = os.path.abspath(os.path.join(settings.UPLOAD_DIR, "psd_test"))
    os.makedirs(upload_dir, exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ['.kenml', '.zip']:
        raise HTTPException(status_code=400, detail="Поддерживаются только файлы .kenml и .zip")

    unique_filename = f"test_{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Сохраняем ОДИН файл (архив или kenml)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Создаем запись в БД
    doc = models.ExternalDocument(
        doc_type="PSD",
        bank_name=f"[ТЕСТ] {project_name}",
        received_at=datetime.now(timezone.utc),
        file_path=file_path,
        status="NEW",
        is_test=True,
        assigned_to=current_user.id,
        assigned_at=datetime.now(timezone.utc),
        notes=f"Тестовый проект. Оригинальный файл: {file.filename}"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Запускаем парсинг (сервис теперь сам разберется, ZIP это или KENML)
    try:
        psd_service.parse_psd_file(db, doc.id, file_path)
        return doc
    except Exception as e:
        doc.status = "ERROR"
        doc.error_message = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")

@router.get("/documents")
def get_psd_documents(
    doc_status: Optional[str] = Query(None, alias="status"),
    assigned_to_me: bool = Query(False),
    is_test: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    query = db.query(models.ExternalDocument).options(joinedload(models.ExternalDocument.assigned_user))
    # Показываем все документы: PSD и SMETA

    if doc_status:
        query = query.filter(models.ExternalDocument.status == doc_status)
    
    if assigned_to_me:
        query = query.filter(models.ExternalDocument.assigned_to == current_user.id)
    
    if is_test is not None:
        query = query.filter(models.ExternalDocument.is_test == is_test)
    else:
        query = query.filter(models.ExternalDocument.is_test == False)
        
    docs = query.order_by(models.ExternalDocument.received_at.desc()).all()
    
    result = []
    for doc in docs:
        doc_dict = {c.name: getattr(doc, c.name) for c in doc.__table__.columns}
        doc_dict["assigned_user_name"] = doc.assigned_user.full_name if doc.assigned_user else None
        result.append(doc_dict)
        
    return result

@router.post("/documents/{doc_id}/assign-analyst")
def assign_to_analyst(
    doc_id: int,
    analyst_id: int = Query(...),
    days: int = Query(5, ge=1, le=10, description="Срок в рабочих днях (1-10)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """Директор назначает аналитика и срок выполнения."""
    if days < 1 or days > 10:
        raise HTTPException(status_code=400, detail="Срок выполнения должен быть от 1 до 10 рабочих дней")
    try:
        doc = psd_service.assign_to_analyst(db, doc_id, analyst_id, days)
        return {"status": "success", "deadline": doc.deadline_at}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/documents/{doc_id}/submit-approval")
def submit_for_approval(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Аналитик отправляет на утверждение директору.
    Блокируется если есть GOODS-позиции:
    - без выбора поставщика вообще (ни active, ни pending)
    - с только pending-выборами (ожидают одобрения менеджером-аналитиком)
    Позиции с active-выбором или отмеченные «нет в реестре» — считаются обработанными."""

    from sqlalchemy import or_ as _or_

    # Subquery: все item_id с хотя бы одним активным выбором поставщика
    active_sel_item_ids_subq = db.query(models.PsdItemSupplierSelection.item_id).filter(
        models.PsdItemSupplierSelection.status == 'active',
        models.PsdItemSupplierSelection.is_active == True,
    ).subquery()

    # Позиции без активного выбора поставщика и без отметки «нет в реестре»
    # (включает позиции с только pending-выборами — они ещё не обработаны)
    unprocessed_items = db.query(models.PsdDocumentItem).filter(
        models.PsdDocumentItem.document_id == doc_id,
        models.PsdDocumentItem.item_type.in_(['GOODS', None]),
        _or_(
            models.PsdDocumentItem.not_in_ktp_registry == False,
            models.PsdDocumentItem.not_in_ktp_registry == None,
        ),
        ~models.PsdDocumentItem.id.in_(active_sel_item_ids_subq),
    ).all()

    if unprocessed_items:
        # Разделяем: pending-ожидающие vs совсем не обработанные
        pending_item_ids_subq = db.query(models.PsdItemSupplierSelection.item_id).filter(
            models.PsdItemSupplierSelection.status == 'pending',
            models.PsdItemSupplierSelection.is_active == True,
        ).subquery()
        unprocessed_ids = {it.id for it in unprocessed_items}
        pending_ids = {
            row.item_id
            for row in db.query(models.PsdItemSupplierSelection.item_id).filter(
                models.PsdItemSupplierSelection.item_id.in_(list(unprocessed_ids)),
                models.PsdItemSupplierSelection.status == 'pending',
                models.PsdItemSupplierSelection.is_active == True,
            ).all()
        }
        truly_unprocessed = [it for it in unprocessed_items if it.id not in pending_ids]
        pending_items = [it for it in unprocessed_items if it.id in pending_ids]

        error_parts = []
        if truly_unprocessed:
            names = [f"{it.position_number or '—'}: {it.name[:45]}..." for it in truly_unprocessed[:5]]
            error_parts.append(
                f"Не обработано ({len(truly_unprocessed)} шт.):\n" + "\n".join(names) +
                (f"\n... и ещё {len(truly_unprocessed) - 5}" if len(truly_unprocessed) > 5 else "")
            )
        if pending_items:
            names = [f"{it.position_number or '—'}: {it.name[:45]}..." for it in pending_items[:5]]
            error_parts.append(
                f"Ожидают одобрения менеджером ({len(pending_items)} шт.):\n" + "\n".join(names) +
                (f"\n... и ещё {len(pending_items) - 5}" if len(pending_items) > 5 else "")
            )
        raise HTTPException(
            status_code=400,
            detail="Нельзя отправить на утверждение.\n" + "\n\n".join(error_parts)
        )

    try:
        psd_service.submit_for_approval(db, doc_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/documents/{doc_id}/approve")
def approve_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """Директор утверждает документ. Генерируется финальный ZIP."""
    try:
        psd_service.approve_document(db, doc_id, current_user)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/documents/{doc_id}/reject")
def reject_document(
    doc_id: int, 
    comment: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """Директор возвращает на доработку с комментарием."""
    try:
        psd_service.reject_document(db, doc_id, comment)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/delegate")
def delegate_authority(
    to_user_id: int = Query(...),
    days: int = Query(14),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """Директор делегирует права другому пользователю."""
    try:
        psd_service.delegate_authority(db, current_user.id, to_user_id, days)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/analysts", response_model=List[dict])
def get_analysts_list(db: Session = Depends(get_db)):
    """Список аналитиков для назначения."""
    users = db.query(models.User).filter(models.User.role == models.UserRole.ANALYST_DRVC).all()
    return [{"id": u.id, "full_name": u.full_name} for u in users]


@router.get("/library-users", response_model=List[dict])
def get_library_users(db: Session = Depends(get_db)):
    """Все пользователи которые могут создавать сопоставления — для фильтра библиотеки."""
    roles = [
        models.UserRole.ANALYST_DRVC,
        models.UserRole.ANALYST_MANAGER,
        models.UserRole.DIRECTOR_DRVC,
    ]
    users = db.query(models.User).filter(models.User.role.in_(roles)).order_by(models.User.full_name).all()
    role_labels = {
        models.UserRole.ANALYST_DRVC: "Аналитик",
        models.UserRole.ANALYST_MANAGER: "Менеджер аналитиков",
        models.UserRole.DIRECTOR_DRVC: "Директор ДРВЦ",
    }
    return [{"id": u.id, "full_name": u.full_name, "role_label": role_labels.get(u.role, u.role)} for u in users]

@router.get("/document-items/{doc_id}", response_model=PsdItemsResponse)
def get_document_items(doc_id: int, only_unmatched: bool = False, search: Optional[str] = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return psd_service.get_document_items_with_matches(db, doc_id, only_unmatched, search, skip, limit)

@router.get("/document-items/{doc_id}/item/{item_id}")
def get_document_item(doc_id: int, item_id: int, db: Session = Depends(get_db)):
    """Получить одну позицию документа с актуальными данными.

    Дополнительно возвращает previous_agsk_selections — ранее выбранные поставщики
    для того же АГСК-кода в других документах. Если поставщик стал неактивным
    в реестре КТП — помечается ktp_is_active=False.
    """
    item = db.query(models.PsdDocumentItem).filter(
        models.PsdDocumentItem.id == item_id,
        models.PsdDocumentItem.document_id == doc_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Позиция не найдена")

    # Загружаем инфо об АГСК
    agsk_info = None
    if item.code_sn:
        agsk_info = db.query(models.Agsk).filter(models.Agsk.code == item.code_sn).first()

    # Загружаем активные выборы поставщиков для этой позиции
    active_selections = db.query(models.PsdItemSupplierSelection).filter(
        models.PsdItemSupplierSelection.item_id == item_id,
        models.PsdItemSupplierSelection.is_active == True,
    ).order_by(models.PsdItemSupplierSelection.id.desc()).all()

    current_manual_matches = []
    for sel in active_selections:
        current_manual_matches.append({
            "id": sel.id,
            "enstru_code": sel.enstru_code or "",
            "status": sel.status,
            "ktp_id": sel.ktp_id,
            "supplier_name": sel.supplier_name,
            "supplier_bin": sel.supplier_bin,
            "supplier_product": sel.supplier_product,
            "dvc_percent": float(sel.dvc_percent) if sel.dvc_percent else None,
            "matched_at": sel.selected_at.isoformat() if sel.selected_at else None,
            "approved_at": None,
        })

    # ── Ранее выбирались для того же АГСК-кода (из других документов) ──────────
    previous_agsk_selections = []
    if item.code_sn:
        # Берём уникальные активные выборы поставщиков по тому же АГСК
        # из ДРУГИХ позиций (не текущей), группируем по ktp_id+enstru_code
        from sqlalchemy import func as _func
        prev_rows = (
            db.query(
                models.PsdItemSupplierSelection.ktp_id,
                models.PsdItemSupplierSelection.enstru_code,
                models.PsdItemSupplierSelection.supplier_bin,
                models.PsdItemSupplierSelection.supplier_name,
                models.PsdItemSupplierSelection.supplier_product,
                models.PsdItemSupplierSelection.dvc_percent,
                _func.count(models.PsdItemSupplierSelection.id).label("times_selected"),
                _func.max(models.PsdItemSupplierSelection.selected_at).label("last_selected_at"),
            )
            .filter(
                models.PsdItemSupplierSelection.agsk_code == item.code_sn,
                models.PsdItemSupplierSelection.item_id != item_id,
                models.PsdItemSupplierSelection.status == "active",
                models.PsdItemSupplierSelection.is_active == True,
            )
            .group_by(
                models.PsdItemSupplierSelection.ktp_id,
                models.PsdItemSupplierSelection.enstru_code,
                models.PsdItemSupplierSelection.supplier_bin,
                models.PsdItemSupplierSelection.supplier_name,
                models.PsdItemSupplierSelection.supplier_product,
                models.PsdItemSupplierSelection.dvc_percent,
            )
            .order_by(_func.count(models.PsdItemSupplierSelection.id).desc())
            .limit(10)
            .all()
        )

        # Для каждого уникального ktp_id проверяем is_active в реестре КТП
        ktp_ids_prev = list({r.ktp_id for r in prev_rows if r.ktp_id})
        ktp_active_map: dict = {}
        if ktp_ids_prev:
            ktp_recs = db.query(models.Reestr_KTP).filter(
                models.Reestr_KTP.id.in_(ktp_ids_prev)
            ).all()
            ktp_active_map = {r.id: r.is_active for r in ktp_recs}

        for r in prev_rows:
            ktp_is_active = ktp_active_map.get(r.ktp_id)  # True / False / None
            # None = поле не заполнено → считаем активным
            is_inactive = (ktp_is_active is False)
            previous_agsk_selections.append({
                "ktp_id": r.ktp_id,
                "enstru_code": r.enstru_code or "",
                "supplier_bin": r.supplier_bin or "",
                "supplier_name": r.supplier_name or "",
                "supplier_product": r.supplier_product or "",
                "dvc_percent": float(r.dvc_percent) if r.dvc_percent else None,
                "times_selected": r.times_selected,
                "last_selected_at": r.last_selected_at.isoformat() if r.last_selected_at else None,
                "ktp_is_active": not is_inactive,   # False = поставщик стал неактивным
            })

    return {
        "id": item.id,
        "item_id": item.id,
        "document_id": item.document_id,
        "position_number": item.position_number,
        "name": item.name,
        "code_sn": item.code_sn,
        "unit": item.unit,
        "volume": float(item.volume) if item.volume else 0,
        "price": float(item.price) if item.price else 0,
        "total_amount": float(item.total_amount) if item.total_amount else 0,
        "enstru_code": item.enstru_code,
        "enstru_name": item.enstru_name,
        "match_type": item.match_type,
        "match_score": item.match_score,
        "match_reason": item.match_reason,
        "not_in_ktp_registry": bool(item.not_in_ktp_registry) if item.not_in_ktp_registry is not None else False,
        "can_edit": True,
        "agsk_name_ru": agsk_info.name_ru if agsk_info else None,
        "agsk_full_name": agsk_info.full_name if agsk_info else None,
        "item_type": item.item_type or "GOODS",
        "current_manual_matches": current_manual_matches,
        "previous_agsk_selections": previous_agsk_selections,
    }

@router.get("/documents/{doc_id}/download-result")
def download_result_zip(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc or not doc.result_file_path or not os.path.exists(doc.result_file_path):
        raise HTTPException(status_code=404, detail="Файл результата не найден")

    return FileResponse(
        path=doc.result_file_path,
        filename=f"Analysis_Result_{doc_id}.zip",
        media_type="application/zip"
    )

@router.post("/documents/{doc_id}/parse")
def parse_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Выбираем парсер в зависимости от типа документа
    if doc.doc_type == "SMETA":
        psd_service.parse_smeta_file(db, doc_id, str(doc.file_path))
    elif doc.doc_type == "PSD":
        psd_service.parse_psd_file(db, doc_id, str(doc.file_path))
    else:
        raise HTTPException(status_code=400, detail=f"Неизвестный тип документа: {doc.doc_type}")

    return {"status": "success", "doc_type": doc.doc_type}

@router.get("/search-enstru-reestr")
def search_enstru_reestr(
    query: str = Query(..., min_length=1),
    search_mode: Literal["all", "agsk", "name"] = Query(default="all"),
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return psd_service.search_enstru_in_reestr(db, query=query, limit=limit, search_mode=search_mode)

@router.get("/export-full-report")
def export_full_analysis_report(
    doc_id: int = Query(..., description="Document ID to export"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    file_path = psd_service.export_full_analysis_report(db, doc_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Не удалось сгенерировать отчет")

    file_name = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@router.get("/documents/{doc_id}/conclusion")
def generate_conclusion_docx(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    file_path = psd_service.generate_psd_conclusion_docx(db, doc_id, current_user)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=500, detail="Не удалось сгенерировать заключение")

    file_name = f"Conclusion_PSD_{doc_id}.docx"
    return FileResponse(
        path=file_path,
        filename=file_name,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

@router.post("/documents/{doc_id}/analyst-comment")
def save_analyst_comment(
    doc_id: int,
    comment: str = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Аналитик сохраняет комментарий к заключению."""
    doc = db.query(models.ExternalDocument).filter(models.ExternalDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")

    # Проверяем, что текущий пользователь назначен как аналитик или является админом/директором
    if doc.assigned_to != current_user.id and current_user.role not in [models.UserRole.ADMIN, models.UserRole.DIRECTOR_DRVC]:
        raise HTTPException(status_code=403, detail="Нет прав для редактирования комментария")

    doc.analyst_comment = comment
    db.commit()
    return {"status": "success", "analyst_comment": comment}

@router.post("/documents/{doc_id}/send-to-do")
async def send_result_to_do(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_director_or_admin)
):
    """
    Отправляет результат анализа (ZIP архив) в дочернюю организацию через callback_url.
    Доступно только директору после утверждения документа.
    """
    from ..services.external_service import send_result_to_callback
    result = await send_result_to_callback(db, doc_id)
    return result


@router.post("/document-items/{item_id}/save-match")
def save_analyst_match(
    item_id: int,
    body: SaveMatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Аналитик выбирает поставщика из Реестра КТП для позиции ПСД.
    Создаёт запись в psd_item_supplier_selections + при необходимости в библиотеке."""
    try:
        selection = psd_service.add_supplier_selection(
            db,
            item_id=item_id,
            enstru_code=body.enstru_code,
            analyst_id=current_user.id,
            ktp_id=body.ktp_id,
            product_code=body.product_code,
            supplier_bin=body.supplier_bin,
            supplier_name=body.supplier_name,
            supplier_product=body.supplier_product,
            dvc_percent=body.dvc_percent,
        )
        return {
            "id": selection.id,
            "item_id": selection.item_id,
            "enstru_code": selection.enstru_code,
            "status": selection.status,
            "ktp_id": selection.ktp_id,
            "supplier_name": selection.supplier_name,
            "supplier_bin": selection.supplier_bin,
            "dvc_percent": float(selection.dvc_percent) if selection.dvc_percent else None,
            "selected_at": selection.selected_at.isoformat() if selection.selected_at else None,
        }
    except ValueError as e:
        msg = str(e)
        status_code = 409 if "уже выбран" in msg else 404
        raise HTTPException(status_code=status_code, detail=msg)


@router.get("/matches", response_model=AgskEnstruMatchesResponse)
def get_matches_library(
    analyst_id: Optional[int] = Query(None),
    date_filter: str = Query("all", description="'today' или 'all'"),
    search: Optional[str] = Query(None, description="Поиск по коду АГСК или ЕНСТРУ"),
    status_filter: Optional[str] = Query(None, description="pending | approved | rejected"),
    skip: int = Query(0),
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Глобальная библиотека АГСК→ЕНСТРУ сопоставлений. Аналитик видит только свои."""
    if current_user.role == models.UserRole.ANALYST_DRVC:
        analyst_id = current_user.id
    return psd_service.get_matches_library(db, analyst_id, date_filter, search, status_filter, skip, limit)


@router.post("/matches", response_model=AgskEnstruMatchesResponse.__annotations__['items'].__args__[0] if False else dict)
def create_match(
    payload: CreateAgskEnstruMatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Создать новую связку АГСК→ЕНСТРУ вручную. Отправляется на утверждение менеджеру."""
    try:
        match = psd_service.create_match(db, payload.agsk_code, payload.enstru_code, current_user.id)
        return {"id": match.id, "agsk_code": match.agsk_code, "enstru_code": match.enstru_code, "status": "pending"}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/matches/by-agsk/{agsk_code}")
def get_matches_by_agsk(
    agsk_code: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Все связки для данного АГСК-кода (для диалога создания)."""
    return psd_service.get_matches_by_agsk(db, agsk_code)


@router.post("/matches/batch")
def create_matches_batch(
    payload: CreateAgskEnstruMatchBatchRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Создать несколько связок АГСК→ЕНСТРУ за раз. Каждая отправляется на утверждение."""
    if not payload.enstru_codes:
        raise HTTPException(status_code=400, detail="Список ЕНСТРУ не может быть пустым")
    created, skipped = [], []
    for enstru_code in payload.enstru_codes:
        try:
            match = psd_service.create_match(db, payload.agsk_code, enstru_code, current_user.id)
            created.append({"id": match.id, "enstru_code": match.enstru_code})
        except ValueError:
            skipped.append(enstru_code)
    return {"created": created, "skipped": skipped, "agsk_code": payload.agsk_code}


@router.post("/matches/{match_id}/approve")
def approve_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_analyst_manager),
):
    """Менеджер утверждает сопоставление."""
    try:
        match = psd_service.approve_analyst_match(db, match_id, current_user.id)
        return {"status": "approved", "match_id": match.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/matches/{match_id}/reject")
def reject_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_analyst_manager),
):
    """Менеджер отклоняет сопоставление."""
    try:
        psd_service.reject_analyst_match(db, match_id)
        return {"status": "rejected", "match_id": match_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/matches/{match_id}")
def delete_match(
    match_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Удаляет выбор поставщика (по ID из psd_item_supplier_selections).
    Аналитик может удалить только свой выбор."""
    sel = db.query(models.PsdItemSupplierSelection).filter(
        models.PsdItemSupplierSelection.id == match_id
    ).first()
    if not sel:
        raise HTTPException(status_code=404, detail="Выбор поставщика не найден")
    if sel.selected_by != current_user.id and current_user.role not in [
        models.UserRole.ADMIN, models.UserRole.ANALYST_MANAGER
    ]:
        raise HTTPException(status_code=403, detail="Нет прав для удаления этого выбора")

    item_id = sel.item_id
    sel.is_active = False
    db.flush()

    # Если активных выборов не осталось — откатываем match_type позиции
    remaining = db.query(models.PsdItemSupplierSelection).filter(
        models.PsdItemSupplierSelection.item_id == item_id,
        models.PsdItemSupplierSelection.is_active == True,
    ).count()
    if remaining == 0:
        item = db.query(models.PsdDocumentItem).filter(models.PsdDocumentItem.id == item_id).first()
        if item:
            item.match_type = 'suggested' if item.enstru_code else 'none'
            item.match_reason = 'Подсказка из библиотеки — поставщик удалён, выберите нового из реестра КТП'

    db.commit()
    return {"status": "deleted", "match_id": match_id}


@router.post("/document-items/{item_id}/not-in-ktp-registry")
def save_not_in_ktp_registry(
    item_id: int,
    value: bool = Body(..., embed=True, description="true - нет в реестре КТП, false - сбросить"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Отмечает позицию как "Нет в реестре КТП".
    При установке true сбрасывает сопоставление и деактивирует записи в библиотеке для этого АГСК.
    """
    item = db.query(models.PsdDocumentItem).filter(models.PsdDocumentItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Позиция документа не найдена")

    item.not_in_ktp_registry = value

    # Если отмечено "нет в реестре", сбрасываем сопоставление
    if value:
        item.enstru_code = None
        item.enstru_name = None
        item.match_type = "none"
        item.match_score = None
        item.match_reason = None

        # Деактивируем выборы поставщиков для этой позиции
        db.query(models.PsdItemSupplierSelection).filter(
            models.PsdItemSupplierSelection.item_id == item_id,
            models.PsdItemSupplierSelection.is_active == True,
        ).update({"is_active": False, "status": "rejected"}, synchronize_session=False)

    db.commit()
    return {"status": "success", "item_id": item_id, "not_in_ktp_registry": value}
