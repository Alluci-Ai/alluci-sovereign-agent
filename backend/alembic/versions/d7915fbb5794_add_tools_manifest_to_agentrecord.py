"""Add tools_manifest to AgentRecord

Revision ID: d7915fbb5794
Revises: d177afc5f5dd
Create Date: 2026-07-01 17:12:25.268679

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7915fbb5794'
down_revision: Union[str, None] = 'd177afc5f5dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.add_column(sa.Column('tools_manifest', sa.String(), server_default='[]', nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.drop_column('tools_manifest')
