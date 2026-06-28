"""Add AgentSkillBinding and engine_manifest

Revision ID: d177afc5f5dd
Revises: fff3aebd855d
Create Date: 2026-06-28 16:20:08.664053

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd177afc5f5dd'
down_revision: Union[str, None] = 'fff3aebd855d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add agent_skill_binding table
    op.create_table(
        'agent_skill_binding',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('skill_id', sa.String(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_skill_binding_agent_id'), 'agent_skill_binding', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_skill_binding_skill_id'), 'agent_skill_binding', ['skill_id'], unique=False)
    
    # Add engine_manifest column to agent_record
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.add_column(sa.Column('engine_manifest', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove engine_manifest column
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.drop_column('engine_manifest')
    
    # Drop agent_skill_binding table
    op.drop_index(op.f('ix_agent_skill_binding_skill_id'), table_name='agent_skill_binding')
    op.drop_index(op.f('ix_agent_skill_binding_agent_id'), table_name='agent_skill_binding')
    op.drop_table('agent_skill_binding')
