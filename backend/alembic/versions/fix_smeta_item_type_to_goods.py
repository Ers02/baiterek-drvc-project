"""fix existing smeta-imported items with NULL item_type → 'GOODS'

Revision ID: fix_smeta_item_type
Revises: fix_pending_sel_to_active
Create Date: 2026-06-02

Задача: парсер сметы (parse_smeta_file) не устанавливал item_type явно,
полагаясь на server_default='GOODS'. В некоторых случаях значение могло
остаться NULL, из-за чего фронт не показывал кнопку «Выбрать поставщика»
для позиций сметы со статусом «Подсказка».
"""
from typing import Union, Sequence
from alembic import op


revision: str = 'fix_smeta_item_type'
down_revision: Union[str, Sequence[str], None] = 'fix_pending_sel_to_active'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Всем позициям с NULL/пустым item_type, у которых is_product=true,
    # выставляем 'GOODS' — иначе UI не покажет действие.
    op.execute("""
        UPDATE psd_document_items
        SET item_type = 'GOODS'
        WHERE (item_type IS NULL OR item_type = '')
          AND is_product = true
    """)


def downgrade() -> None:
    # Откат точно невозможен — оставляем no-op
    pass
