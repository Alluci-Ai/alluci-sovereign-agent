
import os
import asyncio
import logging
from ..logging_config import get_logger
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = get_logger("MemoryManager")

class MemoryManager:
    """
    Sovereign Persistent Memory Manager.
    Uses ChromaDB for vector-based semantic search and long-term context retrieval.
    Falls back to FTSMemoryManager (SQLite FTS5) in LITE_MODE.
    """
    def __init__(self, persist_directory: Optional[str] = None):
        from .fts_manager import FTSMemoryManager
        from ..config import settings
        
        self.lite_mode = getattr(settings, "LITE_MODE", False)
        self.persist_directory = persist_directory or os.path.expanduser("~/.polytope/memory")
        
        if self.lite_mode:
            logger.info("[ MEMORY ] LITE_MODE enabled. Initializing FTSMemoryManager.")
            self.fts_manager = FTSMemoryManager(self.persist_directory)
            self.collection = None
            return

        if not os.path.exists(self.persist_directory):
            os.makedirs(self.persist_directory, mode=0o700, exist_ok=True)
        
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name="polytope_memories",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"[ MEMORY ] ChromaDB initialized at {self.persist_directory}")
        except ImportError:
            logger.warning("[ MEMORY ] chromadb not found. Falling back to FTSMemoryManager.")
            self.lite_mode = True
            self.fts_manager = FTSMemoryManager(self.persist_directory)
            self.collection = None

    async def store(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """Stores a new memory fragment with semantic embeddings or FTS."""
        if self.lite_mode:
            return await self.fts_manager.store(content, metadata)

        import uuid
        mem_id = str(uuid.uuid4())
        meta = {**(metadata or {}), "timestamp": datetime.now().isoformat()}

        # ChromaDB is synchronous and CPU/IO-bound — run in thread pool to avoid
        # blocking the asyncio event loop. ChromaDB uses 'all-MiniLM-L6-v2' by default
        # (downloads ~80MB on first use if not already cached).
        await asyncio.to_thread(
            self.collection.add,
            documents=[content],
            metadatas=[meta],
            ids=[mem_id],
        )
        logger.info(f"[ MEMORY ] Stored fragment: {mem_id[:8]}...")
        return mem_id

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Performs semantic search across the memory manifold."""
        if self.lite_mode:
            return await self.fts_manager.search(query, limit)

        results = await asyncio.to_thread(
            self.collection.query,
            query_texts=[query],
            n_results=limit,
        )

        memories = []
        docs = results.get("documents", [[]])[0]
        ids = results.get("ids", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[None] * len(docs)])[0]

        for doc, mem_id, meta, dist in zip(docs, ids, metas, dists):
            memories.append({
                "id": mem_id,
                "content": doc,
                "metadata": meta,
                "distance": dist,
            })
        return memories

    async def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves recent memories (raw get, no semantic ranking)."""
        if self.lite_mode:
            return await self.fts_manager.get_recent(limit)

        results = await asyncio.to_thread(self.collection.get, limit=limit)

        memories = []
        docs = results.get("documents") or []
        ids = results.get("ids") or []
        metas = results.get("metadatas") or []

        for doc, mem_id, meta in zip(docs, ids, metas):
            memories.append({"id": mem_id, "content": doc, "metadata": meta})
        return memories

    async def delete(self, memory_id: str) -> bool:
        """Delete a specific memory fragment by its ID."""
        if self.lite_mode:
            return await self.fts_manager.delete(memory_id) if hasattr(self.fts_manager, "delete") else False

        try:
            await asyncio.to_thread(self.collection.delete, ids=[memory_id])
            logger.info(f"[ MEMORY ] Deleted fragment: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"[ MEMORY ] Delete failed for {memory_id}: {e}")
            return False
