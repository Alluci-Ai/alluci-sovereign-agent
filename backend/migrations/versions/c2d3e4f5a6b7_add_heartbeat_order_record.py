"""add_heartbeat_order_record

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-03-22 00:01:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a6b7"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column(
            "signal_stored", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.create_index(
        "ix_hb_order_order_id", "heartbeat_order_record", ["order_id"]
    )
    op.create_index(
        "ix_hb_order_agent_id", "heartbeat_order_record", ["agent_id"]
    )
    op.create_index(
        "ix_hb_order_fired_at", "heartbeat_order_record", ["fired_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_hb_order_fired_at", table_name="heartbeat_order_record")
    op.drop_index("ix_hb_order_agent_id", table_name="heartbeat_order_record")
    op.drop_index("ix_hb_order_order_id", table_name="heartbeat_order_record")
    op.drop_table("heartbeat_order_record")
