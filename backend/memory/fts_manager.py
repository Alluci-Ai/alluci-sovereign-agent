
import sqlite3
import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("FTSMemoryManager")

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

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories USING fts5(content, metadata)")
            conn.execute("CREATE TABLE IF NOT EXISTS memory_meta (id TEXT PRIMARY KEY, timestamp TEXT)")
            conn.commit()

    async def store(self, content: str, metadata: Dict[str, Any] = None):
        mem_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        meta_json = str(metadata or {})
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT INTO memories(rowid, content, metadata) VALUES (?, ?, ?)", 
                         (None, content, meta_json))
            row_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO memory_meta(id, timestamp) VALUES (?, ?)", (mem_id, timestamp))
            # We use row_id to link metadata if needed, but for now simple storage
            conn.commit()
            
        logger.info(f"[ FTS_MEMORY ] Stored memory fragment: {mem_id[:8]}...")
        return mem_id

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        memories = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT rowid, content, metadata FROM memories WHERE memories MATCH ? ORDER BY rank LIMIT ?",
                (query, limit)
            )
            for row in cursor:
                # We don't easily have the UUID here without a mapping table, 
                # but for search results it's usually fine.
                memories.append({
                    "id": str(row["rowid"]),
                    "content": row["content"],
                    "metadata": eval(row["metadata"]), # Simple storage
                    "distance": 0.0 # No semantic distance in FTS
                })
        return memories

    async def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        memories = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT rowid, content, metadata FROM memories ORDER BY rowid DESC LIMIT ?",
                (limit,)
            )
            for row in cursor:
                memories.append({
                    "id": str(row["rowid"]),
                    "content": row["content"],
                    "metadata": eval(row["metadata"])
                })
        return memories

    async def delete(self, memory_id: str):
        # In this simple implementation, if memory_id is rowid
        try:
            row_id = int(memory_id)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM memories WHERE rowid = ?", (row_id,))
                conn.commit()
            logger.info(f"[ FTS_MEMORY ] Deleted memory fragment: {memory_id}")
        except ValueError:
            logger.warning(f"[ FTS_MEMORY ] Could not delete non-integer ID: {memory_id}")
