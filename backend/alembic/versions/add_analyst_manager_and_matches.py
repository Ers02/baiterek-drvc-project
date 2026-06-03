"""add analyst_manager role and agsk_enstru_matches table

Revision ID: add_analyst_manager_matches
Revises: rename_agsk_id_drop_dict_fks
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_analyst_manager_matches'
down_revision: Union[str, Sequence[str], None] = 'rename_agsk_id_drop_dict_fks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Добавляем новое значение в enum UserRole
    op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'ANALYST_MANAGER'")

    # 2. Создаём таблицу agsk_enstru_matches (IF NOT EXISTS — на случай если уже существует)
    op.execute("""
        CREATE TABLE IF NOT EXISTS agsk_enstru_matches (
            id          SERIAL PRIMARY KEY,
            agsk_code   VARCHAR(50)  NOT NULL,
            enstru_code VARCHAR(35)  NOT NULL,
            doc_id      INTEGER      REFERENCES external_documents(id) ON DELETE CASCADE,
            item_id     INTEGER      REFERENCES psd_document_items(id) ON DELETE CASCADE,
            matched_by  INTEGER      NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            matched_at  TIMESTAMPTZ  DEFAULT now(),
            is_approved BOOLEAN      NOT NULL DEFAULT false,
            approved_by INTEGER      REFERENCES users(id) ON DELETE SET NULL,
            approved_at TIMESTAMPTZ,
            is_active   BOOLEAN      NOT NULL DEFAULT true
        )
    """)

    # 3. Индексы — CREATE INDEX IF NOT EXISTS чтобы не упасть если уже есть
    op.execute("CREATE INDEX IF NOT EXISTS idx_aem_agsk_code  ON agsk_enstru_matches (agsk_code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aem_item_id    ON agsk_enstru_matches (item_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aem_doc_id     ON agsk_enstru_matches (doc_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aem_matched_by ON agsk_enstru_matches (matched_by)")


def downgrade() -> None:
    op.drop_index('idx_aem_matched_by', table_name='agsk_enstru_matches')
    op.drop_index('idx_aem_doc_id', table_name='agsk_enstru_matches')
    op.drop_index('idx_aem_item_id', table_name='agsk_enstru_matches')
    op.drop_index('idx_aem_agsk_code', table_name='agsk_enstru_matches')
    op.drop_table('agsk_enstru_matches')
    # Примечание: значение 'analyst_manager' из enum удалить нельзя в PostgreSQL без пересоздания
