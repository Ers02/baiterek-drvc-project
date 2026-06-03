"""add cascade rules to all foreign keys

Revision ID: add_cascade_rules_fks
Revises: 9d1391e81a34
Create Date: 2026-05-18 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_cascade_rules_fks'
down_revision: Union[str, Sequence[str], None] = '9d1391e81a34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_fk(table: str, column: str) -> None:
    """Drop a FK constraint on table.column regardless of its auto-generated name."""
    op.execute(f"""
        DO $$
        DECLARE v_name TEXT;
        BEGIN
            SELECT tc.constraint_name INTO v_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'public'
              AND tc.table_name   = '{table}'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND kcu.column_name = '{column}'
            LIMIT 1;
            IF v_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE {table} DROP CONSTRAINT %I', v_name);
            END IF;
        END $$;
    """)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # plan_item_versions
    # ------------------------------------------------------------------

    # agsk_id -> agsk.code  (ON UPDATE CASCADE, ON DELETE SET NULL)
    _drop_fk('plan_item_versions', 'agsk_id')
    op.create_foreign_key(
        'fk_piv_agsk_id', 'plan_item_versions', 'agsk',
        ['agsk_id'], ['code'], onupdate='CASCADE', ondelete='SET NULL'
    )

    # trucode -> enstru.code  (ON UPDATE CASCADE)
    _drop_fk('plan_item_versions', 'trucode')
    op.create_foreign_key(
        'fk_piv_trucode', 'plan_item_versions', 'enstru',
        ['trucode'], ['code'], onupdate='CASCADE'
    )

    # unit_id -> mkei.id  (ON DELETE SET NULL)
    _drop_fk('plan_item_versions', 'unit_id')
    op.create_foreign_key(
        'fk_piv_unit_id', 'plan_item_versions', 'mkei',
        ['unit_id'], ['id'], ondelete='SET NULL'
    )

    # expense_item_id -> cost_items.id  (ON DELETE RESTRICT)
    _drop_fk('plan_item_versions', 'expense_item_id')
    op.create_foreign_key(
        'fk_piv_expense_item_id', 'plan_item_versions', 'cost_items',
        ['expense_item_id'], ['id'], ondelete='RESTRICT'
    )

    # funding_source_id -> source_funding.id  (ON DELETE RESTRICT)
    _drop_fk('plan_item_versions', 'funding_source_id')
    op.create_foreign_key(
        'fk_piv_funding_source_id', 'plan_item_versions', 'source_funding',
        ['funding_source_id'], ['id'], ondelete='RESTRICT'
    )

    # kato_purchase_id -> kato.id  (ON DELETE SET NULL)
    _drop_fk('plan_item_versions', 'kato_purchase_id')
    op.create_foreign_key(
        'fk_piv_kato_purchase_id', 'plan_item_versions', 'kato',
        ['kato_purchase_id'], ['id'], ondelete='SET NULL'
    )

    # kato_delivery_id -> kato.id  (ON DELETE SET NULL)
    _drop_fk('plan_item_versions', 'kato_delivery_id')
    op.create_foreign_key(
        'fk_piv_kato_delivery_id', 'plan_item_versions', 'kato',
        ['kato_delivery_id'], ['id'], ondelete='SET NULL'
    )

    # root_item_id -> plan_item_versions.id  (ON DELETE SET NULL)
    _drop_fk('plan_item_versions', 'root_item_id')
    op.create_foreign_key(
        'fk_piv_root_item_id', 'plan_item_versions', 'plan_item_versions',
        ['root_item_id'], ['id'], ondelete='SET NULL'
    )

    # source_version_id -> procurement_plan_versions.id  (ON DELETE SET NULL)
    _drop_fk('plan_item_versions', 'source_version_id')
    op.create_foreign_key(
        'fk_piv_source_version_id', 'plan_item_versions', 'procurement_plan_versions',
        ['source_version_id'], ['id'], ondelete='SET NULL'
    )

    # ------------------------------------------------------------------
    # procurement_plans
    # ------------------------------------------------------------------

    # created_by -> users.id  (ON DELETE RESTRICT)
    _drop_fk('procurement_plans', 'created_by')
    op.create_foreign_key(
        'fk_pp_created_by', 'procurement_plans', 'users',
        ['created_by'], ['id'], ondelete='RESTRICT'
    )

    # ------------------------------------------------------------------
    # procurement_plan_versions
    # ------------------------------------------------------------------

    # created_by -> users.id  (ON DELETE SET NULL)
    _drop_fk('procurement_plan_versions', 'created_by')
    op.create_foreign_key(
        'fk_ppv_created_by', 'procurement_plan_versions', 'users',
        ['created_by'], ['id'], ondelete='SET NULL'
    )

    # ------------------------------------------------------------------
    # external_documents
    # ------------------------------------------------------------------

    # assigned_to -> users.id  (ON DELETE SET NULL)
    _drop_fk('external_documents', 'assigned_to')
    op.create_foreign_key(
        'fk_ed_assigned_to', 'external_documents', 'users',
        ['assigned_to'], ['id'], ondelete='SET NULL'
    )

    # ------------------------------------------------------------------
    # agsk_reestr_ktp_matches
    # ------------------------------------------------------------------

    # ktp_id -> reestr_ktp.id  (ON DELETE CASCADE)
    _drop_fk('agsk_reestr_ktp_matches', 'ktp_id')
    op.create_foreign_key(
        'fk_arkm_ktp_id', 'agsk_reestr_ktp_matches', 'reestr_ktp',
        ['ktp_id'], ['id'], ondelete='CASCADE'
    )

    # created_by -> users.id  (ON DELETE RESTRICT)
    _drop_fk('agsk_reestr_ktp_matches', 'created_by')
    op.create_foreign_key(
        'fk_arkm_created_by', 'agsk_reestr_ktp_matches', 'users',
        ['created_by'], ['id'], ondelete='RESTRICT'
    )

    # psd_document_id -> external_documents.id  (ON DELETE SET NULL)
    _drop_fk('agsk_reestr_ktp_matches', 'psd_document_id')
    op.create_foreign_key(
        'fk_arkm_psd_document_id', 'agsk_reestr_ktp_matches', 'external_documents',
        ['psd_document_id'], ['id'], ondelete='SET NULL'
    )

    # ------------------------------------------------------------------
    # psd_analysis_sessions
    # ------------------------------------------------------------------

    # document_id -> external_documents.id  (ON DELETE CASCADE)
    _drop_fk('psd_analysis_sessions', 'document_id')
    op.create_foreign_key(
        'fk_pas_document_id', 'psd_analysis_sessions', 'external_documents',
        ['document_id'], ['id'], ondelete='CASCADE'
    )

    # analyst_id -> users.id  (ON DELETE RESTRICT)
    _drop_fk('psd_analysis_sessions', 'analyst_id')
    op.create_foreign_key(
        'fk_pas_analyst_id', 'psd_analysis_sessions', 'users',
        ['analyst_id'], ['id'], ondelete='RESTRICT'
    )

    # ------------------------------------------------------------------
    # admin_tasks
    # ------------------------------------------------------------------

    # assigned_to -> users.id  (ON DELETE SET NULL)
    _drop_fk('admin_tasks', 'assigned_to')
    op.create_foreign_key(
        'fk_at_assigned_to', 'admin_tasks', 'users',
        ['assigned_to'], ['id'], ondelete='SET NULL'
    )

    # ------------------------------------------------------------------
    # users (self-ref)
    # ------------------------------------------------------------------

    # delegated_to_id -> users.id  (ON DELETE SET NULL)
    _drop_fk('users', 'delegated_to_id')
    op.create_foreign_key(
        'fk_users_delegated_to_id', 'users', 'users',
        ['delegated_to_id'], ['id'], ondelete='SET NULL'
    )

    # ------------------------------------------------------------------
    # product_groups
    # ------------------------------------------------------------------

    # created_by -> users.id  (ON DELETE SET NULL)
    _drop_fk('product_groups', 'created_by')
    op.create_foreign_key(
        'fk_pg_created_by', 'product_groups', 'users',
        ['created_by'], ['id'], ondelete='SET NULL'
    )

    # ------------------------------------------------------------------
    # product_group_sets
    # ------------------------------------------------------------------

    # created_by -> users.id  (ON DELETE SET NULL)
    _drop_fk('product_group_sets', 'created_by')
    op.create_foreign_key(
        'fk_pgs_created_by', 'product_group_sets', 'users',
        ['created_by'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove named constraints and restore originals without cascade rules

    op.drop_constraint('fk_pgs_created_by', 'product_group_sets', type_='foreignkey')
    op.create_foreign_key(None, 'product_group_sets', 'users', ['created_by'], ['id'])

    op.drop_constraint('fk_pg_created_by', 'product_groups', type_='foreignkey')
    op.create_foreign_key(None, 'product_groups', 'users', ['created_by'], ['id'])

    op.drop_constraint('fk_users_delegated_to_id', 'users', type_='foreignkey')
    op.create_foreign_key(None, 'users', 'users', ['delegated_to_id'], ['id'])

    op.drop_constraint('fk_at_assigned_to', 'admin_tasks', type_='foreignkey')
    op.create_foreign_key(None, 'admin_tasks', 'users', ['assigned_to'], ['id'])

    op.drop_constraint('fk_pas_analyst_id', 'psd_analysis_sessions', type_='foreignkey')
    op.create_foreign_key(None, 'psd_analysis_sessions', 'users', ['analyst_id'], ['id'])

    op.drop_constraint('fk_pas_document_id', 'psd_analysis_sessions', type_='foreignkey')
    op.create_foreign_key(None, 'psd_analysis_sessions', 'external_documents', ['document_id'], ['id'])

    op.drop_constraint('fk_arkm_psd_document_id', 'agsk_reestr_ktp_matches', type_='foreignkey')
    op.create_foreign_key(None, 'agsk_reestr_ktp_matches', 'external_documents', ['psd_document_id'], ['id'])

    op.drop_constraint('fk_arkm_created_by', 'agsk_reestr_ktp_matches', type_='foreignkey')
    op.create_foreign_key(None, 'agsk_reestr_ktp_matches', 'users', ['created_by'], ['id'])

    op.drop_constraint('fk_arkm_ktp_id', 'agsk_reestr_ktp_matches', type_='foreignkey')
    op.create_foreign_key(None, 'agsk_reestr_ktp_matches', 'reestr_ktp', ['ktp_id'], ['id'])

    op.drop_constraint('fk_ed_assigned_to', 'external_documents', type_='foreignkey')
    op.create_foreign_key(None, 'external_documents', 'users', ['assigned_to'], ['id'])

    op.drop_constraint('fk_ppv_created_by', 'procurement_plan_versions', type_='foreignkey')
    op.create_foreign_key(None, 'procurement_plan_versions', 'users', ['created_by'], ['id'])

    op.drop_constraint('fk_pp_created_by', 'procurement_plans', type_='foreignkey')
    op.create_foreign_key(None, 'procurement_plans', 'users', ['created_by'], ['id'])

    op.drop_constraint('fk_piv_source_version_id', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'procurement_plan_versions', ['source_version_id'], ['id'])

    op.drop_constraint('fk_piv_root_item_id', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'plan_item_versions', ['root_item_id'], ['id'])

    op.drop_constraint('fk_piv_kato_delivery_id', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'kato', ['kato_delivery_id'], ['id'])

    op.drop_constraint('fk_piv_kato_purchase_id', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'kato', ['kato_purchase_id'], ['id'])

    op.drop_constraint('fk_piv_funding_source_id', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'source_funding', ['funding_source_id'], ['id'])

    op.drop_constraint('fk_piv_expense_item_id', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'cost_items', ['expense_item_id'], ['id'])

    op.drop_constraint('fk_piv_unit_id', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'mkei', ['unit_id'], ['id'])

    op.drop_constraint('fk_piv_trucode', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'enstru', ['trucode'], ['code'])

    op.drop_constraint('fk_piv_agsk_id', 'plan_item_versions', type_='foreignkey')
    op.create_foreign_key(None, 'plan_item_versions', 'agsk', ['agsk_id'], ['code'])