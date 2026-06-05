"""Библиотека сопоставлений АГСК → ЕНСТРУ — утверждение / отклонение менеджером.

Используется как миксин в PsdAnalystService.
"""
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ..models.models import Agsk, AgskEnstruMatch, Enstru, PsdDocumentItem, User


class PsdLibraryMixin:
    def _apply_approved_match_to_all(self, db: Session, agsk_code: str, enstru_code: str) -> int:
        """Проставляет подсказку enstru_code для необработанных позиций с данным АГСК-кодом.
        Затрагивает позиции с match_type IN ('none', 'suggested', 'auto_ktp').
        НЕ переводит в match_type='manual' — позиции остаются «необработанными»
        до тех пор, пока аналитик не выберет поставщика из реестра КТП.

        Подсказку ставим ТОЛЬКО если в реестре КТП реально есть активный поставщик
        с этим ЕНСТРУ — иначе подсказка бесполезна (выбирать не из кого)."""
        # Проверка: есть ли в КТП активный поставщик с валидным ДВС для этого ЕНСТРУ.
        # `self` доступно через миксин-наследование (PsdSearchMixin._enstru_codes_with_active_supplier).
        has_supplier = enstru_code in self._enstru_codes_with_active_supplier(db, [enstru_code])
        if not has_supplier:
            return 0

        enstru_obj = db.query(Enstru).filter(Enstru.code == enstru_code).first()
        updated = db.query(PsdDocumentItem).filter(
            PsdDocumentItem.code_sn == agsk_code,
            PsdDocumentItem.match_type.in_(['none', 'suggested', 'auto_ktp']),
        ).update({
            "enstru_code": enstru_code,
            "enstru_name": enstru_obj.name_rus if enstru_obj else None,
            "match_type": "suggested",
            "match_score": 100,
            "match_reason": "Подсказка из утверждённой библиотеки — выберите поставщика из реестра КТП",
        }, synchronize_session=False)
        db.commit()
        return updated

    def approve_analyst_match(self, db: Session, match_id: int, manager_id: int) -> AgskEnstruMatch:
        """Менеджер утверждает библиотечную запись АГСК→ЕНСТРУ.
        1. Помечает пару как утверждённую (входит в библиотеку).
        2. Проставляет ЕНСТРУ-подсказку всем ещё несопоставленным позициям с этим АГСК.
        Выборы поставщиков аналитика уже активны — ничего не меняем."""
        match = db.query(AgskEnstruMatch).filter(AgskEnstruMatch.id == match_id).first()
        if not match:
            raise ValueError("Сопоставление не найдено")
        if not match.is_active:
            raise ValueError("Сопоставление неактивно (отклонено)")

        match.is_approved = True
        match.approved_by = manager_id
        match.approved_at = func.now()
        db.commit()

        # Проставляем ЕНСТРУ-подсказку всем ещё несопоставленным позициям с этим АГСК-кодом
        self._apply_approved_match_to_all(db, match.agsk_code, match.enstru_code)

        db.refresh(match)
        return match

    def reject_analyst_match(self, db: Session, match_id: int) -> AgskEnstruMatch:
        """Менеджер отклоняет библиотечную запись АГСК→ЕНСТРУ.
        Запись не войдёт в библиотеку — только деактивируем её.
        Выборы поставщиков аналитика НЕ затрагиваются: позиции остаются обработанными."""
        match = db.query(AgskEnstruMatch).filter(AgskEnstruMatch.id == match_id).first()
        if not match:
            raise ValueError("Сопоставление не найдено")
        match.is_active = False
        db.commit()
        db.refresh(match)
        return match

    def create_match(self, db: Session, agsk_code: str, enstru_code: str, created_by: int) -> AgskEnstruMatch:
        """Создаёт связку АГСК→ЕНСТРУ.
        - Если активная (pending/approved) уже есть — raise ValueError.
        - Если отклонённая (is_active=False) — реактивирует: сбрасывает approved, ставит нового автора.
        """
        # Проверяем активную
        active = db.query(AgskEnstruMatch).filter(
            AgskEnstruMatch.agsk_code == agsk_code,
            AgskEnstruMatch.enstru_code == enstru_code,
            AgskEnstruMatch.is_active == True,
        ).first()
        if active:
            raise ValueError("Такая связка уже существует")

        # Проверяем отклонённую — реактивируем
        rejected = db.query(AgskEnstruMatch).filter(
            AgskEnstruMatch.agsk_code == agsk_code,
            AgskEnstruMatch.enstru_code == enstru_code,
            AgskEnstruMatch.is_active == False,
        ).order_by(AgskEnstruMatch.id.desc()).first()
        if rejected:
            rejected.is_active = True
            rejected.is_approved = False
            rejected.approved_by = None
            rejected.approved_at = None
            rejected.created_by = created_by
            from sqlalchemy import func as sqlfunc
            rejected.created_at = sqlfunc.now()
            db.commit()
            db.refresh(rejected)
            return rejected

        match = AgskEnstruMatch(agsk_code=agsk_code, enstru_code=enstru_code, created_by=created_by)
        db.add(match)
        db.commit()
        db.refresh(match)
        return match

    def get_matches_by_agsk(self, db: Session, agsk_code: str) -> list:
        """Возвращает все связки для данного АГСК (active + rejected) — для отображения в диалоге создания."""
        matches = db.query(AgskEnstruMatch).filter(
            AgskEnstruMatch.agsk_code == agsk_code,
        ).order_by(AgskEnstruMatch.is_active.desc(), AgskEnstruMatch.is_approved.desc()).all()

        enstru_codes = [m.enstru_code for m in matches if m.enstru_code]
        enstru_map = {e.code: e for e in db.query(Enstru).filter(Enstru.code.in_(enstru_codes)).all()} if enstru_codes else {}

        result = []
        for m in matches:
            enstru_obj = enstru_map.get(m.enstru_code)
            if m.is_active and m.is_approved:
                status = "approved"
            elif m.is_active:
                status = "pending"
            else:
                status = "rejected"
            result.append({
                "id": m.id,
                "enstru_code": m.enstru_code,
                "enstru_name_rus": enstru_obj.name_rus if enstru_obj else None,
                "enstru_detail_rus": enstru_obj.detail_rus if enstru_obj else None,
                "status": status,
            })
        return result

    def get_matches_library(
        self, db: Session,
        analyst_id: Optional[int] = None,
        date_filter: str = "all",    # "today" | "all"
        search: Optional[str] = None,
        status_filter: Optional[str] = None,  # "pending" | "approved" | "rejected" | None
        skip: int = 0,
        limit: int = 100,
    ) -> Dict:
        """Возвращает глобальную библиотеку АГСК→ЕНСТРУ сопоставлений."""
        from sqlalchemy import or_
        query = db.query(AgskEnstruMatch)

        if analyst_id:
            query = query.filter(AgskEnstruMatch.created_by == analyst_id)

        if date_filter == "today":
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(AgskEnstruMatch.created_at >= today_start)

        if status_filter == "pending":
            query = query.filter(AgskEnstruMatch.is_active == True, AgskEnstruMatch.is_approved == False)
        elif status_filter == "approved":
            query = query.filter(AgskEnstruMatch.is_active == True, AgskEnstruMatch.is_approved == True)
        elif status_filter == "rejected":
            query = query.filter(AgskEnstruMatch.is_active == False)

        if search:
            like = f"%{search}%"
            # Ищем по коду АГСК или коду ЕНСТРУ (имена подтянем после)
            query = query.filter(
                or_(
                    AgskEnstruMatch.agsk_code.ilike(like),
                    AgskEnstruMatch.enstru_code.ilike(like),
                )
            )

        total = query.count()
        matches = query.order_by(desc(AgskEnstruMatch.created_at)).offset(skip).limit(limit).all()

        analyst_ids = list({m.created_by for m in matches if m.created_by})
        approver_ids = list({m.approved_by for m in matches if m.approved_by})
        agsk_codes  = list({m.agsk_code   for m in matches if m.agsk_code})
        enstru_codes = list({m.enstru_code for m in matches if m.enstru_code})

        analysts_map  = {u.id: u for u in db.query(User).filter(User.id.in_(analyst_ids)).all()}  if analyst_ids  else {}
        approvers_map = {u.id: u for u in db.query(User).filter(User.id.in_(approver_ids)).all()} if approver_ids else {}
        agsk_map      = {a.code: a for a in db.query(Agsk).filter(Agsk.code.in_(agsk_codes)).all()} if agsk_codes else {}
        enstru_map    = {e.code: e for e in db.query(Enstru).filter(Enstru.code.in_(enstru_codes)).all()} if enstru_codes else {}

        result = []
        for m in matches:
            if m.is_active and m.is_approved:
                status = "approved"
            elif m.is_active and not m.is_approved:
                status = "pending"
            else:
                status = "rejected"
            analyst_u  = analysts_map.get(m.created_by)
            approver_u = approvers_map.get(m.approved_by) if m.approved_by else None
            agsk_obj   = agsk_map.get(m.agsk_code)
            enstru_obj = enstru_map.get(m.enstru_code)
            result.append({
                "id": m.id,
                "agsk_code": m.agsk_code,
                "agsk_full_name": agsk_obj.full_name if agsk_obj else None,
                "enstru_code": m.enstru_code,
                "enstru_name_rus": enstru_obj.name_rus  if enstru_obj else None,
                "enstru_detail_rus": enstru_obj.detail_rus if enstru_obj else None,
                "enstru_standard": enstru_obj.standard  if enstru_obj else None,
                "created_by": m.created_by,
                "analyst_name": analyst_u.full_name if analyst_u else "—",
                "created_at": m.created_at.isoformat() if m.created_at else None,
                "is_approved": m.is_approved,
                "is_active": m.is_active,
                "approved_by": m.approved_by,
                "approved_by_name": approver_u.full_name if approver_u else None,
                "approved_at": m.approved_at.isoformat() if m.approved_at else None,
                "status": status,
            })
        return {"items": result, "total": total}
