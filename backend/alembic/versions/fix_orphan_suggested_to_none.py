"""fix existing 'suggested' items whose ENSTRU has no supplier in KTP → 'none'

Revision ID: fix_orphan_suggested
Revises: fix_smeta_item_type
Create Date: 2026-06-02

Парсер сметы раньше ставил match_type='suggested' для всех позиций с ЕНСТРУ-кодом,
даже если этот ЕНСТРУ не присутствовал в реестре КТП у активных поставщиков
с валидным ДВС. На UI получалась «осиротевшая» подсказка — кнопка «найти в реестре
КТП» всё равно ничего не находила.

Эта миграция переводит такие позиции в match_type='none' с пояснением.
Логика проверки совпадает с парсером (psd_parser_service.parse_smeta_file):
поставщик должен быть is_active != FALSE и иметь dvc_percent > 0.
"""
from typing import Union, Sequence
from alembic import op


revision: str = 'fix_orphan_suggested'
down_revision: Union[str, Sequence[str], None] = 'fix_smeta_item_type'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Позиции с match_type='suggested' и enstru_code, для которых в Reestr_KTP
    # нет ни одного активного поставщика с валидным ДВС.
    op.execute("""
        UPDATE psd_document_items
        SET match_type = 'none',
            match_score = NULL,
            match_reason = 'ЕНСТРУ из сметы, но в реестре КТП нет активных поставщиков'
        WHERE match_type = 'suggested'
          AND enstru_code IS NOT NULL
          AND enstru_code <> ''
          AND NOT EXISTS (
              SELECT 1
              FROM reestr_ktp r
              WHERE r.is_active IS NOT FALSE
                AND r.enstru_codes ? psd_document_items.enstru_code
                AND NULLIF(REGEXP_REPLACE(r.dvc_percent, '[^0-9.]', '', 'g'), '')::numeric > 0
          )
    """)


def downgrade() -> None:
    # Точный откат невозможен (мы не знаем какие позиции были изначально 'none',
    # а какие — 'suggested'). Оставляем no-op.
    pass
