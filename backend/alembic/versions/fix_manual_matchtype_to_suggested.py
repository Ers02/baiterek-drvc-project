"""fix match_type manual→suggested for items without active supplier selection

Revision ID: fix_manual_to_suggested
Revises: refactor_agsk_matches_add_supplier_selections
Create Date: 2026-05-28

Задача: старый код _run_auto_matching_for_document ставил match_type='manual'
для позиций, которые нашлись в утверждённой библиотеке АГСК→ЕНСТРУ.
Это делало их «обработанными» в UI без реального выбора поставщика.
Исправляем: переводим такие позиции в match_type='suggested'
(есть подсказка, но поставщик не выбран).
"""
from typing import Union, Sequence
from alembic import op


revision: str = 'fix_manual_to_suggested'
down_revision: Union[str, Sequence[str], None] = 'refactor_agsk_supplier_sel'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Переводим в 'suggested' все позиции, у которых:
    # - match_type = 'manual'  (поставлено авто-матчингом из библиотеки)
    # - нет ни одной активной записи в psd_item_supplier_selections
    op.execute("""
        UPDATE psd_document_items
        SET match_type   = 'suggested',
            match_reason = 'Подсказка из утверждённой библиотеки — выберите поставщика из реестра КТП'
        WHERE match_type = 'manual'
          AND id NOT IN (
              SELECT DISTINCT item_id
              FROM psd_item_supplier_selections
              WHERE status = 'active'
                AND is_active = true
          )
    """)


def downgrade() -> None:
    # Обратное преобразование: 'suggested' → 'manual' для позиций с enstru_code
    # (точное восстановление невозможно, поэтому откатываем только что можем)
    op.execute("""
        UPDATE psd_document_items
        SET match_type   = 'manual',
            match_reason = 'Автоматически из утверждённой библиотеки сопоставлений'
        WHERE match_type = 'suggested'
          AND enstru_code IS NOT NULL
          AND id NOT IN (
              SELECT DISTINCT item_id
              FROM psd_item_supplier_selections
              WHERE status = 'active'
                AND is_active = true
          )
    """)
