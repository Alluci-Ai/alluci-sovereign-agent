"""
H-LSM Memory Adapter
====================
Provides DAG executor actions for querying and storing memories
across all three H-LSM tiers.

Actions exposed to the planner:
  - memory_search   : Semantic + FTS search across L1 and L2
  - memory_store    : Store a new episodic memory (L1)
  - memory_recall   : Get recent working memory for current session
  - memory_working  : Get current session L0 working window
"""
import logging
from ..logging_config import get_logger
from typing import Dict, Any, List, Optional

from .base import Adapter

logger = get_logger("Adapters.HLSMMemory")


class HLSMMemoryAdapter(Adapter):
    """
    DAG executor adapter for H-LSM memory operations.
    All methods are production-ready — no stubs or mock fallbacks.
    """

    def __init__(self, hlsm_manager):
        self.hlsm = hlsm_manager

    @property
    def name(self) -> str:  # type: ignore
        return "memory"

    async def execute(self, args: Dict[str, Any]) -> Any:
        """
        Dispatch to the appropriate HLSM operation based on args["action"].

        Expected args structure:
            {
                "action": "memory_search" | "memory_store" | "memory_recall" | "memory_working",
                "query": str,                # For search/recall
                "content": str,              # For store
                "session_key": str,          # Optional — session scoping
                "limit": int,                # Optional — max results (default 5)
                "psi": float,                # Optional — current affective tension
                "source": str,               # Optional — origin label for store
                "metadata": dict,            # Optional — extra metadata for store
            }
        """
        if not self.hlsm:
            return "H-LSM memory manager not initialized."

        action = args.get("action", "memory_search")
        query = args.get("query", "")
        content = args.get("content", "")
        session_key = args.get("session_key", "")
        limit = int(args.get("limit", 5))
        psi = float(args.get("psi", 0.0))
        source = args.get("source", "task_result")
        metadata = args.get("metadata") or {}

        if action in ("memory_search", "search"):
            if not query:
                return "memory_search requires a 'query' argument."
            ctx = await self.hlsm.retrieve_context(
                objective=query, psi=psi, session_key=session_key
            )
            results = (
                ctx.working_memories[:limit]
                + ctx.episodic_memories[:limit]
                + ctx.semantic_memories[:limit]
            )
            if not results:
                return "No relevant memories found."
            return "\n".join([
                f"[Tier-{r.tier} | {r.source}] {r.content[:300]}"
                for r in results
            ])

        elif action in ("memory_store", "store"):
            if not content:
                return "memory_store requires a 'content' argument."
            entry_id = await self.hlsm.l1_store(
                content=content,
                source=source,
                session_key=session_key,
                psi=psi,
                extra_metadata=metadata if metadata else None,
            )
            return f"Stored memory {entry_id[:8]} to L1 episodic tier."

        elif action in ("memory_recall", "recall"):
            recent = await self.hlsm.l1_get_recent(limit=limit, session_key=session_key)
            if not recent:
                return "No recent episodic memories found."
            return "\n".join([
                f"[{r.source}] {r.content[:300]}"
                for r in recent
            ])

        elif action in ("memory_working", "working"):
            working = await self.hlsm.l0_retrieve(session_key)
            if not working:
                return "Working memory is empty for this session."
            return "\n".join([
                f"[working:{r.source}] {r.content[:200]}"
                for r in working
            ])

        else:
            return (
                f"Unknown memory action: '{action}'. "
                f"Valid actions: memory_search, memory_store, memory_recall, memory_working"
            )
