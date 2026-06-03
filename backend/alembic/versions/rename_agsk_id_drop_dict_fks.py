"""rename agsk_id to agsk_code and drop dictionary FK constraints

Revision ID: rename_agsk_id_drop_dict_fks
Revises: add_cascade_rules_fks
Create Date: 2026-05-18 01:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'rename_agsk_id_drop_dict_fks'
down_revision: Union[str, Sequence[str], None] = 'add_cascade_rules_fks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the FK from agsk (was added in the previous migration as fk_piv_agsk_id)
    op.drop_constraint('fk_piv_agsk_id', 'plan_item_versions', type_='foreignkey')

    # Drop the FK from enstru (was added in the previous migration as fk_piv_trucode)
    op.drop_constraint('fk_piv_trucode', 'plan_item_versions', type_='foreignkey')

    # Rename the column agsk_id -> agsk_code (data stays untouched, just the name changes)
    op.alter_column('plan_item_versions', 'agsk_id', new_column_name='agsk_code')


def downgrade() -> None:
    op.alter_column('plan_item_versions', 'agsk_code', new_column_name='agsk_id')

    op.create_foreign_key(
        'fk_piv_trucode', 'plan_item_versions', 'enstru',
        ['trucode'], ['code'], onupdate='CASCADE'
    )
    op.create_foreign_key(
        'fk_piv_agsk_id', 'plan_item_versions', 'agsk',
        ['agsk_id'], ['code'], onupdate='CASCADE', ondelete='SET NULL'
    )
