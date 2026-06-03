"""Migrate agsk_reestr_ktp_matches -> agsk_enstru_matches and drop old table

Revision ID: migrate_agsk_matches_consolidate
Revises: add_analyst_manager_matches
Create Date: 2026-05-25 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'migrate_agsk_matches_consolidate'
down_revision: Union[str, Sequence[str], None] = 'add_analyst_manager_matches'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Переносим уникальные пары (agsk_code, enstru_code) из старой таблицы в новую.
    # Помечаем как уже утверждённые (is_approved=TRUE, is_active=TRUE),
    # так как они ранее уже использовались аналитиками без дополнительной проверки.
    op.execute("""
        INSERT INTO agsk_enstru_matches
            (agsk_code, enstru_code, doc_id, item_id,
             matched_by, matched_at,
             is_approved, approved_by, approved_at,
             is_active)
        SELECT DISTINCT ON (agsk_code, enstru_code)
            agsk_code,
            enstru_code,
            NULL::integer  AS doc_id,
            NULL::integer  AS item_id,
            created_by     AS matched_by,
            COALESCE(created_at, NOW()) AS matched_at,
            TRUE           AS is_approved,
            NULL::integer  AS approved_by,
            COALESCE(created_at, NOW()) AS approved_at,
            TRUE           AS is_active
        FROM agsk_reestr_ktp_matches
        WHERE is_active = TRUE
        ORDER BY agsk_code, enstru_code, id ASC
    """)

    # Удаляем старую таблицу (со всеми FK и индексами)
    op.drop_table('agsk_reestr_ktp_matches')


def downgrade() -> None:
    # Восстанавливаем структуру старой таблицы (данные будут потеряны)
    op.create_table(
        'agsk_reestr_ktp_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agsk_code', sa.String(50), nullable=False),
        sa.Column('enstru_code', sa.String(35), nullable=False),
        sa.Column('ktp_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(20), nullable=True),
        sa.Column('agsk_name_ru', sa.Text(), nullable=True),
        sa.Column('enstru_name_ru', sa.Text(), nullable=True),
        sa.Column('product_name_ktp', sa.Text(), nullable=True),
        sa.Column('dvc_percent', sa.Numeric(5, 2), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('psd_document_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('true')),
        sa.ForeignKeyConstraint(['ktp_id'], ['reestr_ktp.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['psd_document_id'], ['external_documents.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agsk_code', 'enstru_code', 'ktp_id', name='uq_agsk_reestr_ktp_manual_v2'),
    )
    op.create_index('ix_agsk_reestr_ktp_matches_agsk_code', 'agsk_reestr_ktp_matches', ['agsk_code'])
    op.create_index('ix_agsk_reestr_ktp_matches_enstru_code', 'agsk_reestr_ktp_matches', ['enstru_code'])
