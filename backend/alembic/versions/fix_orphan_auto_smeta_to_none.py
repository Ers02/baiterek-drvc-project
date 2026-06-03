"""fix old smeta items with match_type='auto' but no supplier in KTP → 'none'

Revision ID: fix_orphan_auto_smeta
Revises: fix_orphan_suggested
Create Date: 2026-06-02

Самый первый парсер сметы ставил match_type='auto' для всех позиций с ЕНСТРУ —
даже если у них не было АГСК-кода и поставщика в реестре КТП. На UI такие
позиции показывались зелёным «✅ Авто» и считались обработанными, но открыв
их аналитик не находил ни одного поставщика для выбора.

Эта миграция переводит такие позиции в match_type='none' с понятным reason.
Правило: match_type='auto' + reason='Из файла сметы' + нет АГСК-кода
+ нет поставщика в КТП с этим ЕНСТРУ → 'none'.
"""
from typing import Union, Sequence
from alembic import op


revision: str = 'fix_orphan_auto_smeta'
down_revision: Union[str, Sequence[str], None] = 'fix_orphan_suggested'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        UPDATE psd_document_items
        SET match_type = 'none',
            match_score = NULL,
            match_reason = 'ЕНСТРУ из сметы, но в реестре КТП нет активных поставщиков'
        WHERE match_type = 'auto'
          AND match_reason = 'Из файла сметы'
          AND code_sn IS NULL
          AND enstru_code IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM reestr_ktp r
              WHERE r.is_active IS NOT FALSE
                AND r.enstru_codes ? psd_document_items.enstru_code
                AND NULLIF(REGEXP_REPLACE(r.dvc_percent, '[^0-9.]', '', 'g'), '')::numeric > 0
          )
    """)


def downgrade() -> None:
    pass
