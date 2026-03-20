"""add_agent_record_and_heartbeat_order_record

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-03-20 00:00:02.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
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
        sa.Column("fallback_chain", sa.String(), nullable=False, server_default="gemini-flash,claude-haiku"),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("heartbeat_orders", sa.Text(), nullable=True),
        sa.Column("soul_manifest_override", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_agent_record_status", "agent_record", ["status"])

    op.create_table(
        "heartbeat_order_record",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("agent_id", sa.String(), nullable=True),
        sa.Column("fired_at", sa.Float(), nullable=False),
        sa.Column("probe_type", sa.String(), nullable=False, server_default=""),
        sa.Column("action_type", sa.String(), nullable=False, server_default=""),
        sa.Column("outcome", sa.String(), nullable=False, server_default="success"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("signal_stored", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_hb_order_record_order_id", "heartbeat_order_record", ["order_id"])
    op.create_index("ix_hb_order_record_agent_id", "heartbeat_order_record", ["agent_id"])
    op.create_index("ix_hb_order_record_fired_at", "heartbeat_order_record", ["fired_at"])


def downgrade() -> None:
    op.drop_index("ix_hb_order_record_fired_at")
    op.drop_index("ix_hb_order_record_agent_id")
    op.drop_index("ix_hb_order_record_order_id")
    op.drop_table("heartbeat_order_record")
    op.drop_index("ix_agent_record_status")
    op.drop_table("agent_record")
