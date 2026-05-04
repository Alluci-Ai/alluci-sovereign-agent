"""
Hierarchical Long-Short Manifold (H-LSM) Memory Manager
========================================================

Three-tier sovereign memory architecture:

  L0 — Working Memory   : Redis (TTL 1h) | SQL fallback in LITE_MODE
  L1 — Episodic Memory  : SQLite/PostgreSQL with topology-decay
  L2 — Semantic Memory  : ChromaDB vector store (promoted from L1)

Integration points:
  - Called by orchestrator._build_system_context() for retrieval
  - Called by orchestrator.execute_objective() for post-execution encoding
  - Consolidation sweep runs every 30 min via AsyncIO background task
  - AffectKernel modulates retrieval scoring via ψ/valence
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, select, col

from ..logging_config import get_logger
from ..ace.memory_decay import MemoryTopologyDecay
from ..models import HLSMEpisodicEntry, HLSMWorkingEntry
from ..inference.ppn import DiscreteProjectionKernel

logger = get_logger("HLSM")

# ─── Configuration Constants ──────────────────────────────────────────────────

L0_TTL_SECONDS: float = 3600.0          # 1 hour working memory TTL
L0_MAX_ENTRIES: int = 50                 # Max working entries per session
L1_HALF_LIFE_SECONDS: float = 2592000.0 # 30-day half-life for episodic
L1_PRUNE_THRESHOLD: float = 0.10        # Retention below this → delete L1
L2_PRUNE_THRESHOLD: float = 0.05        # Retention below this → delete L2
PROMOTION_ACCESS_COUNT: int = 3         # L1 access count needed to promote to L2
PROMOTION_RETENTION_MIN: float = 0.30   # L1 retention must be above this to promote
MAX_MEMORY_TOKENS: int = 1500           # Approx token budget for context injection
MAX_MEMORY_CHARS: int = MAX_MEMORY_TOKENS * 4  # ~6000 chars
CONSOLIDATION_INTERVAL_SECONDS: float = 1800.0  # 30 minutes


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class HLSMRetrievalResult:
    """A single memory item returned by retrieve_context()."""
    id: str
    content: str
    tier: int                        # 0=working, 1=episodic, 2=semantic
    source: str
    relevance_score: float           # Combined retrieval + retention score
    retention_score: float           # Decay-computed retention ∈ [0, 1]
    psi_at_encoding: float = 0.0
    session_key: str = ""
    access_count: int = 0


@dataclass
class HLSMContext:
    """Structured context block injected into the planning context."""
    working_memories: List[HLSMRetrievalResult] = field(default_factory=list)
    episodic_memories: List[HLSMRetrievalResult] = field(default_factory=list)
    semantic_memories: List[HLSMRetrievalResult] = field(default_factory=list)
    total_chars: int = 0
    total_tokens: int = 0

    def to_prompt_block(self) -> str:
        """
        Renders the H-LSM context as a structured prompt block.
        Sections are ordered by relevance and tier priority.
        """
        if not (self.working_memories or self.episodic_memories or self.semantic_memories):
            return ""

        lines = ["[ SOVEREIGN MEMORY CONTEXT ]"]

        if self.working_memories:
            lines.append("\n── Working Memory (Current Session) ──")
            for m in self.working_memories[:5]:
                lines.append(f"  • {m.content[:300]}")

        if self.episodic_memories:
            lines.append("\n── Episodic Memory (Recent Experience) ──")
            for m in self.episodic_memories[:5]:
                src_tag = f"[{m.source}]" if m.source else ""
                lines.append(f"  • {src_tag} {m.content[:400]}")

        if self.semantic_memories:
            lines.append("\n── Semantic Memory (Long-Term Knowledge) ──")
            for m in self.semantic_memories[:5]:
                lines.append(f"  • {m.content[:500]}")

        return "\n".join(lines)


# ─── H-LSM Manager ────────────────────────────────────────────────────────────

class HLSMManager:
    """
    Hierarchical Long-Short Manifold Memory Manager.

    Manages three memory tiers with automatic promotion, decay, and
    affective modulation aligned with the ACE engine's ψ (psi) state.

    Usage:
        manager = HLSMManager(db_engine, redis_client, chroma_collection, settings)
        await manager.start_consolidation_loop()

        # During planning:
        ctx = await manager.retrieve_context(objective, psi=0.3, session_key="sess_abc")
        prompt_block = ctx.to_prompt_block()

        # After execution:
        await manager.encode_from_execution(run_id, task_results, objective, session_key, psi)
    """

    def __init__(
        self,
        db_engine,
        redis_client: Optional[Any],
        chroma_collection: Optional[Any],
        settings: Optional[Any] = None,
    ):
        self.db_engine = db_engine
        self.redis = redis_client
        self.chroma = chroma_collection
        self.settings = settings
        self.decay = MemoryTopologyDecay(half_life=L1_HALF_LIFE_SECONDS)
        self._consolidation_task: Optional[asyncio.Task] = None
        self._embed_model: Optional[Any] = None  # Lazy-loaded sentence-transformer
        
        # [ PPN-007 ] Simplicial H-LSM: Initialize the Discrete Projection Kernel
        self.dpk = DiscreteProjectionKernel()

        logger.info(
            "[HLSM] Initialized. "
            f"L0={'Redis' if redis_client else 'SQL-fallback'}, "
            f"L1=SQL, "
            f"L2={'ChromaDB' if chroma_collection else 'disabled'}"
        )

    def _get_token_count(self, text: str) -> int:
        """
        Returns estimated token count.
        Uses words * 1.35 as a robust heuristic for English/Code mixture.
        Replaces the brittle chars/4 approximation.
        """
        if not text: return 0
        return int(len(text.split()) * 1.35)

    # ─── Embedding (lazy load) ─────────────────────────────────────────────────

    def _get_embed_model(self):
        """Lazy-load the sentence-transformer model. Thread-safe via GIL."""
        if self._embed_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embed_model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("[HLSM] Sentence-transformer loaded (all-MiniLM-L6-v2)")
            except ImportError:
                logger.warning("[HLSM] sentence-transformers not available — L2 semantic search disabled")
        return self._embed_model

    # ─── L0 Working Memory ────────────────────────────────────────────────────

    def _l0_redis_key(self, session_key: str) -> str:
        return f"hlsm:working:{session_key}"

    async def l0_store(self, content: str, session_key: str, source: str = "conversation") -> str:
        """Store a working memory entry for the current session."""
        entry_id = str(uuid.uuid4())
        entry = {
            "id": entry_id,
            "content": content,
            "source": source,
            "created_at": time.time(),
        }

        if self.redis:
            try:
                key = self._l0_redis_key(session_key)
                # Store as a list; push to left (most recent first)
                await self.redis.lpush(key, json.dumps(entry))
                # Trim to max length
                await self.redis.ltrim(key, 0, L0_MAX_ENTRIES - 1)
                # Refresh TTL on every write
                await self.redis.expire(key, int(L0_TTL_SECONDS))
                return entry_id
            except Exception as e:
                logger.error(f"[HLSM L0] Redis store failed: {e} — falling back to SQL")

        # SQL fallback (LITE_MODE or Redis unavailable)
        now = time.time()
        db_entry = HLSMWorkingEntry(
            id=entry_id,
            session_key=session_key,
            content=content,
            source=source,
            created_at=now,
            expires_at=now + L0_TTL_SECONDS,
        )
        await asyncio.to_thread(self._l0_sql_store, db_entry)
        return entry_id

    def _l0_sql_store(self, entry: HLSMWorkingEntry) -> None:
        with Session(self.db_engine) as session:
            session.add(entry)
            session.commit()

    async def l0_retrieve(self, session_key: str) -> List[HLSMRetrievalResult]:
        """Retrieve all working memory for a session (most recent first)."""
        if self.redis:
            try:
                key = self._l0_redis_key(session_key)
                raw_entries = await self.redis.lrange(key, 0, L0_MAX_ENTRIES - 1)
                results = []
                for raw in raw_entries:
                    try:
                        entry = json.loads(raw)
                        results.append(HLSMRetrievalResult(
                            id=entry.get("id", ""),
                            content=entry.get("content", ""),
                            tier=0,
                            source=entry.get("source", "conversation"),
                            relevance_score=1.0,
                            retention_score=1.0,
                        ))
                    except json.JSONDecodeError:
                        continue
                return results
            except Exception as e:
                logger.error(f"[HLSM L0] Redis retrieve failed: {e}")

        # SQL fallback
        return await asyncio.to_thread(self._l0_sql_retrieve, session_key)

    def _l0_sql_retrieve(self, session_key: str) -> List[HLSMRetrievalResult]:
        now = time.time()
        with Session(self.db_engine) as session:
            entries = session.exec(
                select(HLSMWorkingEntry)
                .where(
                    HLSMWorkingEntry.session_key == session_key,
                    HLSMWorkingEntry.expires_at > now,
                )
                .order_by(col(HLSMWorkingEntry.created_at).desc())
                .limit(L0_MAX_ENTRIES)
            ).all()
        return [
            HLSMRetrievalResult(
                id=e.id, content=e.content, tier=0,
                source=e.source, relevance_score=1.0, retention_score=1.0,
            )
            for e in entries
        ]

    async def l0_clear_session(self, session_key: str) -> None:
        """Remove all working memory for a session (called on session end)."""
        if self.redis:
            try:
                await self.redis.delete(self._l0_redis_key(session_key))
            except Exception as e:
                logger.error(f"[HLSM L0] Redis clear failed: {e}")
        await asyncio.to_thread(self._l0_sql_clear, session_key)

    def _l0_sql_clear(self, session_key: str) -> None:
        with Session(self.db_engine) as session:
            entries = session.exec(
                select(HLSMWorkingEntry).where(HLSMWorkingEntry.session_key == session_key)
            ).all()
            for e in entries:
                session.delete(e)
            session.commit()

    # ─── L1 Episodic Memory ───────────────────────────────────────────────────

    async def l1_store(
        self,
        content: str,
        source: str = "task_result",
        session_key: str = "",
        objective: str = "",
        psi: float = 0.0,
        valence: float = 0.5,
        topological_importance: float = 1.0,
        extra_metadata: Optional[Dict] = None,
    ) -> str:
        """Store an episodic memory entry to L1 (SQL)."""
        entry_id = str(uuid.uuid4())
        now = time.time()
        objective_hash = hashlib.sha256(objective.encode()).hexdigest()[:16] if objective else ""

        entry = HLSMEpisodicEntry(
            id=entry_id,
            content=content,
            source=source,
            session_key=session_key,
            objective_hash=objective_hash,
            psi_at_encoding=max(0.0, min(1.0, float(psi))),
            valence_at_encoding=max(0.0, min(1.0, float(valence))),
            topological_importance=max(0.1, float(topological_importance)),
            betti_1_support=0.0,
            access_count=0,
            last_accessed=now,
            created_at=now,
            retention_score=1.0,
            promoted_to_l2=False,
            extra_metadata=json.dumps(extra_metadata) if extra_metadata else None,
        )

        await asyncio.to_thread(self._l1_sql_insert, entry)
        logger.debug(f"[HLSM L1] Stored episodic entry {entry_id[:8]} source={source}")
        return entry_id

    def _l1_sql_insert(self, entry: HLSMEpisodicEntry) -> None:
        with Session(self.db_engine) as session:
            session.add(entry)
            session.commit()

    async def l1_search(self, query: str, limit: int = 10) -> List[HLSMRetrievalResult]:
        """
        Full-text search across L1 episodic memories.
        Uses FTS5 for high-performance matching.
        """
        results = await asyncio.to_thread(self._l1_fts_search, query, limit)
        if results:
            ids_to_update = [r.id for r in results]
            await asyncio.to_thread(self._l1_update_access, ids_to_update)
        return results

    def _l1_fts_search(self, query: str, limit: int) -> List[HLSMRetrievalResult]:
        """
        SQLite FTS5 MATCH or PostgreSQL ILIKE search for episodic entries.
        Returns entries sorted by retention × relevance.
        """
        now = time.time()
        results: List[HLSMRetrievalResult] = []
        clean_query = query.replace("'", "''").strip()

        with Session(self.db_engine) as session:
            from sqlalchemy import text as sa_text
            db_url = str(self.db_engine.url)

            if "sqlite" in db_url:
                try:
                    # High-performance FTS5 MATCH
                    raw = session.exec(sa_text(
                        "SELECT main.id, main.content, main.source, main.session_key, "
                        "main.psi_at_encoding, main.topological_importance, "
                        "main.betti_1_support, main.access_count, main.last_accessed, "
                        "main.retention_score "
                        "FROM hlsm_episodic main "
                        "JOIN hlsm_episodic_fts fts ON main.id = fts.id "
                        "WHERE hlsm_episodic_fts MATCH :q "
                        "ORDER BY rank "
                        "LIMIT :limit"
                    ).bindparams(q=clean_query, limit=limit)).fetchall()
                except Exception as e:
                    logger.debug(f"[HLSM L1] FTS5 search failed: {e} - falling back to LIKE")
                    # Fallback to standard LIKE
                    raw = session.exec(sa_text(
                        "SELECT id, content, source, session_key, psi_at_encoding, "
                        "topological_importance, betti_1_support, access_count, "
                        "last_accessed, retention_score "
                        "FROM hlsm_episodic "
                        "WHERE content LIKE :q "
                        "ORDER BY last_accessed DESC "
                        "LIMIT :limit"
                    ).bindparams(q=f"%{clean_query}%", limit=limit)).fetchall()
            else:
                # PostgreSQL High-Performance FTS (Native tsvector)
                # This assumes a GIN index on content (handled in Phase 3 hardening)
                raw = session.exec(sa_text(
                    "SELECT id, content, source, session_key, psi_at_encoding, "
                    "topological_importance, betti_1_support, access_count, "
                    "last_accessed, retention_score "
                    "FROM hlsm_episodic "
                    "WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :q) "
                    "ORDER BY ts_rank(to_tsvector('english', content), plainto_tsquery('english', :q)) DESC "
                    "LIMIT :limit"
                ).bindparams(q=query, limit=limit)).fetchall()

            for row in raw:
                (entry_id, content, source, session_key, psi_enc,
                 topo_imp, betti_1, access_count, last_accessed, retention) = row

                # Recompute retention
                retention = self.decay.calculate_retention(
                    last_accessed=float(last_accessed or now),
                    topological_importance=float(topo_imp or 1.0),
                    betti_1_support=float(betti_1 or 0.0),
                )
                if self.decay.should_prune(retention, L1_PRUNE_THRESHOLD):
                    continue

                # Relevance = retention score (FTS doesn't provide BM25 rank via SQLModel)
                results.append(HLSMRetrievalResult(
                    id=str(entry_id),
                    content=str(content),
                    tier=1,
                    source=str(source or ""),
                    relevance_score=retention,
                    retention_score=retention,
                    psi_at_encoding=float(psi_enc or 0.0),
                    session_key=str(session_key or ""),
                    access_count=int(access_count or 0),
                ))

        # Sort by retention × access_count (recency + frequency combined)
        results.sort(key=lambda r: r.retention_score * (1 + r.access_count * 0.1), reverse=True)
        return results[:limit]

    def _l1_update_access(self, ids: List[str]) -> None:
        """Increment access_count and update last_accessed for retrieved entries."""
        now = time.time()
        with Session(self.db_engine) as session:
            entries = session.exec(
                select(HLSMEpisodicEntry).where(col(HLSMEpisodicEntry.id).in_(ids))
            ).all()
            for entry in entries:
                entry.access_count += 1
                entry.last_accessed = now
            session.commit()

    async def l1_get_recent(self, limit: int = 20, session_key: str = "") -> List[HLSMRetrievalResult]:
        """Get most recent L1 episodic entries, optionally filtered by session."""
        return await asyncio.to_thread(self._l1_sql_recent, limit, session_key)

    def _l1_sql_recent(self, limit: int, session_key: str) -> List[HLSMRetrievalResult]:
        now = time.time()
        with Session(self.db_engine) as session:
            stmt = select(HLSMEpisodicEntry).order_by(col(HLSMEpisodicEntry.created_at).desc())
            if session_key:
                stmt = stmt.where(HLSMEpisodicEntry.session_key == session_key)
            entries = session.exec(stmt.limit(limit)).all()

        results = []
        for e in entries:
            retention = self.decay.calculate_retention(
                e.last_accessed, e.topological_importance, e.betti_1_support
            )
            if self.decay.should_prune(retention, L1_PRUNE_THRESHOLD):
                continue
            results.append(HLSMRetrievalResult(
                id=e.id, content=e.content, tier=1,
                source=e.source, relevance_score=retention, retention_score=retention,
                psi_at_encoding=e.psi_at_encoding, session_key=e.session_key,
                access_count=e.access_count,
            ))
        return results

    # ─── L2 Semantic Memory ───────────────────────────────────────────────────

    async def l2_store(self, entry: HLSMEpisodicEntry) -> Optional[str]:
        """
        Promote an L1 entry to L2 ChromaDB semantic storage.
        Returns ChromaDB document ID on success, None if L2 unavailable.
        """
        if not self.chroma:
            logger.debug("[HLSM L2] ChromaDB not available — skipping L2 promotion")
            return None

        # [ PPN-008 ] Generate Topological Barcode (Simplicial Projection)
        betti_signature = self.dpk.get_betti_signature(self.dpk.project_state(entry.content))

        meta = {
            "source": entry.source,
            "session_key": entry.session_key,
            "objective_hash": entry.objective_hash,
            "psi_at_encoding": entry.psi_at_encoding,
            "valence_at_encoding": entry.valence_at_encoding,
            "topological_importance": entry.topological_importance,
            "betti_1_support": entry.betti_1_support,
            "betti_signature": str(betti_signature),  # Topological Barcode
            "access_count": entry.access_count,
            "created_at": entry.created_at,
            "l1_id": entry.id,
        }

        try:
            chroma_id = f"l2_{entry.id}"
            await asyncio.to_thread(
                self.chroma.add,
                documents=[entry.content],
                metadatas=[meta],
                ids=[chroma_id],
            )
            logger.info(f"[HLSM L2] Promoted L1→L2: {entry.id[:8]} → {chroma_id}")
            return chroma_id
        except Exception as e:
            logger.error(f"[HLSM L2] ChromaDB store failed for {entry.id}: {e}", exc_info=True)
            return None

    async def l2_search(self, query: str, limit: int = 10) -> List[HLSMRetrievalResult]:
        """Semantic similarity search against L2 ChromaDB collection."""
        if not self.chroma:
            return []

        try:
            raw = await asyncio.to_thread(
                self.chroma.query,
                query_texts=[query],
                n_results=min(limit, max(1, self.chroma.count() if hasattr(self.chroma, 'count') else limit)),
            )

            results = []
            docs = raw.get("documents", [[]])[0]
            ids = raw.get("ids", [[]])[0]
            metas = raw.get("metadatas", [[]])[0]
            dists = raw.get("distances", [[None] * len(docs)])[0]

            for doc, chroma_id, meta, dist in zip(docs, ids, metas, dists):
                # Convert ChromaDB cosine distance [0,2] to similarity [1,0]
                similarity = 1.0 - (float(dist) / 2.0) if dist is not None else 0.5

                # Apply Betti-1 boost from metadata
                betti_support = float(meta.get("betti_1_support", 0.0)) if meta else 0.0
                topo_imp = float(meta.get("topological_importance", 1.0)) if meta else 1.0
                created_at = float(meta.get("created_at", time.time())) if meta else time.time()
                
                # [ PPN-009 ] Structural Homeomorphism Check
                stored_betti = meta.get("betti_signature", "") if meta else ""
                query_betti = str(self.dpk.get_betti_signature(self.dpk.project_state(query)))
                
                # If the query and memory share the same topological shape, strongly boost relevance
                if stored_betti and stored_betti == query_betti:
                    similarity = min(1.0, similarity + 0.5)
                    topo_imp += 0.5

                # Compute retention from creation time
                retention = self.decay.calculate_retention(
                    last_accessed=created_at,
                    topological_importance=topo_imp,
                    betti_1_support=betti_support,
                )
                if self.decay.should_prune(retention, L2_PRUNE_THRESHOLD):
                    continue

                # Combined score: similarity × retention
                combined = similarity * retention

                results.append(HLSMRetrievalResult(
                    id=chroma_id,
                    content=doc,
                    tier=2,
                    source=meta.get("source", "") if meta else "",
                    relevance_score=combined,
                    retention_score=retention,
                    psi_at_encoding=float(meta.get("psi_at_encoding", 0.0)) if meta else 0.0,
                    session_key=meta.get("session_key", "") if meta else "",
                    access_count=int(meta.get("access_count", 0)) if meta else 0,
                ))

            results.sort(key=lambda r: r.relevance_score, reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"[HLSM L2] ChromaDB search failed: {e}", exc_info=True)
            return []

    async def l2_delete(self, chroma_id: str) -> bool:
        """Remove a pruned entry from ChromaDB."""
        if not self.chroma:
            return False
        try:
            await asyncio.to_thread(self.chroma.delete, ids=[chroma_id])
            logger.info(f"[HLSM L2] Pruned decayed entry: {chroma_id}")
            return True
        except Exception as e:
            logger.error(f"[HLSM L2] Delete failed for {chroma_id}: {e}")
            return False

    # ─── Unified Retrieval ────────────────────────────────────────────────────

    async def retrieve_context(
        self,
        objective: str,
        psi: float = 0.0,
        session_key: str = "",
        valence: float = 0.5,
        max_per_tier: int = 5,
    ) -> HLSMContext:
        """
        Main retrieval entrypoint. Called by orchestrator._build_system_context().

        Queries all three tiers in parallel, merges, applies affective modulation,
        and returns a structured HLSMContext ready for prompt injection.

        Args:
            objective: The current objective text (used as search query)
            psi: Current affective tension ψ ∈ [0, 1]
            session_key: Current session identifier
            valence: Current affective valence ∈ [0, 1]
            max_per_tier: Max entries per tier in the returned context

        Returns:
            HLSMContext with working, episodic, and semantic memory lists
        """
        # Derive a search query from the objective
        # Use first 200 chars as search terms — sufficient for FTS + vector search
        search_query = objective[:200].strip()

        # Parallel retrieval from all three tiers
        l0_results, l1_results, l2_results = await asyncio.gather(
            self.l0_retrieve(session_key),
            self.l1_search(search_query, limit=max_per_tier * 2),
            self.l2_search(search_query, limit=max_per_tier * 2),
            return_exceptions=True,
        )

        # Handle exceptions from individual tier failures
        if isinstance(l0_results, Exception):
            logger.error(f"[HLSM] L0 retrieval failed: {l0_results}")
            l0_results = []
        if isinstance(l1_results, Exception):
            logger.error(f"[HLSM] L1 retrieval failed: {l1_results}")
            l1_results = []
        if isinstance(l2_results, Exception):
            logger.error(f"[HLSM] L2 retrieval failed: {l2_results}")
            l2_results = []

        # Apply affective modulation to L1 and L2 scores
        # High ψ → agent under stress → boost high-importance memories
        # Low ψ → calm exploration → allow lower-retention memories
        if psi > 0.0:
            try:
                from ..ace.affect_kernel import AffectKernel, AffectiveState
                kernel = AffectKernel()
                affect_state = AffectiveState(
                    valence=valence * 1024.0,
                    arousal=psi * 512.0,
                    tension=psi * 1024.0,
                )
                for result in l1_results + l2_results:
                    result.relevance_score = max(0.0, min(1.0,
                        kernel.apply(result.relevance_score, affect_state)
                    ))
            except Exception as e:
                logger.debug(f"[HLSM] Affective modulation skipped: {e}")

        # Sort each tier by relevance
        l1_results.sort(key=lambda r: r.relevance_score, reverse=True)
        l2_results.sort(key=lambda r: r.relevance_score, reverse=True)

        # Build context, respecting token budget
        ctx = HLSMContext(
            working_memories=l0_results[:max_per_tier],
            episodic_memories=l1_results[:max_per_tier],
            semantic_memories=l2_results[:max_per_tier],
        )
        prompt = ctx.to_prompt_block()
        ctx.total_chars = len(prompt)
        ctx.total_tokens = self._get_token_count(prompt)

        logger.info(
            f"[HLSM] Retrieved: L0={len(ctx.working_memories)}, "
            f"L1={len(ctx.episodic_memories)}, "
            f"L2={len(ctx.semantic_memories)} "
            f"({ctx.total_chars} chars, psi={psi:.2f})"
        )
        return ctx

    # ─── Encoding from Execution ──────────────────────────────────────────────

    async def encode_from_execution(
        self,
        run_id: int,
        tasks: Dict[str, Any],
        objective: str,
        session_key: str = "",
        psi: float = 0.0,
        valence: float = 0.5,
    ) -> int:
        """
        Post-execution memory formation. Called by orchestrator after task completion.

        Stores completed task results as L1 episodic memories.
        Skips failed tasks (they are stored as negative examples with low importance).
        Returns count of memories stored.

        Args:
            run_id: Database Run ID for traceability
            tasks: Dict[task_id, DAGTask] from the execution
            objective: The original objective (for hashing)
            session_key: Session identifier
            psi: Affective tension at time of completion
            valence: Affective valence at completion
        """
        stored = 0
        obj_hash = hashlib.sha256(objective.encode()).hexdigest()[:16]

        for task_id, task in tasks.items():
            status = getattr(task, "status", "unknown")
            result = getattr(task, "result", "")
            action = getattr(task, "action", "unknown")

            if not result or len(str(result).strip()) < 10:
                continue  # Skip empty or trivially short results

            if str(status) == "completed":
                content = (
                    f"[Task: {action}] Objective: {objective[:100]} | "
                    f"Result: {str(result)[:500]}"
                )
                importance = 1.0 + (psi * 0.5)  # High-tension results are more important
            elif str(status) == "failed":
                content = (
                    f"[Failed: {action}] Objective: {objective[:100]} | "
                    f"Error: {str(result)[:300]}"
                )
                importance = 0.5  # Lower importance for failures
            else:
                continue

            await self.l1_store(
                content=content,
                source="task_result",
                session_key=session_key,
                objective=objective,
                psi=psi,
                valence=valence,
                topological_importance=importance,
                extra_metadata={"run_id": run_id, "task_id": task_id, "action": action},
            )
            stored += 1

        # Also store the objective itself as a working memory entry
        if objective.strip():
            await self.l0_store(
                content=f"[Executed objective] {objective[:300]}",
                session_key=session_key,
                source="objective",
            )

        logger.info(f"[HLSM] Encoded {stored} task results from run {run_id} to L1 episodic")
        return stored

    async def encode_message(
        self,
        content: str,
        session_key: str,
        source: str = "conversation",
        psi: float = 0.0,
        valence: float = 0.5,
    ) -> str:
        """
        Store a single message (user input or agent reply) to L0 working memory.
        If content is substantive (>100 chars), also store to L1 episodic.
        """
        # Always store to L0 working memory
        l0_id = await self.l0_store(content, session_key, source)

        # Long messages → also encode to episodic for cross-session recall
        if len(content) >= 100:
            await self.l1_store(
                content=content,
                source=source,
                session_key=session_key,
                psi=psi,
                valence=valence,
                topological_importance=1.0,
            )

        return l0_id

    # ─── Consolidation Sweep ──────────────────────────────────────────────────

    async def consolidation_sweep(self) -> Dict[str, int]:
        """
        Runs the full memory consolidation cycle:
          1. Apply decay to all L1 entries
          2. Promote high-access L1 entries to L2
          3. Prune decayed L1 entries
          4. Prune decayed L2 entries from ChromaDB
          5. Prune expired L0 SQL fallback entries

        Returns summary counts: { promoted, pruned_l1, pruned_l2, pruned_l0 }
        """
        logger.info("[HLSM] Starting consolidation sweep...")
        summary = {"promoted": 0, "pruned_l1": 0, "pruned_l2": 0, "pruned_l0": 0}
        
        from ..metrics import MEMORY_CONSOLIDATION_TOTAL
        MEMORY_CONSOLIDATION_TOTAL.labels(tier="L0").inc()
        MEMORY_CONSOLIDATION_TOTAL.labels(tier="L1").inc()
        MEMORY_CONSOLIDATION_TOTAL.labels(tier="L2").inc()

        # ── L1 Promotion and Pruning ──────────────────────────────────────────
        l1_entries = await asyncio.to_thread(self._load_all_l1_for_consolidation)
        now = time.time()

        promote_ids: List[str] = []
        prune_ids: List[str] = []

        for entry in l1_entries:
            retention = self.decay.calculate_retention(
                last_accessed=entry.last_accessed,
                topological_importance=entry.topological_importance,
                betti_1_support=entry.betti_1_support,
            )

            if self.decay.should_prune(retention, L1_PRUNE_THRESHOLD):
                prune_ids.append(entry.id)
            elif (
                not entry.promoted_to_l2
                and entry.access_count >= PROMOTION_ACCESS_COUNT
                and retention >= PROMOTION_RETENTION_MIN
            ):
                promote_ids.append(entry.id)

        # Promote to L2
        for entry_id in promote_ids:
            entry = await asyncio.to_thread(self._load_l1_entry, entry_id)
            if entry:
                chroma_id = await self.l2_store(entry)
                if chroma_id:
                    await asyncio.to_thread(self._mark_l1_promoted, entry_id)
                    summary["promoted"] += 1

        # Prune L1
        if prune_ids:
            await asyncio.to_thread(self._prune_l1_entries, prune_ids)
            summary["pruned_l1"] = len(prune_ids)

        # ── L2 Pruning (ChromaDB) ─────────────────────────────────────────────
        if self.chroma:
            try:
                all_l2 = await asyncio.to_thread(self.chroma.get, limit=10000)
                l2_ids = all_l2.get("ids", [])
                l2_metas = all_l2.get("metadatas", [])

                for chroma_id, meta in zip(l2_ids, l2_metas):
                    if not meta:
                        continue
                    created_at = float(meta.get("created_at", now))
                    topo_imp = float(meta.get("topological_importance", 1.0))
                    betti_1 = float(meta.get("betti_1_support", 0.0))

                    retention = self.decay.calculate_retention(
                        last_accessed=created_at,
                        topological_importance=topo_imp,
                        betti_1_support=betti_1,
                    )
                    if self.decay.should_prune(retention, L2_PRUNE_THRESHOLD):
                        await self.l2_delete(chroma_id)
                        summary["pruned_l2"] += 1
            except Exception as e:
                logger.error(f"[HLSM] L2 consolidation error: {e}", exc_info=True)

        # ── L0 SQL Fallback TTL Pruning ───────────────────────────────────────
        pruned_l0 = await asyncio.to_thread(self._prune_expired_l0_sql)
        summary["pruned_l0"] = pruned_l0

        logger.info(
            f"[HLSM] Consolidation complete: "
            f"promoted={summary['promoted']}, "
            f"pruned_l1={summary['pruned_l1']}, "
            f"pruned_l2={summary['pruned_l2']}, "
            f"pruned_l0={summary['pruned_l0']}"
        )
        return summary

    def _load_all_l1_for_consolidation(self) -> List[HLSMEpisodicEntry]:
        with Session(self.db_engine) as session:
            return session.exec(select(HLSMEpisodicEntry)).all()

    def _load_l1_entry(self, entry_id: str) -> Optional[HLSMEpisodicEntry]:
        with Session(self.db_engine) as session:
            return session.get(HLSMEpisodicEntry, entry_id)

    def _mark_l1_promoted(self, entry_id: str) -> None:
        with Session(self.db_engine) as session:
            entry = session.get(HLSMEpisodicEntry, entry_id)
            if entry:
                entry.promoted_to_l2 = True
                session.add(entry)
                session.commit()

    def _prune_l1_entries(self, ids: List[str]) -> None:
        with Session(self.db_engine) as session:
            entries = session.exec(
                select(HLSMEpisodicEntry).where(col(HLSMEpisodicEntry.id).in_(ids))
            ).all()
            for e in entries:
                session.delete(e)
            session.commit()

    def _prune_expired_l0_sql(self) -> int:
        now = time.time()
        with Session(self.db_engine) as session:
            expired = session.exec(
                select(HLSMWorkingEntry).where(HLSMWorkingEntry.expires_at < now)
            ).all()
            count = len(expired)
            for e in expired:
                session.delete(e)
            session.commit()
        return count

    # ─── Background Loop ──────────────────────────────────────────────────────

    async def start_consolidation_loop(self) -> None:
        """Start the background consolidation task. Call from services.init_services()."""
        if self._consolidation_task and not self._consolidation_task.done():
            return
        self._consolidation_task = asyncio.create_task(self._consolidation_loop())
        logger.info(f"[HLSM] Consolidation loop started (interval={CONSOLIDATION_INTERVAL_SECONDS}s)")

    async def stop_consolidation_loop(self) -> None:
        """Stop the background consolidation task. Call from services.shutdown_services()."""
        if self._consolidation_task and not self._consolidation_task.done():
            self._consolidation_task.cancel()
            try:
                await self._consolidation_task
            except asyncio.CancelledError:
                logger.info("[HLSM] Consolidation loop stopped")

    async def _consolidation_loop(self) -> None:
        """Runs consolidation_sweep() on a fixed interval."""
        while True:
            try:
                await asyncio.sleep(CONSOLIDATION_INTERVAL_SECONDS)
                await self.consolidation_sweep()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[HLSM] Consolidation loop error: {e}", exc_info=True)
                # Back off and retry after 60 seconds on unexpected error
                await asyncio.sleep(60.0)

    # ─── Statistics & Introspection ───────────────────────────────────────────

    async def get_stats(self) -> Dict[str, Any]:
        """Returns memory system statistics for the MemoryPanel UI and /memory/stats endpoint."""
        l1_count = await asyncio.to_thread(self._count_l1)
        l0_count_sql = await asyncio.to_thread(self._count_l0_sql)
        l2_count = 0

        if self.chroma:
            try:
                l2_count = await asyncio.to_thread(self.chroma.count)
            except Exception:
                l2_count = -1

        return {
            "hlsm_version": "1.0",
            "tiers": {
                "L0_working": {
                    "backend": "Redis" if self.redis else "SQL-fallback",
                    "sql_entries": l0_count_sql,
                    "ttl_seconds": L0_TTL_SECONDS,
                },
                "L1_episodic": {
                    "backend": "SQL",
                    "entries": l1_count,
                    "half_life_days": L1_HALF_LIFE_SECONDS / 86400,
                    "prune_threshold": L1_PRUNE_THRESHOLD,
                    "promotion_threshold": PROMOTION_ACCESS_COUNT,
                },
                "L2_semantic": {
                    "backend": "ChromaDB" if self.chroma else "disabled",
                    "entries": l2_count,
                    "prune_threshold": L2_PRUNE_THRESHOLD,
                },
            },
            "consolidation_interval_minutes": CONSOLIDATION_INTERVAL_SECONDS / 60,
        }

    def _count_l1(self) -> int:
        with Session(self.db_engine) as session:
            return len(session.exec(select(HLSMEpisodicEntry)).all())

    def _count_l0_sql(self) -> int:
        now = time.time()
        with Session(self.db_engine) as session:
            return len(session.exec(
                select(HLSMWorkingEntry).where(HLSMWorkingEntry.expires_at > now)
            ).all())

    # ─── Legacy MemoryManager Compatibility ───────────────────────────────────
    # These methods provide drop-in compatibility with the existing MemoryAdapter
    # and MemoryManager API calls that pre-date H-LSM.

    async def store(self, content: str, metadata: Dict[str, Any] = None, session_key: str = "") -> str:
        """Legacy compatibility: store() → l1_store()."""
        source = (metadata or {}).get("source", "user_manual")
        psi = float((metadata or {}).get("psi", 0.0))
        return await self.l1_store(content=content, source=source, session_key=session_key,
                                   psi=psi, extra_metadata=metadata)

    async def search(self, query: str, limit: int = 5, session_key: str = "", psi: float = 0.0) -> List[Dict]:
        """Legacy compatibility: search() → retrieve_context() → dict list."""
        ctx = await self.retrieve_context(query, psi=psi, session_key=session_key)
        results = []
        for m in ctx.working_memories + ctx.episodic_memories + ctx.semantic_memories:
            results.append({
                "id": m.id,
                "content": m.content,
                "metadata": {"source": m.source, "tier": m.tier},
                "distance": 1.0 - m.relevance_score,
            })
        return results[:limit]

    async def list_entries(self, limit: int = 50, offset: int = 0) -> Dict:
        """Legacy compatibility: list_entries() for the memory router."""
        entries = await asyncio.to_thread(self._l1_paginate, limit, offset)
        return {
            "entries": [
                {"id": e.id, "content": e.content, "source": e.source,
                 "tier": 1, "access_count": e.access_count,
                 "retention_score": e.retention_score,
                 "created_at": e.created_at}
                for e in entries
            ],
            "total": await asyncio.to_thread(self._count_l1),
            "limit": limit,
            "offset": offset,
        }

    def _l1_paginate(self, limit: int, offset: int) -> List[HLSMEpisodicEntry]:
        with Session(self.db_engine) as session:
            return session.exec(
                select(HLSMEpisodicEntry)
                .order_by(col(HLSMEpisodicEntry.created_at).desc())
                .offset(offset)
                .limit(limit)
            ).all()

    async def delete(self, memory_id: str) -> bool:
        """Legacy compatibility: delete an L1 episodic entry by ID."""
        try:
            deleted = await asyncio.to_thread(self._l1_delete_by_id, memory_id)
            if not deleted:
                # Try L2
                await self.l2_delete(memory_id)
                return True
            return deleted
        except Exception as e:
            logger.error(f"[HLSM] Delete failed for {memory_id}: {e}")
            return False

    def _l1_delete_by_id(self, memory_id: str) -> bool:
        with Session(self.db_engine) as session:
            entry = session.get(HLSMEpisodicEntry, memory_id)
            if entry:
                session.delete(entry)
                session.commit()
                return True
        return False
