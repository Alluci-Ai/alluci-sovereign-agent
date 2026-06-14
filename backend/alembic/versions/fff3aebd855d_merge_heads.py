"""merge heads

Revision ID: fff3aebd855d
Revises: 20240609_add_queued_task, 274e447f4ca5, 8d0c8354fde3
Create Date: 2026-06-13 10:28:05.943513

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fff3aebd855d'
down_revision: Union[str, None] = ('20240609_add_queued_task', '274e447f4ca5', '8d0c8354fde3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
