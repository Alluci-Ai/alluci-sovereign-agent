"""add_agent_record

Revision ID: b1c2d3e4f5a6
Revises: a1b2c3d4e5f6
Create Date: 2026-03-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_record",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("model", sa.String(), nullable=False, server_default="gpt-4o"),
        sa.Column(
            "fallback_chain",
            sa.String(),
            nullable=False,
            server_default="gemini-flash,claude-haiku",
        ),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("heartbeat_orders", sa.Text(), nullable=True),
        sa.Column("soul_manifest_override", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_record_status", "agent_record", ["status"])


def downgrade() -> None:
    op.drop_index("ix_agent_record_status", table_name="agent_record")
    op.drop_table("agent_record")
