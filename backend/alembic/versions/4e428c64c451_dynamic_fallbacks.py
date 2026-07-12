"""dynamic_fallbacks

Revision ID: 4e428c64c451
Revises: 55083b74ecb6
Create Date: 2026-07-12 10:54:07.623811

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e428c64c451'
down_revision: Union[str, None] = '55083b74ecb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Scrub existing legacy data
    op.execute("UPDATE agent_record SET fallback_chain = NULL WHERE fallback_chain = 'gemini-flash,claude-haiku'")

    # 2. Alter column to remove default using batch alter
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.alter_column('fallback_chain',
               existing_type=sa.VARCHAR(),
               server_default=None,
               existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('agent_record', schema=None) as batch_op:
        batch_op.alter_column('fallback_chain',
               existing_type=sa.VARCHAR(),
               server_default='gemini-flash,claude-haiku',
               existing_nullable=True)
