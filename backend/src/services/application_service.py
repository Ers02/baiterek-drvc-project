from sqlalchemy.orm import Session
from src.models.application import Application, ApplicationState
from src.schemas.application import ApplicationCreate, ApplicationUpdate
from src.utils.docx_generator import generate_docx


def get_next_number(db: Session) -> int:
    last = db.query(Application).order_by(Application.number.desc()).first()
    return (last.number if last else 0) + 1


def create_application(db: Session, app_in: ApplicationCreate, user: dict):
    number = get_next_number(db)
    db_app = Application(**app_in.dict(), number=number)
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app


def get_applications(db: Session, state: str = None, skip: int = 0, limit: int = 100):
    query = db.query(Application)
    if state:
        query = query.filter(Application.state == ApplicationState(state))
    return query.offset(skip).limit(limit).all()


def get_application(db: Session, app_id: int):
    return db.query(Application).filter(Application.id == app_id).first()


def update_application(db: Session, app_id: int, app_in: ApplicationUpdate):
    db_app = get_application(db, app_id)
    if not db_app:
        return None
    update_data = app_in.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_app, key, value)
    db.commit()
    db.refresh(db_app)
    return db_app


def change_application_state(db: Session, app_id: int, new_state: str):
    db_app = get_application(db, app_id)
    if not db_app:
        return None

    allowed_transitions = {
        "draft": ["submitted"],
        "submitted": ["pre_approved"],
        "pre_approved": ["bank_discussed"],
        "bank_discussed": ["final_approved"],
    }

    current = db_app.state.value
    if new_state not in allowed_transitions.get(current, []):
        raise ValueError(f"Недопустимый переход из {current} в {new_state}")

    db_app.state = ApplicationState(new_state)
    db.commit()
    db.refresh(db_app)
    return db_app


def generate_docx_bytes(db: Session, app_id: int):
    app = get_application(db, app_id)
    if not app:
        return None
    return generate_docx(app)