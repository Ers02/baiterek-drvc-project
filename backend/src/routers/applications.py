from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from src.database.database import get_db
from src.schemas.application import ApplicationCreate, ApplicationUpdate, ApplicationResponse
from src.services.application_service import (
    create_application, get_applications, get_application,
    update_application, change_application_state, generate_docx_bytes
)
from src.utils.auth import get_current_user
from typing import List
import io

router = APIRouter()


@router.post("/", response_model=ApplicationResponse)
def create(app: ApplicationCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return create_application(db, app, user)


@router.get("/", response_model=List[ApplicationResponse])
def list_apps(state: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_applications(db, state, skip, limit)


@router.get("/{app_id}", response_model=ApplicationResponse)
def get_one(app_id: int, db: Session = Depends(get_db)):
    app = get_application(db, app_id)
    if not app:
        raise HTTPException(404, "Заявка не найдена")
    return app


@router.put("/{app_id}", response_model=ApplicationResponse)
def update(app_id: int, app_in: ApplicationUpdate, db: Session = Depends(get_db)):
    updated = update_application(db, app_id, app_in)
    if not updated:
        raise HTTPException(404, "Заявка не найдена")
    return updated


@router.post("/{app_id}/state/{new_state}")
def set_state(app_id: int, new_state: str, db: Session = Depends(get_db)):
    try:
        app = change_application_state(db, app_id, new_state)
        if not app:
            raise HTTPException(404, "Заявка не найдена")
        return {"message": "Статус обновлён", "state": app.state.value}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{app_id}/download-docx")
def download_docx(app_id: int, db: Session = Depends(get_db)):
    docx_bytes = generate_docx_bytes(db, app_id)
    if not docx_bytes:
        raise HTTPException(404, "Заявка не найдена")

    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename=application_{app_id}.docx"}
    )