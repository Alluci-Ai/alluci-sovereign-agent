
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("MemoryManager")

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

    async def store(self, content: str, metadata: Dict[str, Any] = None):
        """Stores a new memory fragment with semantic embeddings or FTS."""
        if self.lite_mode:
            return await self.fts_manager.store(content, metadata)
        
        import uuid
        mem_id = str(uuid.uuid4())
        meta = metadata or {}
        meta["timestamp"] = datetime.now().isoformat()
        
        # In a real system, we'd use a local embedding model (e.g., SentenceTransformers)
        # ChromaDB by default uses 'all-MiniLM-L6-v2' if no embedding function is provided.
        # This will download the model on first use (~80MB).
        
        self.collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[mem_id]
        )
        logger.info(f"[ MEMORY ] Stored memory fragment: {mem_id[:8]}...")
        return mem_id

    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Performs semantic search or keyword search across the memory manifold."""
        if self.lite_mode:
            return await self.fts_manager.search(query, limit)
            
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        memories = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                memories.append({
                    "id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i]
                })
        return memories

    async def get_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves recent memories (raw get)."""
        if self.lite_mode:
            return await self.fts_manager.get_recent(limit)
            
        results = self.collection.get(limit=limit)
        memories = []
        if results["documents"]:
            for i in range(len(results["documents"])):
                memories.append({
                    "id": results["ids"][i],
                    "content": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
        return memories

    async def delete(self, memory_id: str):
        if self.lite_mode:
            return await self.fts_manager.delete(memory_id)
            
        self.collection.delete(ids=[memory_id])
        logger.info(f"[ MEMORY ] Deleted memory fragment: {memory_id}")
