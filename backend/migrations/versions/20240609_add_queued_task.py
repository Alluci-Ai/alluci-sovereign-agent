"""add queued_task table"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20240609_add_queued_task"
down_revision = "d5383825d624_add_sprint_1_6_tables"  # last migration in list
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "queued_task",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "status",
            sa.Enum(
                "queued",
                "running",
                "completed",
                "failed",
                "pending",
                "skipped",
                "suspended_security",
                name="taskstatus",
            ),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("payload", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("checkpoint", sa.JSON, nullable=True),
        sa.Column("result", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )

def downgrade():
    op.drop_table("queued_task")
    # Drop the enum type if no other table uses it
    op.execute('DROP TYPE IF EXISTS taskstatus')
