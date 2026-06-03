"""Refactor agsk_enstru_matches + add psd_item_supplier_selections

Revision ID: refactor_agsk_supplier_sel
Revises: migrate_agsk_matches_consolidate
Create Date: 2026-05-28 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'refactor_agsk_supplier_sel'
down_revision: Union[str, Sequence[str], None] = 'migrate_agsk_matches_consolidate'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Удаляем индексы по удаляемым/переименовываемым столбцам ──────────
    op.execute("DROP INDEX IF EXISTS idx_aem_doc_id")
    op.execute("DROP INDEX IF EXISTS idx_aem_item_id")
    op.execute("DROP INDEX IF EXISTS idx_aem_matched_by")

    # ── 2. Удаляем столбцы doc_id и item_id (CASCADE снимет FK-констрейнты) ─
    op.execute("ALTER TABLE agsk_enstru_matches DROP COLUMN IF EXISTS doc_id CASCADE")
    op.execute("ALTER TABLE agsk_enstru_matches DROP COLUMN IF EXISTS item_id CASCADE")

    # ── 3. Переименовываем matched_by → created_by, matched_at → created_at ─
    op.execute("ALTER TABLE agsk_enstru_matches RENAME COLUMN matched_by TO created_by")
    op.execute("ALTER TABLE agsk_enstru_matches RENAME COLUMN matched_at TO created_at")

    # ── 4. Дедупликация: оставляем одну запись на пару (agsk_code, enstru_code)
    #       Приоритет: утверждённые → активные → последние по id
    op.execute("""
        DELETE FROM agsk_enstru_matches
        WHERE id NOT IN (
            SELECT DISTINCT ON (agsk_code, enstru_code) id
            FROM agsk_enstru_matches
            ORDER BY agsk_code, enstru_code,
                     is_approved DESC,
                     is_active DESC,
                     id DESC
        )
    """)

    # ── 5. Добавляем UNIQUE-констрейнт (agsk_code, enstru_code) ─────────────
    op.execute("""
        ALTER TABLE agsk_enstru_matches
        ADD CONSTRAINT uq_agsk_enstru UNIQUE (agsk_code, enstru_code)
    """)

    # ── 6. Пересоздаём индекс на created_by ──────────────────────────────────
    op.execute("CREATE INDEX IF NOT EXISTS idx_aem_created_by ON agsk_enstru_matches (created_by)")

    # ── 7. Создаём таблицу выбора поставщиков по позиции ─────────────────────
    op.execute("""
        CREATE TABLE IF NOT EXISTS psd_item_supplier_selections (
            id              SERIAL PRIMARY KEY,
            item_id         INTEGER      NOT NULL REFERENCES psd_document_items(id) ON DELETE CASCADE,
            agsk_code       VARCHAR(50)  NOT NULL,
            enstru_code     VARCHAR(35),
            ktp_id          INTEGER      REFERENCES reestr_ktp(id) ON DELETE SET NULL,
            product_code    TEXT,
            supplier_bin    VARCHAR(12),
            supplier_name   TEXT,
            supplier_product TEXT,
            dvc_percent     NUMERIC(5,2),
            selected_by     INTEGER      NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            selected_at     TIMESTAMPTZ  DEFAULT now(),
            library_match_id INTEGER     REFERENCES agsk_enstru_matches(id) ON DELETE SET NULL,
            status          VARCHAR(20)  NOT NULL DEFAULT 'active',
            is_active       BOOLEAN      NOT NULL DEFAULT true,
            notes           TEXT
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_piss_item_id       ON psd_item_supplier_selections (item_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_piss_agsk_code     ON psd_item_supplier_selections (agsk_code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_piss_library_match ON psd_item_supplier_selections (library_match_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_piss_selected_by   ON psd_item_supplier_selections (selected_by)")


def downgrade() -> None:
    # Удаляем таблицу выбора поставщиков
    op.execute("DROP TABLE IF EXISTS psd_item_supplier_selections CASCADE")

    # Удаляем UNIQUE-констрейнт
    op.execute("ALTER TABLE agsk_enstru_matches DROP CONSTRAINT IF EXISTS uq_agsk_enstru")

    # Удаляем новый индекс
    op.execute("DROP INDEX IF EXISTS idx_aem_created_by")

    # Переименовываем обратно
    op.execute("ALTER TABLE agsk_enstru_matches RENAME COLUMN created_by TO matched_by")
    op.execute("ALTER TABLE agsk_enstru_matches RENAME COLUMN created_at TO matched_at")

    # Восстанавливаем столбцы (без данных — только структуру)
    op.execute("""
        ALTER TABLE agsk_enstru_matches
        ADD COLUMN IF NOT EXISTS doc_id  INTEGER REFERENCES external_documents(id) ON DELETE CASCADE,
        ADD COLUMN IF NOT EXISTS item_id INTEGER REFERENCES psd_document_items(id) ON DELETE CASCADE
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_aem_doc_id     ON agsk_enstru_matches (doc_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aem_item_id    ON agsk_enstru_matches (item_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_aem_matched_by ON agsk_enstru_matches (matched_by)")
