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

        # Проверяем: есть ли точное совпадение АГСК в Реестре КТП
        is_exact_ktp_match = self.db.query(Reestr_KTP.id).filter(
            Reestr_KTP.agsk3_codes.contains([q])
        ).first() is not None

        # 1. Утверждённая библиотека сопоставлений (проверено менеджером)
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
            m_type = "manual_ktp" if is_exact_ktp_match else "manual"
            return {
                "enstru_code": best_approved.enstru_code,
                "enstru_name": enstru_obj.name_rus if enstru_obj else None,
                "match_type": m_type,
                "score": 100,
                "reason": "Утверждённая библиотека сопоставлений АГСК → ЕНСТРУ",
            }

        # 2. Прямой поиск в Реестре КТП (точный код 1 в 1)
        ktp_exact = self.db.query(Reestr_KTP).filter(
            Reestr_KTP.agsk3_codes.contains([q])
        ).first()

        if ktp_exact and ktp_exact.enstru_codes:
            for code in ktp_exact.enstru_codes:
                if self._check_enstru_exists(code):
                    name = "Из КТП"
                    try:
                        idx = ktp_exact.enstru_codes.index(code)
                        if ktp_exact.enstru_names and len(ktp_exact.enstru_names) > idx:
                            name = ktp_exact.enstru_names[idx]
                    except Exception:
                        pass
                    dvc = ktp_exact.dvc_percent or "0"
                    return {
                        "enstru_code": code,
                        "enstru_name": name,
                        "match_type": "auto_ktp",
                        "score": 95,
                        "reason": f"Реестр КТП (Завод: {ktp_exact.company_name}, ДВС: {dvc}%)",
                    }

        return None
