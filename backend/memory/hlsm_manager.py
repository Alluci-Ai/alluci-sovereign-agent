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
import time
import uuid
import re
from html.parser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
        self.ignore = False

    def handle_starttag(self, tag, attrs):
        if tag in ["style", "script", "head", "title", "meta"]:
            self.ignore = True

    def handle_endtag(self, tag):
        if tag in ["style", "script", "head", "title", "meta"]:
            self.ignore = False

    def handle_data(self, d):
        if not self.ignore:
            self.text.append(d)

    def get_data(self):
        return ''.join(self.text)

def _sanitize_hlsm_text(content: str) -> str:
    """Guarantee that H-LSM only ever ingests cleanly formatted text."""
    if not content or not isinstance(content, str):
        return str(content)
    if '<' not in content and '>' not in content:
        return content
    try:
        s = MLStripper()
        s.feed(content)
        cleaned = re.sub(r'\n\s*\n', '\n\n', s.get_data())
        return cleaned.strip()
    except Exception:
        cleaned = re.sub(r'<[^>]+>', '', content)
        return re.sub(r'\n\s*\n', '\n\n', cleaned).strip()
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
        manager = HLSMManager(db_engine, redis_client, settings.GRAPH_DB_PATH, settings)
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
        kuzu_db_path: Optional[str],
        settings: Optional[Any] = None,
    ):
        self.db_engine = db_engine
        self.redis = redis_client
        self.kuzu_db_path = kuzu_db_path
        self.settings = settings
        
        # Initialize KùzuDB connection
        self.kuzu_db = None
        self.kuzu_conn = None
        if kuzu_db_path:
            try:
                import kuzu
                self.kuzu_db = kuzu.Database(kuzu_db_path)
                self.kuzu_conn = kuzu.Connection(self.kuzu_db)
                
                self.kuzu_conn.execute(
                    "CREATE NODE TABLE IF NOT EXISTS SemanticMemory (id STRING, content STRING, source STRING, session_key STRING, psi_at_encoding DOUBLE, topological_importance DOUBLE, betti_1_support DOUBLE, betti_signature STRING, access_count INT64, created_at DOUBLE, l1_id STRING, is_barcode BOOLEAN, uri STRING, blob_path STRING, ttl DOUBLE, PRIMARY KEY (id))"
                )
                self.kuzu_conn.execute(
                    "CREATE NODE TABLE IF NOT EXISTS L3Memory (id STRING, content STRING, source STRING, session_key STRING, l1_id STRING, created_at DOUBLE, PRIMARY KEY (id))"
                )
                self.kuzu_conn.execute(
                    "CREATE NODE TABLE IF NOT EXISTS GraphNode (name STRING, PRIMARY KEY (name))"
                )
                self.kuzu_conn.execute(
                    "CREATE REL TABLE IF NOT EXISTS RELATES_TO (FROM GraphNode TO GraphNode, predicate STRING, source_memory STRING, weight DOUBLE)"
                )
            except ImportError:
                logger.warning("[HLSM] kuzu library not installed. L2 Semantic Memory disabled.")
            except Exception as e:
                logger.error(f"[HLSM] Failed to initialize KùzuDB at {kuzu_db_path}: {e}")

        self.decay = MemoryTopologyDecay(half_life=L1_HALF_LIFE_SECONDS)
        self._consolidation_task: Optional[asyncio.Task] = None
        self._embed_model: Optional[Any] = None  # Lazy-loaded sentence-transformer
        
        # [ PPN-007 ] Simplicial H-LSM: Initialize the Discrete Projection Kernel
        self.dpk = DiscreteProjectionKernel()

        logger.info(
            "[HLSM] Initialized. "
            f"L0={'Redis' if redis_client else 'SQL-fallback'}, "
            f"L1=SQL, "
            f"L2={'KùzuDB' if self.kuzu_conn else 'disabled'}"
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
        content = _sanitize_hlsm_text(content)
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
        content = _sanitize_hlsm_text(content)
        entry_id = str(uuid.uuid4())
        now = time.time()
        objective_hash = hashlib.sha256(objective.encode()).hexdigest()[:16] if objective else ""

        entry = HLSMEpisodicEntry(
            id=entry_id,
            content=content,
            source=source,
            session_key=session_key,
            objective_hash=objective_hash,
            psi_at_encoding=max(0.0, min(1.0, psi)),
            valence_at_encoding=max(0.0, min(1.0, valence)),
            topological_importance=max(0.1, topological_importance),
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

    async def synthesize_and_store_chat_session(
        self,
        session_key: str,
        messages: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Synthesizes a chat session into a high-density summary node and stores it in L1/L2.
        """
        from .chat_synthesis import ChatSynthesisEngine
        engine = ChatSynthesisEngine(settings=self.settings)
        payload = await engine.synthesize_session(session_key, messages)
        if not payload:
            return None
        
        # Store to L1 Episodic Memory
        entry_id = str(uuid.uuid4())
        now = time.time()
        entry = HLSMEpisodicEntry(
            id=entry_id,
            content=payload["summary_content"],
            source="chat_synthesis",
            session_key=session_key,
            objective_hash=hashlib.sha256(payload["topic_summary"].encode()).hexdigest()[:16],
            psi_at_encoding=0.5,
            valence_at_encoding=0.5,
            topological_importance=1.5,
            access_count=1,
            last_accessed=now,
            created_at=now,
            retention_score=1.0,
            promoted_to_l2=False,
            extra_metadata=json.dumps(payload["metadata"]),
        )
        await asyncio.to_thread(self._l1_sql_insert, entry)

        # Promote to L2 Semantic Memory if available
        if self.kuzu_conn:
            try:
                await self.l2_store(entry)
            except Exception as err:
                logger.warning(f"[HLSM] Failed to promote synthesized session {session_key[:8]} to L2: {err}")

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
                    raw = session.exec(sa_text(  # type: ignore
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
                    raw = session.exec(sa_text(  # type: ignore
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
                raw = session.exec(sa_text(  # type: ignore
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
        Promote an L1 entry to L2 KùzuDB semantic storage.
        Returns KùzuDB node ID on success, None if L2 unavailable.
        """
        if not self.kuzu_conn:
            logger.debug("[HLSM L2] KùzuDB not available — skipping L2 promotion")
            return None

        # [ PPN-008 ] Generate Topological Barcode (Simplicial Projection)
        betti_signature = self.dpk.get_betti_signature(self.dpk.project_state(entry.content))

        try:
            kuzu_id = f"l2_{entry.id}"
            
            # Cypher parameterized MERGE to insert the promoted memory
            query = (
                "MERGE (m:SemanticMemory {id: $id}) "
                "SET m.content = $content, m.source = $source, m.session_key = $session_key, "
                "m.psi_at_encoding = $psi_at_encoding, m.topological_importance = $topological_importance, "
                "m.betti_1_support = $betti_1_support, m.betti_signature = $betti_signature, "
                "m.access_count = $access_count, m.created_at = $created_at, m.l1_id = $l1_id, "
                "m.is_barcode = $is_barcode, m.uri = $uri, m.blob_path = $blob_path, m.ttl = $ttl"
            )
            
            extra = entry.extra_metadata or {}
            params = {
                "id": kuzu_id,
                "content": entry.content,
                "source": entry.source or "",
                "session_key": entry.session_key or "",
                "psi_at_encoding": entry.psi_at_encoding or 0.0,
                "topological_importance": entry.topological_importance or 1.0,
                "betti_1_support": entry.betti_1_support or 0.0,
                "betti_signature": betti_signature,
                "access_count": entry.access_count or 0,
                "created_at": entry.created_at or time.time(),
                "l1_id": entry.id,
                "is_barcode": extra.get("is_barcode", False),
                "uri": extra.get("uri", ""),
                "blob_path": extra.get("blob_path", ""),
                "ttl": extra.get("ttl", 0.0)
            }
            
            await asyncio.to_thread(self.kuzu_conn.execute, query, params)
            logger.info(f"[HLSM L2] Promoted L1→L2: {entry.id[:8]} → {kuzu_id} (Barcode: {betti_signature[:8]}...)")
            return kuzu_id
        except Exception as e:
            logger.error(f"[HLSM L2] KùzuDB store failed for {entry.id}: {e}", exc_info=True)
            return None

    async def l2_search(self, query: str, limit: int = 10) -> List[HLSMRetrievalResult]:
        """
        O(1) Topological Barcode search against L2 KùzuDB collection.
        Replaces slow cosine-similarity vector searches with instantaneous graph lookups.
        """
        if not self.kuzu_conn:
            return []

        try:
            # 1. Dynamically compute the topological barcode of the incoming query
            query_betti = str(self.dpk.get_betti_signature(self.dpk.project_state(query)))
            
            # 2. Execute an O(1) graph match in KùzuDB based on the barcode
            cypher_query = (
                "MATCH (m:SemanticMemory {betti_signature: $sig}) "
                "RETURN m.id, m.content, m.source, m.session_key, m.psi_at_encoding, "
                "m.topological_importance, m.betti_1_support, m.access_count, m.created_at, "
                "m.is_barcode, m.uri, m.blob_path, m.ttl "
                "LIMIT $limit"
            )
            
            raw_results = await asyncio.to_thread(
                self.kuzu_conn.execute, 
                cypher_query, 
                {"sig": query_betti, "limit": limit}
            )
            
            results = []
            
            while raw_results.has_next():
                row = raw_results.get_next()
                kuzu_id, content, source, session_key, psi_enc, topo_imp, betti_support, access_count, created_at, is_barcode, uri, blob_path, ttl = row
                
                if is_barcode:
                    try:
                        import os
                        if blob_path and os.path.exists(blob_path):
                            with open(blob_path, "r", encoding="utf-8") as f:
                                content = f.read()
                        else:
                            content = f"[Source Blob Unavailable]\n{content}"
                    except Exception as e:
                        logger.warning(f"[HLSM L2] Failed to rehydrate barcode {kuzu_id}: {e}")
                        content = f"[Source Blob Unavailable]\n{content}"
                
                # Because it's an exact topological match, similarity is 1.0
                similarity = 1.0
                
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
                    id=kuzu_id,
                    content=content,
                    tier=2,
                    source=source,
                    relevance_score=combined,
                    retention_score=retention,
                    psi_at_encoding=float(psi_enc),
                    session_key=session_key,
                    access_count=int(access_count),
                ))

            results.sort(key=lambda r: r.relevance_score, reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"[HLSM L2] KùzuDB search failed: {e}", exc_info=True)
            return []

    async def publish_subagent_insight(
        self,
        agent_id: str,
        topic: str,
        insight_summary: str,
        session_key: str = "",
        privacy_level: str = "PUBLIC"
    ) -> Optional[str]:
        """
        [ Federated SubAgent Memory Bus ]
        Publishes a knowledge insight node into the shared KùzuDB graph memory.
        Enables Executive Alluci to instantly recall any subagent's findings.
        """
        import uuid
        entry = HLSMEpisodicEntry(
            id=f"insight_{uuid.uuid4().hex[:8]}",
            content=f"[{agent_id.upper()} INSIGHT - {topic}]: {insight_summary}",
            source=agent_id,
            session_key=session_key,
            psi_at_encoding=0.0,
            topological_importance=1.0,
        )
        self._l1_sql_insert(entry)
        return await self.l2_store(entry)

    async def l2_delete(self, kuzu_id: str) -> bool:
        """Remove a pruned entry from KùzuDB."""
        if not self.kuzu_conn:
            return False
        try:
            query = "MATCH (m:SemanticMemory {id: $id}) DELETE m"
            await asyncio.to_thread(self.kuzu_conn.execute, query, {"id": kuzu_id})
            logger.info(f"[HLSM L2] Pruned decayed entry: {kuzu_id}")
            return True
        except Exception as e:
            logger.error(f"[HLSM L2] Delete failed for {kuzu_id}: {e}")
            return False
    # ─── L3 Knowledge Graph ───────────────────────────────────────────────────

    async def l3_store(self, entry: HLSMEpisodicEntry) -> Optional[str]:
        """
        Promote an L2 entry to L3 Knowledge Graph.
        Extracts semantic triplets using Executive Core and weights edges via Topological Barcode.
        """
        if not self.kuzu_conn:
            logger.debug("[HLSM L3] KùzuDB not available — skipping L3 promotion")
            return None

        from backend import services
        import json
        
        # 1. Prompt Executive Core for Triplets
        prompt = (
            "Extract semantic triplets (Subject, Predicate, Object) from the following text.\n"
            "Return ONLY a valid JSON array of arrays, e.g., [[\"User\", \"prefers\", \"dark mode\"]].\n\n"
            f"Text: {entry.content}"
        )
        try:
            if services.router is None:
                logger.warning("[HLSM L3] Router is not initialized. Skipping L3 promotion.")
                return None
            response = await services.router.get_response(prompt=prompt)
            # Find the JSON array in the response
            text = response.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].strip()
            triplets = json.loads(text)
        except Exception as e:
            logger.error(f"[HLSM L3] Triplet extraction failed: {e}")
            return None

        # 2. Get Topological Weight
        betti_weight = entry.topological_importance if entry.topological_importance else 1.0

        # 3. Insert into KuzuDB
        try:
            kuzu_id = f"l3_{entry.id}"
            for subject, predicate, obj in triplets:
                s_name = str(subject).replace('"', '').replace("'", "")
                o_name = str(obj).replace('"', '').replace("'", "")
                p_type = str(predicate).upper().replace(" ", "_").replace("-", "_")
                
                query = (
                    "MERGE (s:GraphNode {name: $s_name}) "
                    "MERGE (o:GraphNode {name: $o_name}) "
                    f"MERGE (s)-[r:RELATES_TO {{predicate: $p_type, source_memory: $l1_id, weight: $weight}}]->(o)"
                )
                await asyncio.to_thread(self.kuzu_conn.execute, query, {
                    "s_name": s_name, 
                    "o_name": o_name, 
                    "p_type": p_type,
                    "l1_id": entry.id,
                    "weight": betti_weight
                })
            
            meta_query = (
                "MERGE (m:L3Memory {id: $id}) "
                "SET m.content = $content, m.source = $source, m.l1_id = $l1_id, m.created_at = $created_at"
            )
            await asyncio.to_thread(self.kuzu_conn.execute, meta_query, {
                "id": kuzu_id,
                "content": json.dumps(triplets),
                "source": entry.source or "",
                "l1_id": entry.id,
                "session_key": entry.session_key or "",
                "created_at": time.time()
            })
            
            logger.info(f"[HLSM L3] Promoted L2→L3: {entry.id[:8]} → {len(triplets)} triplets")
            return kuzu_id
        except Exception as e:
            logger.error(f"[HLSM L3] KùzuDB store failed: {e}", exc_info=True)
            return None

    async def l3_search(self, query: str, limit: int = 10) -> List[HLSMRetrievalResult]:
        """Search L3 Knowledge Graph nodes."""
        if not self.kuzu_conn:
            return []
        try:
            # Fallback search on L3Memory content for simple retrieval
            cypher_query = (
                "MATCH (m:L3Memory) "
                "RETURN m.id, m.content, m.source, m.l1_id, m.created_at "
                "LIMIT $limit"
            )
            raw_results = await asyncio.to_thread(self.kuzu_conn.execute, cypher_query, {"limit": limit})
            results = []
            while raw_results.has_next():
                row = raw_results.get_next()
                kuzu_id, content, source, l1_id, created_at = row
                results.append(HLSMRetrievalResult(
                    id=kuzu_id,
                    content=content,
                    tier=3,
                    source=source,
                    relevance_score=1.0,
                    retention_score=1.0,
                ))
            return results
        except Exception as e:
            logger.error(f"[HLSM L3] Search failed: {e}")
            return []

    async def l3_delete(self, kuzu_id: str) -> bool:
        """Remove L3 entry and its edges."""
        if not self.kuzu_conn:
            return False
        try:
            # First get the l1_id from the L3Memory node
            get_query = "MATCH (m:L3Memory {id: $id}) RETURN m.l1_id"
            raw_results = await asyncio.to_thread(self.kuzu_conn.execute, get_query, {"id": kuzu_id})
            if raw_results.has_next():
                l1_id = raw_results.get_next()[0]
                # Delete relationships that were sourced from this memory
                rel_query = "MATCH ()-[r:RELATES_TO {source_memory: $l1_id}]->() DELETE r"
                await asyncio.to_thread(self.kuzu_conn.execute, rel_query, {"l1_id": l1_id})
                
            query = "MATCH (m:L3Memory {id: $id}) DELETE m"
            await asyncio.to_thread(self.kuzu_conn.execute, query, {"id": kuzu_id})
            logger.info(f"[HLSM L3] Pruned decayed entry: {kuzu_id}")
            return True
        except Exception as e:
            logger.error(f"[HLSM L3] Delete failed for {kuzu_id}: {e}")
            return False

    async def delete(self, entry_id: str) -> bool:
        """
        Unified deletion for memory entries across all tiers (L0, L1, L2, L3).
        """
        deleted = False
        base_id = entry_id
        if base_id.startswith("l2_") or base_id.startswith("l3_") or base_id.startswith("l0_"):
            base_id = base_id[3:]

        # 0. Delete from L0 SQL database (Working Memory)
        def _delete_l0():
            with Session(self.db_engine) as session:
                w_entry = session.get(HLSMWorkingEntry, base_id)
                if w_entry:
                    session.delete(w_entry)
                    session.commit()
                    return True
                return False

        try:
            if await asyncio.to_thread(_delete_l0):
                deleted = True
                logger.info(f"[HLSM] Deleted L0 working memory entry: {base_id}")
        except Exception as e:
            logger.error(f"[HLSM] L0 delete error: {e}")

        # 1. Delete from L1 SQL database (Episodic Memory)
        def _delete_l1():
            with Session(self.db_engine) as session:
                from sqlalchemy import text as sa_text
                entry = session.get(HLSMEpisodicEntry, base_id)
                if entry:
                    session.delete(entry)
                    try:
                        session.exec(sa_text("DELETE FROM hlsm_episodic_fts WHERE id = :id").bindparams(id=base_id))  # type: ignore
                    except Exception:
                        pass
                    session.commit()
                    return True
                return False

        try:
            if await asyncio.to_thread(_delete_l1):
                deleted = True
                logger.info(f"[HLSM] Deleted L1 episodic entry: {base_id}")
        except Exception as e:
            logger.error(f"[HLSM] L1 delete error: {e}")

        # 2. Delete from KùzuDB (L2 Semantic / L3 Graph)
        if self.kuzu_conn:
            try:
                q2 = "MATCH (m:SemanticMemory) WHERE m.id = $id OR m.l1_id = $id DELETE m"
                await asyncio.to_thread(self.kuzu_conn.execute, q2, {"id": entry_id})
                await asyncio.to_thread(self.kuzu_conn.execute, q2, {"id": base_id})

                await self.l3_delete(entry_id)
                await self.l3_delete(base_id)
                deleted = True
            except Exception as e:
                logger.debug(f"[HLSM] KùzuDB delete error: {e}")

        return True

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
                for result in l1_results + l2_results:  # type: ignore
                    result.relevance_score = max(0.0, min(1.0,
                        kernel.apply(result.relevance_score, affect_state)
                    ))
            except Exception as e:
                logger.debug(f"[HLSM] Affective modulation skipped: {e}")

        # Sort each tier by relevance
        l1_results.sort(key=lambda r: r.relevance_score, reverse=True)  # type: ignore
        l2_results.sort(key=lambda r: r.relevance_score, reverse=True)  # type: ignore

        # Build context, respecting token budget
        ctx = HLSMContext(
            working_memories=l0_results[:max_per_tier],  # type: ignore
            episodic_memories=l1_results[:max_per_tier],  # type: ignore
            semantic_memories=l2_results[:max_per_tier],  # type: ignore
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

    async def encode_self_healing_delta(
        self,
        objective: str,
        failed_plan: List[Dict[str, Any]],
        successful_plan: List[Dict[str, Any]],
        error_reason: str,
        session_key: str = ""
    ) -> str:
        """
        Extracts and stores the Delta between a hallucinated/failed plan and a successful self-healed plan.
        This provides crucial training data for the Nightly Dreaming Cycle and LoRA Forge.
        """
        content = (
            f"[SELF-HEALING RESOLUTION] Objective: {objective[:150]}\n"
            f"Error Caught: {error_reason}\n"
            f"Failed Topology Nodes: {len(failed_plan)}\n"
            f"Healed Topology Nodes: {len(successful_plan)}\n"
            f"Delta applied to achieve mathematical soundness."
        )
        
        # We store the raw JSON delta in extra_metadata for the LoRA Forge
        extra_metadata = {
            "type": "self_healing_delta",
            "failed_plan": failed_plan,
            "successful_plan": successful_plan,
            "error": error_reason
        }

        # Store with very high topological importance so it definitely promotes to L2 Semantic Memory
        entry_id = await self.l1_store(
            content=content,
            source="self_healing_forge",
            session_key=session_key,
            objective=objective,
            psi=0.8, # Represents high cognitive effort
            valence=0.5,
            topological_importance=2.0, # Massive boost to ensure preservation
            extra_metadata=extra_metadata
        )
        
        logger.info(f"[HLSM] Encoded self-healing delta for LoRA Forge. Entry ID: {entry_id}")
        return entry_id

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
            entry = await asyncio.to_thread(self._load_l1_entry, entry_id)  # type: ignore
            if entry:
                chroma_id = await self.l2_store(entry)
                if chroma_id:
                    await asyncio.to_thread(self._mark_l1_promoted, entry_id)
                    summary["promoted"] += 1

        # Prune L1
        if prune_ids:
            await asyncio.to_thread(self._prune_l1_entries, prune_ids)
            summary["pruned_l1"] = len(prune_ids)

        # ── L2 Pruning (KùzuDB) ─────────────────────────────────────────────
        if self.kuzu_conn:
            try:
                cypher_query = (
                    "MATCH (m:SemanticMemory) "
                    "RETURN m.id, m.created_at, m.topological_importance, m.betti_1_support"
                )
                
                raw_results = await asyncio.to_thread(
                    self.kuzu_conn.execute, 
                    cypher_query
                )
                
                while raw_results.has_next():
                    row = raw_results.get_next()
                    kuzu_id, created_at, topo_imp, betti_1 = row

                    retention = self.decay.calculate_retention(
                        last_accessed=created_at,
                        topological_importance=topo_imp,
                        betti_1_support=betti_1,
                    )
                    
                    if self.decay.should_prune(retention, L2_PRUNE_THRESHOLD):
                        await self.l2_delete(kuzu_id)
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
            return session.exec(select(HLSMEpisodicEntry)).all()  # type: ignore

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
        l3_count = 0

        if self.kuzu_conn:
            try:
                raw_results = await asyncio.to_thread(self.kuzu_conn.execute, "MATCH (n:SemanticMemory) RETURN COUNT(n)")
                if raw_results.has_next():
                    l2_count = raw_results.get_next()[0]
                
                raw_results_l3 = await asyncio.to_thread(self.kuzu_conn.execute, "MATCH (n:L3Memory) RETURN COUNT(n)")
                if raw_results_l3.has_next():
                    l3_count = raw_results_l3.get_next()[0]
            except Exception:
                l2_count = -1
                l3_count = -1

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
                    "backend": "KùzuDB" if self.kuzu_conn else "disabled",
                    "entries": l2_count,
                    "prune_threshold": L2_PRUNE_THRESHOLD,
                },
                "L3_knowledge_graph": {
                    "backend": "KùzuDB" if self.kuzu_conn else "disabled",
                    "entries": l3_count if self.kuzu_conn else 0,
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

    async def store(self, content: str, metadata: Dict[str, Any] = None, session_key: str = "") -> str:  # type: ignore
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

    async def list_entries(self, limit: int = 50, offset: int = 0, tier: Optional[int] = None) -> Dict:
        """Unified fetch across specified tier or all tiers."""
        import json
        entries = []
        total = 0
        
        if tier == 0:
            entries = await asyncio.to_thread(self._l0_paginate_sql, limit, offset)
            total = await asyncio.to_thread(self._count_l0_sql)
            formatted = [
                {"id": e.id, "content": e.content, "source": e.source, "tier": 0, "created_at": e.created_at, "extra_metadata": None, "promoted_to_l2": False}
                for e in entries
            ]
        elif tier == 1:
            entries = await asyncio.to_thread(self._l1_paginate, limit, offset)
            total = await asyncio.to_thread(self._count_l1)
            formatted = [
                {"id": e.id, "content": e.content, "source": e.source, "tier": 1, "access_count": e.access_count, "retention_score": e.retention_score, "created_at": e.created_at, "promoted_to_l2": e.promoted_to_l2, "promoted_to_l3": getattr(e, 'promoted_to_l3', False), "extra_metadata": json.dumps(e.extra_metadata) if e.extra_metadata else None}
                for e in entries
            ]
        elif tier == 2:
            if not self.kuzu_conn:
                formatted = []
            else:
                query = "MATCH (m:SemanticMemory) RETURN m.id, m.content, m.source, m.created_at SKIP $offset LIMIT $limit"
                count_query = "MATCH (m:SemanticMemory) RETURN COUNT(m)"
                raw_results = await asyncio.to_thread(self.kuzu_conn.execute, query, {"offset": offset, "limit": limit})
                raw_count = await asyncio.to_thread(self.kuzu_conn.execute, count_query)
                total = raw_count.get_next()[0] if raw_count.has_next() else 0
                formatted = []
                while raw_results.has_next():
                    row = raw_results.get_next()
                    formatted.append({"id": row[0], "content": row[1], "source": row[2], "tier": 2, "created_at": row[3], "promoted_to_l2": True})
        elif tier == 3:
            if not self.kuzu_conn:
                formatted = []
            else:
                query = "MATCH (m:L3Memory) RETURN m.id, m.content, m.source, m.created_at SKIP $offset LIMIT $limit"
                count_query = "MATCH (m:L3Memory) RETURN COUNT(m)"
                raw_results = await asyncio.to_thread(self.kuzu_conn.execute, query, {"offset": offset, "limit": limit})
                raw_count = await asyncio.to_thread(self.kuzu_conn.execute, count_query)
                total = raw_count.get_next()[0] if raw_count.has_next() else 0
                formatted = []
                while raw_results.has_next():
                    row = raw_results.get_next()
                    formatted.append({"id": row[0], "content": row[1], "source": row[2], "tier": 3, "created_at": row[3], "promoted_to_l3": True})
        else:
            # Fallback for all
            entries = await asyncio.to_thread(self._l1_paginate, limit, offset)
            total = await asyncio.to_thread(self._count_l1)
            formatted = [
                {"id": e.id, "content": e.content, "source": e.source, "tier": 1, "access_count": e.access_count, "retention_score": e.retention_score, "created_at": e.created_at, "promoted_to_l2": e.promoted_to_l2, "promoted_to_l3": getattr(e, 'promoted_to_l3', False), "extra_metadata": json.dumps(e.extra_metadata) if e.extra_metadata else None}
                for e in entries
            ]

        return {
            "entries": formatted,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _l0_paginate_sql(self, limit: int, offset: int) -> List[HLSMWorkingEntry]:
        with Session(self.db_engine) as session:
            return session.exec(  # type: ignore
                select(HLSMWorkingEntry)
                .order_by(col(HLSMWorkingEntry.created_at).desc())
                .offset(offset)
                .limit(limit)
            ).all()

    def _l1_paginate(self, limit: int, offset: int) -> List[HLSMEpisodicEntry]:
        with Session(self.db_engine) as session:
            return session.exec(  # type: ignore
                select(HLSMEpisodicEntry)
                .order_by(col(HLSMEpisodicEntry.created_at).desc())
                .offset(offset)
                .limit(limit)
            ).all()

    async def _l0_delete_by_id(self, memory_id: str) -> bool:
        if self.redis:
            try:
                keys = await self.redis.keys("hlsm:working:*")
                for key in keys:
                    items = await self.redis.lrange(key, 0, -1)
                    for item in items:
                        try:
                            data = json.loads(item)
                            if data.get("id") == memory_id:
                                await self.redis.lrem(key, 1, item)
                                return True
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                logger.error(f"[HLSM L0] Redis delete failed: {e}")
        # SQL fallback
        return await asyncio.to_thread(self._l0_sql_delete_by_id, memory_id)

    def _l0_sql_delete_by_id(self, memory_id: str) -> bool:
        with Session(self.db_engine) as session:
            entry = session.get(HLSMWorkingEntry, memory_id)
            if entry:
                session.delete(entry)
                session.commit()
                return True
        return False


    def _l1_delete_by_id(self, memory_id: str) -> bool:
        with Session(self.db_engine) as session:
            entry = session.get(HLSMEpisodicEntry, memory_id)
            if entry:
                session.delete(entry)
                session.commit()
                return True
        return False
