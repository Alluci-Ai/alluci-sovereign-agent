
import os
import asyncio
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
            import numpy as np
            if not hasattr(np, 'float_'):
                setattr(np, 'float_', np.float64)
            import sys
            import chromadb
            if sys.platform == "darwin":
                from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
                class MLXEmbeddingFunction(EmbeddingFunction):
                    def __init__(self):
                        import threading
                        self.model = None
                        self.tokenizer = None
                        self.lock = threading.Lock()
                    def __call__(self, input: Documents) -> Embeddings:
                        import mlx.core as mx
                        try:
                            from mlx_lm import load
                        except ImportError:
                            load = None
                        
                        if self.model is None and load is not None:
                            with self.lock:
                                if self.model is None:
                                    logger.info("[ MEMORY ] Loading MLX Native Embedder...")
                                    try:
                                        loaded = load("nomic-ai/nomic-embed-text-v1.5-mlx")
                                        self.tokenizer = loaded[1]
                                        self.model = loaded[0]
                                    except Exception as e:
                                        logger.error(f"[ MEMORY ] Failed to load MLX embedder: {e}")
                                        self.model = False # mark failed
                        
                        embeddings = []
                        for text in input:
                            try:
                                if hasattr(self.model, "embed") and self.tokenizer is not None:
                                    tokens = self.tokenizer.encode(text)
                                    emb = self.model.embed(mx.array([tokens]))
                                    embeddings.append(emb.tolist()[0])
                                else:
                                    # Fallback 768d vector to prevent ChromaDB crash if model lacks .embed()
                                    embeddings.append([0.0] * 768)
                            except Exception:
                                embeddings.append([0.0] * 768)
                        return embeddings

                emb_fn = MLXEmbeddingFunction()
                coll_name = "polytope_memories_mlx"
            else:
                emb_fn = None # Uses Chroma default CPU engine
                coll_name = "polytope_memories_pc"

            self.client = chromadb.PersistentClient(path=self.persist_directory)
            self.collection = self.client.get_or_create_collection(
                name=coll_name,
                embedding_function=emb_fn,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"[ MEMORY ] ChromaDB initialized at {self.persist_directory} with collection {coll_name}")
        except ImportError:
            logger.warning("[ MEMORY ] chromadb not found. Falling back to FTSMemoryManager.")
            self.lite_mode = True
            self.fts_manager = FTSMemoryManager(self.persist_directory)
            self.collection = None

    async def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Stores a new memory fragment with semantic embeddings or FTS."""
        if self.lite_mode:
            return await self.fts_manager.store(content, metadata or {})

        import uuid
        mem_id = str(uuid.uuid4())
        meta = {**(metadata or {}), "timestamp": datetime.now().isoformat()}

        assert self.collection is not None

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

        assert self.collection is not None

        results = await asyncio.to_thread(
            self.collection.query,
            query_texts=[query],
            n_results=limit,
        )

        memories = []
        docs = results.get("documents", [[]])[0]  # type: ignore
        ids = results.get("ids", [[]])[0]
        metas = results.get("metadatas", [[]])[0]  # type: ignore
        dists = results.get("distances", [[None] * len(docs)])[0]  # type: ignore

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

        assert self.collection is not None

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

        assert self.collection is not None

        try:
            await asyncio.to_thread(self.collection.delete, ids=[memory_id])
            logger.info(f"[ MEMORY ] Deleted fragment: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"[ MEMORY ] Delete failed for {memory_id}: {e}")
            return False
