"""add_hlsm_episodic_and_working_tables

Revision ID: f1a2b3c4d5e6
Revises: ed12bc369d08
Create Date: 2026-03-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "ed12bc369d08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── L1 Episodic Memory Table ─────────────────────────────────────────────
    op.create_table(
        "hlsm_episodic",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="task_result"),
        sa.Column("session_key", sa.String(), nullable=False, server_default=""),
        sa.Column("objective_hash", sa.String(), nullable=False, server_default=""),
        sa.Column("psi_at_encoding", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("valence_at_encoding", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("topological_importance", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("betti_1_support", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_accessed", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("retention_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("promoted_to_l2", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extra_metadata", sa.Text(), nullable=True),
    )
    op.create_index("ix_hlsm_episodic_session_key", "hlsm_episodic", ["session_key"])
    op.create_index("ix_hlsm_episodic_source", "hlsm_episodic", ["source"])
    op.create_index("ix_hlsm_episodic_objective_hash", "hlsm_episodic", ["objective_hash"])
    op.create_index("ix_hlsm_episodic_last_accessed", "hlsm_episodic", ["last_accessed"])

    # ── L0 Working Memory Fallback Table (for LITE_MODE / Redis-unavailable) ─
    op.create_table(
        "hlsm_working",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("session_key", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="conversation"),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
    )
    op.create_index("ix_hlsm_working_session_key", "hlsm_working", ["session_key"])
    op.create_index("ix_hlsm_working_expires_at", "hlsm_working", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_hlsm_working_expires_at")
    op.drop_index("ix_hlsm_working_session_key")
    op.drop_table("hlsm_working")

    op.drop_index("ix_hlsm_episodic_last_accessed")
    op.drop_index("ix_hlsm_episodic_objective_hash")
    op.drop_index("ix_hlsm_episodic_source")
    op.drop_index("ix_hlsm_episodic_session_key")
    op.drop_table("hlsm_episodic")
