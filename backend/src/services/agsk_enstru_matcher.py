"""
Сервис для автоматического сопоставления AGSK ↔ REESTR KTP
Реализует каскадную логику: Библиотека КТП -> Реестр КТП
"""
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, cast, String, or_, func, desc, asc, and_
from ..models.models import AgskReestrKtpMatch, Reestr_KTP, Enstru

class AgskEnstruMatcher:
    def __init__(self, db: Session):
        self.db = db

    def _check_enstru_exists(self, code: str) -> bool:
        if not code: return False
        return self.db.query(Enstru.id).filter(Enstru.code == code).first() is not None

    def get_match_for_agsk(self, agsk_code: str) -> Optional[Dict[str, Any]]:
        if not agsk_code: return None
        q = str(agsk_code).strip()

        # Определяем, есть ли точное совпадение АГСК в Реестре КТП
        is_exact_ktp_match = self.db.query(Reestr_KTP.id).filter(
            Reestr_KTP.agsk3_codes.contains([q])
        ).first() is not None

        # 1. Библиотека замен КТП (Ручные привязки)
        best_manual = (
            self.db.query(AgskReestrKtpMatch)
            .filter(
                AgskReestrKtpMatch.agsk_code == q,
                AgskReestrKtpMatch.is_active == True
            )
            .order_by(asc(AgskReestrKtpMatch.dvc_percent))
            .first()
        )
        
        if best_manual:
            # КТП+Библиотека только если он ДО ЭТОГО был КТП (точный AGsk match)
            m_type = "manual_ktp" if (best_manual.ktp_id and is_exact_ktp_match) else "manual"
            return {
                "enstru_code": best_manual.enstru_code,
                "enstru_name": best_manual.enstru_name_ru,
                "match_type": m_type,
                "score": 100,
                "reason": f"Библиотека замен (КТП: {best_manual.product_name_ktp or '—'}, ДВС: {best_manual.dvc_percent}%)"
            }
            
        # 2. Прямой поиск в Реестре КТП (Точный код 1 в 1)
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
                    except: pass
                    
                    dvc = ktp_exact.dvc_percent or "0"
                    return {
                        "enstru_code": code,
                        "enstru_name": name,
                        "match_type": "auto_ktp", # Изменено на auto_ktp
                        "score": 95,
                        "reason": f"Реестр КТП (Завод: {ktp_exact.company_name}, ДВС: {dvc}%)"
                    }

        # Только точное совпадение АГСК кода - сопоставление по родительской группе удалено
        return None
