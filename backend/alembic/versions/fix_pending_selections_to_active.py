"""fix existing pending supplier selections → active; update item match_type

Revision ID: fix_pending_sel_to_active
Revises: fix_manual_to_suggested
Create Date: 2026-05-28

Задача: старый код add_supplier_selection ставил status='pending' для выборов
поставщиков, когда пара АГСК→ЕНСТРУ не была утверждена в библиотеке.
Это оставляло позиции в match_type='suggested' без видимого результата в UI.

Новое поведение: выборы всегда active, позиция сразу manual.
Миграция исправляет существующие данные.
"""
from typing import Union, Sequence
from alembic import op


revision: str = 'fix_pending_sel_to_active'
down_revision: Union[str, Sequence[str], None] = 'fix_manual_to_suggested'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Все pending-выборы поставщиков переводим в active
    op.execute("""
        UPDATE psd_item_supplier_selections
        SET status = 'active'
        WHERE status = 'pending'
          AND is_active = true
    """)

    # 2. Позиции, у которых теперь есть хотя бы один active-выбор,
    #    но match_type ещё не 'manual' — помечаем как обработанные
    op.execute("""
        UPDATE psd_document_items
        SET match_type   = 'manual',
            match_score  = 100,
            match_reason = 'Выбор аналитика из реестра КТП'
        WHERE match_type != 'manual'
          AND id IN (
              SELECT DISTINCT item_id
              FROM psd_item_supplier_selections
              WHERE status = 'active'
                AND is_active = true
          )
    """)


def downgrade() -> None:
    # Точный откат невозможен (не знаем какие были pending vs active),
    # поэтому downgrade — no-op
    pass
