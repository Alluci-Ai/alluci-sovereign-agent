"""
FTSMemoryManager — SQLite FTS5 fallback memory store.
Used when ChromaDB is unavailable (LITE_MODE or ImportError).

Security hardening: metadata is stored as JSON and deserialised with
json.loads() — never eval(). The _safe_load_meta() helper handles legacy
rows that were written with str() before this fix.
"""

import ast
import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..logging_config import get_logger

logger = get_logger("FTSMemoryManager")


class FTSMemoryManager:
    """
    Lightweight memory manager using SQLite FTS5 for keyword-based search.
    Used as a fallback for ChromaDB on resource-constrained devices.
    """

    def __init__(self, persist_directory: str):
        self.db_path = os.path.join(persist_directory, "fts_memory.db")
        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory, mode=0o700, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memories "
                "USING fts5(content, metadata)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS memory_meta "
                "(id TEXT PRIMARY KEY, timestamp TEXT)"
            )
            conn.commit()

    @staticmethod
    def _safe_load_meta(raw: str) -> Dict[str, Any]:
        """
        Safely deserialise a stored metadata string.

        Attempts json.loads() first (current serialisation format).
        Falls back to ast.literal_eval() for rows written before this fix
        when metadata was stored with str() / Python repr.
        Returns {} on any parse failure — never raises, never calls eval().
        """
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            pass
        try:
            result = ast.literal_eval(raw)
            if isinstance(result, dict):
                return result
        except (ValueError, SyntaxError):
            pass
        logger.warning(
            "[FTS_MEMORY] Could not deserialise metadata row — "
            "returning empty dict. Raw (truncated): %s",
            raw[:120],
        )
        return {}

    async def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        mem_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        # json.dumps produces valid JSON that round-trips through json.loads
        meta_json = json.dumps(metadata or {})

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO memories(rowid, content, metadata) VALUES (?, ?, ?)",
                (None, content, meta_json),
            )
            conn.execute(
                "INSERT INTO memory_meta(id, timestamp) VALUES (?, ?)",
                (mem_id, timestamp),
            )
            conn.commit()

        logger.info("[FTS_MEMORY] Stored memory fragment: %s...", mem_id[:8])
        return mem_id

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        memories: List[Dict[str, Any]] = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute(
                    "SELECT rowid, content, metadata FROM memories "
                    "WHERE memories MATCH ? ORDER BY rank LIMIT ?",
                    (query, limit),
                )
            except sqlite3.OperationalError as e:
                # FTS5 MATCH raises on malformed query tokens
                logger.warning("[FTS_MEMORY] FTS search error for %r: %s", query, e)
                return memories

            for row in cursor:
                memories.append(
                    {
                        "id": str(row["rowid"]),
                        "content": row["content"],
                        "metadata": self._safe_load_meta(row["metadata"]),
                        "distance": 0.0,
                    }
                )
        return memories

    async def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        memories: List[Dict[str, Any]] = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT rowid, content, metadata FROM memories "
                "ORDER BY rowid DESC LIMIT ?",
                (limit,),
            )
            for row in cursor:
                memories.append(
                    {
                        "id": str(row["rowid"]),
                        "content": row["content"],
                        "metadata": self._safe_load_meta(row["metadata"]),
                    }
                )
        return memories

    async def delete(self, memory_id: str) -> bool:
        try:
            row_id = int(memory_id)
        except ValueError:
            logger.warning(
                "[FTS_MEMORY] Could not delete non-integer ID: %s", memory_id
            )
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memories WHERE rowid = ?", (row_id,))
            conn.commit()
        logger.info("[FTS_MEMORY] Deleted memory fragment: %s", memory_id)
        return True
