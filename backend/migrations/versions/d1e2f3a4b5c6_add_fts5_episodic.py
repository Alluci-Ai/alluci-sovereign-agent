"""add_fts5_episodic_search

Creates the hlsm_episodic_fts FTS5 virtual table and three sync triggers
(INSERT / DELETE / UPDATE) that keep it in sync with hlsm_episodic.

NOTE: FTS5 virtual tables use SQLite-specific syntax. When the database
is PostgreSQL, this migration is a no-op — HLSM falls back to ILIKE search
automatically (see hlsm_manager.l1_search).

Revision ID: d1e2f3a4b5c6
Revises: c2d3e4f5a6b7
Create Date: 2026-03-22 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "d1e2f3a4b5c6"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None

# ── Detect dialect ────────────────────────────────────────────────────────────

def _is_sqlite() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "sqlite"


# ── Upgrade ───────────────────────────────────────────────────────────────────

def upgrade() -> None:
    if not _is_sqlite():
        # PostgreSQL uses ILIKE fallback in hlsm_manager.l1_search();
        # no FTS5 table needed.
        return

    # 1. FTS5 virtual table — unicode61 tokeniser strips diacritics for
    #    accent-insensitive search across languages.
    op.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS hlsm_episodic_fts
        USING fts5(
            id UNINDEXED,
            content,
            tokenize='unicode61 remove_diacritics 1'
        )
        """
    )

    # 2. Backfill from existing rows (idempotent: INSERT OR IGNORE).
    op.execute(
        """
        INSERT OR IGNORE INTO hlsm_episodic_fts(id, content)
        SELECT id, content FROM hlsm_episodic
        """
    )

    # 3. Keep the FTS index in sync automatically via triggers.
    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS hlsm_episodic_after_insert
        AFTER INSERT ON hlsm_episodic
        BEGIN
            INSERT INTO hlsm_episodic_fts(id, content)
            VALUES (new.id, new.content);
        END
        """
    )

    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS hlsm_episodic_after_delete
        AFTER DELETE ON hlsm_episodic
        BEGIN
            DELETE FROM hlsm_episodic_fts WHERE id = old.id;
        END
        """
    )

    op.execute(
        """
        CREATE TRIGGER IF NOT EXISTS hlsm_episodic_after_update
        AFTER UPDATE OF content ON hlsm_episodic
        BEGIN
            UPDATE hlsm_episodic_fts
            SET content = new.content
            WHERE id = old.id;
        END
        """
    )


# ── Downgrade ─────────────────────────────────────────────────────────────────

def downgrade() -> None:
    if not _is_sqlite():
        return

    op.execute("DROP TRIGGER IF EXISTS hlsm_episodic_after_update")
    op.execute("DROP TRIGGER IF EXISTS hlsm_episodic_after_delete")
    op.execute("DROP TRIGGER IF EXISTS hlsm_episodic_after_insert")
    op.execute("DROP TABLE IF EXISTS hlsm_episodic_fts")
