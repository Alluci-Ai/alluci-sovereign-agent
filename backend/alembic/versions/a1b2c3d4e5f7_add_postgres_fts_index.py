"""add postgres fts index

Revision ID: a1b2c3d4e5f7
Revises: 8f15288273f9
Create Date: 2026-05-03 23:34:00.000000

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a1b2c3d4e5f7' # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = '8f15288273f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Create a GIN index on the content column for high-performance PostgreSQL FTS
    # We use a raw SQL execution because Alembic/SQLAlchemy standard index creation 
    # doesn't natively support to_tsvector expressions without complex dialect-specific logic.
    
    # Get the bind to check dialect
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute(
            "CREATE INDEX IF NOT EXISTS hlsm_episodic_content_fts_idx ON hlsm_episodic "
            "USING GIN (to_tsvector('english', content))"
        )
    elif connection.dialect.name == "sqlite":
        # SQLite FTS is handled via virtual tables in raw_sql migrations
        pass

def downgrade() -> None:
    connection = op.get_bind()
    if connection.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS hlsm_episodic_content_fts_idx")
