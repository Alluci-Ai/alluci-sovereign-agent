"""add_soul_profiles

Revision ID: 55083b74ecb6
Revises: d7915fbb5795
Create Date: 2026-07-06 16:23:00.895058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55083b74ecb6'
down_revision: Union[str, None] = 'd7915fbb5795'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create soul_profile_record table
    op.create_table(
        'soul_profile_record',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('manifest', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_soul_profile_record_name'), 'soul_profile_record', ['name'], unique=False)

    # Add soul_profile_id to agent_record using batch_alter_table
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.add_column(sa.Column('soul_profile_id', sa.String(), nullable=True))
        batch_op.create_foreign_key(
            'fk_agent_record_soul_profile_id',
            'soul_profile_record',
            ['soul_profile_id'],
            ['id']
        )

def downgrade() -> None:
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.drop_constraint('fk_agent_record_soul_profile_id', type_='foreignkey')
        batch_op.drop_column('soul_profile_id')

    op.drop_index(op.f('ix_soul_profile_record_name'), table_name='soul_profile_record')
    op.drop_table('soul_profile_record')
