"""add_topological_fields_to_audit_log

Revision ID: 274e447f4ca5
Revises: a1b2c3d4e5f7
Create Date: 2026-05-29 12:25:57.061704

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlmodel.sql.sqltypes import AutoString


# revision identifiers, used by Alembic.
revision: str = '274e447f4ca5'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.add_column(sa.Column('betti', AutoString(), nullable=True))
        batch_op.add_column(sa.Column('phi_total', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('coherence', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('psi', sa.Float(), nullable=True))
        batch_op.add_column(sa.Column('merkle_attribution_hash', AutoString(), nullable=True))
        batch_op.add_column(sa.Column('pvt_json', AutoString(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('audit_log', schema=None) as batch_op:
        batch_op.drop_column('pvt_json')
        batch_op.drop_column('merkle_attribution_hash')
        batch_op.drop_column('psi')
        batch_op.drop_column('coherence')
        batch_op.drop_column('phi_total')
        batch_op.drop_column('betti')
