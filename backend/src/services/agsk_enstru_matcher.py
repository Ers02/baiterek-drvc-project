"""
Сервис для автоматического сопоставления AGSK → ENSTRU.
Приоритеты: 1. Утверждённая библиотека (agsk_enstru_matches) → 2. Реестр КТП
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from ..models.models import AgskEnstruMatch, Reestr_KTP, Enstru


class AgskEnstruMatcher:
    def __init__(self, db: Session):
        self.db = db

    def _check_enstru_exists(self, code: str) -> bool:
        if not code:
            return False
        return self.db.query(Enstru.id).filter(Enstru.code == code).first() is not None

    def get_match_for_agsk(self, agsk_code: str) -> Optional[Dict[str, Any]]:
        if not agsk_code:
            return None
        q = str(agsk_code).strip()

        # ── ПРИОРИТЕТ 1: точное совпадение кода АГСК в jsonb agsk3_codes Реестра КТП ──
        # Код АГСК из ПСД 1-в-1 присутствует в активной записи реестра → это
        # АВТО-сопоставление (100% совпадение кода). Наличие ЕНСТРУ в справочнике
        # НЕ требуется — код АГСК уже доказывает совпадение.
        ktp_exact = self.db.query(Reestr_KTP).filter(
            Reestr_KTP.is_active.isnot(False),
            Reestr_KTP.agsk3_codes.contains([q])
        ).order_by(Reestr_KTP.id).first()

        if ktp_exact:
            enstru_code = ktp_exact.enstru_codes[0] if ktp_exact.enstru_codes else None
            enstru_name = None
            if enstru_code:
                if ktp_exact.enstru_names:
                    enstru_name = ktp_exact.enstru_names[0]
                enstru_obj = self.db.query(Enstru).filter(Enstru.code == enstru_code).first()
                if enstru_obj and enstru_obj.name_rus:
                    enstru_name = enstru_obj.name_rus
            dvc = ktp_exact.dvc_percent or "0"
            return {
                "enstru_code": enstru_code,
                "enstru_name": enstru_name,
                "match_type": "auto_ktp",
                "score": 100,
                "reason": f"Точное совпадение кода АГСК в реестре КТП (Завод: {ktp_exact.company_name}, ДВС: {dvc}%)",
            }

        # ── ПРИОРИТЕТ 2: утверждённая библиотека (АГСК → ЕНСТРУ, проверено менеджером) ──
        # Прямого совпадения АГСК в КТП нет → это лишь подсказка для аналитика.
        best_approved = (
            self.db.query(AgskEnstruMatch)
            .filter(
                AgskEnstruMatch.agsk_code == q,
                AgskEnstruMatch.is_approved == True,
                AgskEnstruMatch.is_active == True,
            )
            .order_by(desc(AgskEnstruMatch.approved_at))
            .first()
        )

        if best_approved:
            enstru_obj = self.db.query(Enstru).filter(Enstru.code == best_approved.enstru_code).first()
            return {
                "enstru_code": best_approved.enstru_code,
                "enstru_name": enstru_obj.name_rus if enstru_obj else None,
                "match_type": "library",
                "score": 90,
                "reason": "Утверждённая библиотека сопоставлений АГСК → ЕНСТРУ",
            }

        return None
