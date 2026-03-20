"""add_pcl_opportunity_and_world_snapshot_tables

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-03-20 00:00:01.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pcl_opportunity",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("detector_name", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("recommended_action", sa.String(), nullable=False, server_default="notify"),
        sa.Column("objective", sa.Text(), nullable=False, server_default=""),
        sa.Column("notification_body", sa.Text(), nullable=False, server_default=""),
        sa.Column("autonomy_level", sa.String(), nullable=False, server_default="RESTRICTED"),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("affects_goal_id", sa.Integer(), nullable=True),
        sa.Column("actioned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("actioned_at", sa.Float(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("user_engaged", sa.Boolean(), nullable=True),
        sa.Column("detected_at", sa.Float(), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_pcl_opportunity_detector", "pcl_opportunity", ["detector_name"])
    op.create_index("ix_pcl_opportunity_detected_at", "pcl_opportunity", ["detected_at"])

    op.create_table(
        "pcl_world_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("built_at", sa.Float(), nullable=False),
        sa.Column("active_goals_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("goals_at_risk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_psi", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("current_flow_mode", sa.String(), nullable=False, server_default="STANDARD"),
        sa.Column("pending_bridge_messages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunities_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opportunities_actioned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cycle_duration_ms", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.create_index("ix_pcl_snapshot_cycle", "pcl_world_snapshot", ["cycle_number"])
    op.create_index("ix_pcl_snapshot_built_at", "pcl_world_snapshot", ["built_at"])


def downgrade() -> None:
    op.drop_index("ix_pcl_snapshot_built_at")
    op.drop_index("ix_pcl_snapshot_cycle")
    op.drop_table("pcl_world_snapshot")
    op.drop_index("ix_pcl_opportunity_detected_at")
    op.drop_index("ix_pcl_opportunity_detector")
    op.drop_table("pcl_opportunity")
