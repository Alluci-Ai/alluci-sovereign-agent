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
import numpy as np
from .markov_trace import MarkovTraceEngine

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

    def handle_data(self, data: str):
        if not self.ignore:
            self.text.append(data)

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

def _extract_kuzu_rows(raw_results: Any) -> List[Any]:
    """Safely extract rows from KùzuDB QueryResult, Python list, tuple, or generic iterable."""
    if raw_results is None:
        return []
    if isinstance(raw_results, (list, tuple)):
        return list(raw_results)
    if hasattr(raw_results, "has_next") and callable(getattr(raw_results, "has_next")):
        rows = []
        while raw_results.has_next():
            rows.append(raw_results.get_next())
        return rows
    if hasattr(raw_results, "__iter__"):
        return list(raw_results)
    return []


def _distill_document_metadata(filename: str, content: str) -> Dict[str, Any]:
    """
    Fast, deterministic single-pass distillation of document structure:
    Extracts title, 3-5 core key points, and domain acronym definitions.
    """
    clean_lines = [line.strip() for line in content.split("\n") if line.strip()]
    if not clean_lines:
        return {"title": filename, "summary": "", "key_points": [], "acronyms": ""}
    
    # 1. Title extraction
    title = clean_lines[0].lstrip("#").strip()
    if len(title) > 120 or len(title) < 4:
        title = filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
    
    # 2. Acronym & definition extraction (e.g. "CIMC (California Institute for Machine Consciousness)" or "CIMC: ...")
    acronym_map: Dict[str, str] = {}
    
    # Pattern A: Full Name (ACRONYM) or ACRONYM (Full Name)
    matches_paren = re.findall(r'\b([A-Z][A-Za-z0-9\s&]{3,60})\s*\(([A-Z0-9]{2,10})\)|\b([A-Z0-9]{2,10})\s*\(([A-Z][A-Za-z0-9\s&]{3,60})\)', content)
    for m in matches_paren:
        if m[0] and m[1]:
            full, acr = m[0].strip(), m[1].strip()
            if len(acr) <= 8 and acr.isupper():
                acronym_map[acr] = full
        elif m[2] and m[3]:
            acr, full = m[2].strip(), m[3].strip()
            if len(acr) <= 8 and acr.isupper():
                acronym_map[acr] = full

    # Pattern B: Colon definition e.g. CIMC: California Institute for Machine Consciousness
    matches_colon = re.findall(r'\b([A-Z0-9]{2,10})\s*:\s*([A-Z][A-Za-z0-9\s&]{4,60})', content)
    for acr, full in matches_colon:
        if len(acr) <= 8 and acr.isupper() and acr not in acronym_map:
            acronym_map[acr] = full.strip()

    # Pattern C: Acronym from filename or title if first letters match (e.g. CIMC -> California Institute for Machine Consciousness)
    title_words = [w for w in title.split() if w and w[0].isupper()]
    if len(title_words) >= 2:
        constructed_acr = "".join(w[0] for w in title_words if w.lower() not in {"for", "the", "and", "of", "in", "to", "a"})
        if len(constructed_acr) >= 2 and constructed_acr not in acronym_map:
            acronym_map[constructed_acr] = title

    acronyms_str = ", ".join(f"{k}: {v}" for k, v in acronym_map.items())

    # 3. Key Points extraction (take informative paragraphs or bullet items)
    key_points = []
    for line in clean_lines[1:30]:
        if line.startswith(("-", "•", "*", "1.", "2.", "3.", "4.", "5.", "I.", "II.", "III.")) and len(line) > 20:
            key_points.append(line.lstrip("-•* 0123456789.IVX").strip())
        elif len(line) > 40 and not line.startswith("#") and len(key_points) < 4:
            key_points.append(line)
        if len(key_points) >= 5:
            break
            
    if not key_points and len(clean_lines) > 1:
        key_points = clean_lines[1:4]

    # 4. Summary construction
    summary_parts = []
    if title:
        summary_parts.append(f"Title: {title}.")
    if acronyms_str:
        summary_parts.append(f"Key Acronyms: {acronyms_str}.")
    if key_points:
        summary_parts.append(f"Core Points: {' | '.join(key_points[:3])}")
    summary = " ".join(summary_parts)

    return {
        "title": title,
        "summary": summary[:1200],
        "key_points": key_points[:5],
        "acronyms": acronyms_str[:500]
    }

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
    graph_memories: List[HLSMRetrievalResult] = field(default_factory=list)
    total_chars: int = 0
    total_tokens: int = 0
    spectral_metrics: Optional[Dict[str, Any]] = None

    def to_prompt_block(self) -> str:
        """
        Renders the H-LSM context as a structured prompt block.
        Sections are ordered by relevance and tier priority.
        """
        if not (self.working_memories or self.episodic_memories or self.semantic_memories or self.graph_memories):
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

        if self.graph_memories:
            lines.append("\n── Knowledge Graph Entities (Relational Memory) ──")
            for m in self.graph_memories[:5]:
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
                    "CREATE NODE TABLE IF NOT EXISTS DocumentNode (id STRING, name STRING, title STRING, sha256 STRING, local_path STRING, mime_type STRING, summary STRING, acronyms STRING, created_at DOUBLE, session_key STRING, access_count INT64, PRIMARY KEY (id))"
                )
                self.kuzu_conn.execute(
                    "CREATE NODE TABLE IF NOT EXISTS KeyPointNode (id STRING, text STRING, document_id STRING, PRIMARY KEY (id))"
                )
                self.kuzu_conn.execute(
                    "CREATE NODE TABLE IF NOT EXISTS GraphNode (name STRING, PRIMARY KEY (name))"
                )
                self.kuzu_conn.execute(
                    "CREATE REL TABLE IF NOT EXISTS RELATES_TO (FROM GraphNode TO GraphNode, predicate STRING, source_memory STRING, weight DOUBLE)"
                )
                self.kuzu_conn.execute(
                    "CREATE REL TABLE IF NOT EXISTS HAS_KEY_POINT (FROM DocumentNode TO KeyPointNode)"
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
        
        # Markov Trace & Spectral Geometry Engine (PPN Trace Logic)
        self.trace_engine = MarkovTraceEngine()

        # Deep 4-Tier Memory Auditor & Deduplication Engine
        from .hlsm_auditor import HLSMDeepAuditor
        from .hlsm_deduplicator import HLSMDeduplicator
        self.auditor = HLSMDeepAuditor(db_engine=self.db_engine, kuzu_conn=self.kuzu_conn)
        self.deduplicator = HLSMDeduplicator(db_engine=self.db_engine, kuzu_conn=self.kuzu_conn)

        logger.info(
            "[HLSM] Initialized. "
            f"L0={'Redis' if redis_client else 'SQL-fallback'}, "
            f"L1=SQL, "
            f"L2={'KùzuDB' if self.kuzu_conn else 'disabled'}, "
            "Trace=MarkovEngine, "
            "Auditor=Active, Deduplicator=Active"
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

    def _compute_candidate_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Generates vector representations for memory candidates to compute Markov Trace affinities.
        Uses sentence-transformers if available, otherwise fast deterministic hash n-grams.
        """
        if not texts:
            return np.empty((0, 128), dtype=np.float32)
        
        embed_model = self._get_embed_model()
        if embed_model is not None:
            try:
                embeddings = embed_model.encode(texts, convert_to_numpy=True)
                return embeddings
            except Exception as e:
                logger.debug(f"[HLSM Trace] Neural embedding fallback: {e}")

        # Deterministic hash n-gram embedding fallback
        dim = 128
        matrix = np.zeros((len(texts), dim), dtype=np.float32)
        for i, text in enumerate(texts):
            words = text.lower().split()
            for w in words:
                h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16) % dim
                matrix[i, h] += 1.0
            norm = np.linalg.norm(matrix[i])
            if norm > 0:
                matrix[i] /= norm
        return matrix

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
            extra_metadata=extra_metadata if extra_metadata else None,
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
            extra_metadata=payload["metadata"] if isinstance(payload.get("metadata"), dict) else None,
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
                    # Robust keyword-split fallback to standard LIKE with stop-word filtering
                    stop_words = {"the", "and", "can", "you", "all", "your", "are", "for", "with", "this", "that", "what", "how", "tell", "show", "list", "hello", "alluci", "from", "into"}
                    words = [w for w in clean_query.lower().split() if len(w) > 3 and w not in stop_words]
                    if words:
                        like_clauses = " OR ".join([f"LOWER(content) LIKE :w{i}" for i in range(len(words))])
                        params: Dict[str, Any] = {f"w{i}": f"%{w}%" for i, w in enumerate(words)}
                        params["limit"] = limit * 2
                        raw = session.exec(sa_text(  # type: ignore
                            "SELECT id, content, source, session_key, psi_at_encoding, "
                            "topological_importance, betti_1_support, access_count, "
                            "last_accessed, retention_score "
                            "FROM hlsm_episodic "
                            f"WHERE {like_clauses} "
                            "ORDER BY last_accessed DESC "
                            "LIMIT :limit"
                        ).bindparams(**params)).fetchall()
                    else:
                        raw = []
            else:
                # PostgreSQL High-Performance FTS (Native tsvector)
                raw = session.exec(sa_text(  # type: ignore
                    "SELECT id, content, source, session_key, psi_at_encoding, "
                    "topological_importance, betti_1_support, access_count, "
                    "last_accessed, retention_score "
                    "FROM hlsm_episodic "
                    "WHERE to_tsvector('english', content) @@ plainto_tsquery('english', :q) "
                    "ORDER BY last_accessed DESC "
                    "LIMIT :limit"
                ).bindparams(q=query, limit=limit)).fetchall()

            stop_words = {"the", "and", "can", "you", "all", "your", "are", "for", "with", "this", "that", "what", "how", "tell", "show", "list", "hello", "alluci", "from", "into"}
            query_words = set(clean_query.lower().split()) - stop_words

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

                # Calculate lexical overlap relevance score
                content_words = set(str(content).lower().split())
                if query_words:
                    overlap = len(query_words & content_words)
                    lexical_relevance = overlap / len(query_words)
                else:
                    lexical_relevance = 0.5

                if lexical_relevance < 0.15:
                    continue

                combined_relevance = lexical_relevance * retention
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
            
            extra: Dict[str, Any] = {}
            if isinstance(entry.extra_metadata, str):
                try:
                    parsed = json.loads(entry.extra_metadata)
                    if isinstance(parsed, dict):
                        extra = parsed
                except Exception:
                    extra = {}
            elif isinstance(entry.extra_metadata, dict):
                extra = entry.extra_metadata
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
            
            rows = _extract_kuzu_rows(raw_results)
            for row in rows:
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
        """
        Search L3 Knowledge Graph nodes, including DocumentNode, KeyPointNode, and L3Memory entities.
        """
        if not self.kuzu_conn:
            return []
        try:
            results = []
            seen_ids = set()
            clean_q = query.strip().lower()
            search_terms = [t for t in re.split(r'[\s_\-\.\(\)]+', clean_q) if len(t) > 2]

            # 1. Match DocumentNode entities by title, acronyms, name, or summary
            try:
                doc_query = (
                    "MATCH (d:DocumentNode) "
                    "RETURN d.id, d.name, d.title, d.summary, d.acronyms, d.local_path, d.created_at "
                    "LIMIT 50"
                )
                raw_docs = await asyncio.to_thread(self.kuzu_conn.execute, doc_query)
                doc_rows = _extract_kuzu_rows(raw_docs)
                for row in doc_rows:
                    d_id, d_name, d_title, d_summary, d_acronyms, d_path, d_created = row
                    d_text = f"{d_name} {d_title} {d_summary} {d_acronyms}".lower()
                    
                    # Check for direct substring or token overlap
                    match_score = 0.0
                    if clean_q in d_text:
                        match_score = 1.5
                    elif search_terms:
                        matches = sum(1 for t in search_terms if t in d_text)
                        match_score = (matches / len(search_terms)) * 1.3 if matches > 0 else 0.0

                    if match_score >= 0.3:
                        kp_lines = []
                        try:
                            kp_query = "MATCH (d:DocumentNode {id: $id})-[:HAS_KEY_POINT]->(k:KeyPointNode) RETURN k.text LIMIT 5"
                            raw_kp = await asyncio.to_thread(self.kuzu_conn.execute, kp_query, {"id": d_id})
                            kp_rows = _extract_kuzu_rows(raw_kp)
                            for kp in kp_rows:
                                kp_lines.append(f"  • {kp[0]}")
                        except Exception:
                            pass

                        kp_section = f"\nKey Theses & Core Points:\n" + "\n".join(kp_lines) if kp_lines else ""
                        doc_content = (
                            f"[GROUNDED DOCUMENT PROVENANCE: {d_title} (`{d_name}`) | Acronyms: {d_acronyms} | Path: {d_path}]\n"
                            f"Executive Summary: {d_summary}{kp_section}"
                        )
                        seen_ids.add(d_id)
                        results.append(HLSMRetrievalResult(
                            id=d_id,
                            content=doc_content,
                            tier=3,
                            source="document_provenance",
                            relevance_score=min(1.5, match_score * 1.4),
                            retention_score=1.0,
                        ))
            except Exception as doc_err:
                logger.debug(f"[HLSM L3] DocumentNode query notice: {doc_err}")

            # 2. General L3Memory search
            cypher_query = (
                "MATCH (m:L3Memory) "
                "RETURN m.id, m.content, m.source, m.l1_id, m.created_at "
                "LIMIT $limit"
            )
            raw_results = await asyncio.to_thread(self.kuzu_conn.execute, cypher_query, {"limit": limit})
            rows = _extract_kuzu_rows(raw_results)
            for row in rows:
                kuzu_id, content, source, l1_id, created_at = row
                if kuzu_id not in seen_ids:
                    seen_ids.add(kuzu_id)
                    results.append(HLSMRetrievalResult(
                        id=kuzu_id,
                        content=content,
                        tier=3,
                        source=source,
                        relevance_score=1.0,
                        retention_score=1.0,
                    ))

            results.sort(key=lambda r: r.relevance_score, reverse=True)
            return results[:limit]
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
            rows = _extract_kuzu_rows(raw_results)
            if rows:
                l1_id = rows[0][0]
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
        if base_id.startswith("l0_") or base_id.startswith("l1_") or base_id.startswith("l2_") or base_id.startswith("l3_"):
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

        # Parallel retrieval across all 4 tiers (L0 Working, L1 FTS5, L2 Semantic, L3 Knowledge Graph)
        l0_results, l1_results, l2_results, l3_results = await asyncio.gather(
            self.l0_retrieve(session_key),
            self.l1_search(search_query, limit=max_per_tier * 2),
            self.l2_search(search_query, limit=max_per_tier * 2),
            self.l3_search(search_query, limit=max_per_tier * 2),
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
        if isinstance(l3_results, Exception):
            logger.error(f"[HLSM] L3 retrieval failed: {l3_results}")
            l3_results = []

        # Tri-Hybrid Reciprocal Rank Fusion (RRF)
        # Combines L1 (Exact FTS5), L2 (Dense Semantic Vectors), and L3 (KùzuDB Graph Entities)
        k_rrf = 60
        tier_weights = {"L1": 1.0, "L2": 1.2, "L3": 1.4}
        rrf_scores: Dict[str, float] = {}
        item_registry: Dict[str, HLSMRetrievalResult] = {}

        for tier_name, tier_items in [("L1", l1_results), ("L2", l2_results), ("L3", l3_results)]:
            if isinstance(tier_items, list):
                for rank, item in enumerate(tier_items):
                    doc_key = item.id or item.content[:100]
                    item_registry[doc_key] = item
                    rrf_scores[doc_key] = rrf_scores.get(doc_key, 0.0) + (tier_weights[tier_name] / (k_rrf + rank + 1))

        # Assign normalized RRF relevance score
        for doc_key, rrf_val in rrf_scores.items():
            if doc_key in item_registry:
                item_registry[doc_key].relevance_score = max(item_registry[doc_key].relevance_score, rrf_val * 100.0)

        # Apply affective modulation to L1, L2, L3 scores
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
                for result in l1_results + l2_results + l3_results:  # type: ignore
                    result.relevance_score = max(0.0, min(1.0,
                        kernel.apply(result.relevance_score, affect_state)
                    ))
            except Exception as e:
                logger.debug(f"[HLSM] Affective modulation skipped: {e}")

        # Markov Trace Multi-Hop Rescoring & Spectral Context Scaling
        all_candidates = l1_results + l2_results + l3_results  # type: ignore
        spectral_metrics = None

        if len(all_candidates) >= 3:
            try:
                texts = [m.content for m in all_candidates]
                direct_scores = [m.relevance_score for m in all_candidates]
                embeddings = self._compute_candidate_embeddings(texts)
                rescored, spectral_metrics = self.trace_engine.rescore_with_markov_trace(
                    candidate_items=all_candidates,
                    embeddings=embeddings,
                    direct_relevance_scores=direct_scores,
                    visible_top_k=max_per_tier,
                )
                score_map = {item.id: score for item, score in rescored}
                for r in all_candidates:
                    if r.id in score_map:
                        r.relevance_score = score_map[r.id]

                # Dynamic Context Depth Scaling from Spectral Dimension
                mixing_rate = spectral_metrics.get("mixing_rate", "nominal")
                spectral_dim = spectral_metrics.get("spectral_dimension", 1.0)
                if mixing_rate == "sparse" or spectral_dim > 1.5:
                    max_per_tier = min(max_per_tier + 2, 8)
            except Exception as trace_err:
                logger.debug(f"[HLSM] Markov trace rescoring skipped: {trace_err}")

        # Sort each tier by relevance
        l1_results.sort(key=lambda r: r.relevance_score, reverse=True)  # type: ignore
        l2_results.sort(key=lambda r: r.relevance_score, reverse=True)  # type: ignore
        l3_results.sort(key=lambda r: r.relevance_score, reverse=True)  # type: ignore

        # Gated Relevance Cutoff: Only memories with genuine query relevance are admitted to working context
        RELEVANCE_FLOOR = 0.35
        filtered_l1 = [m for m in l1_results if getattr(m, 'relevance_score', 0.0) >= RELEVANCE_FLOOR]  # type: ignore
        filtered_l2 = [m for m in l2_results if getattr(m, 'relevance_score', 0.0) >= RELEVANCE_FLOOR]  # type: ignore
        filtered_l3 = [m for m in l3_results if getattr(m, 'relevance_score', 0.0) >= RELEVANCE_FLOOR]  # type: ignore

        # Build context, respecting token budget
        ctx = HLSMContext(
            working_memories=l0_results[:max_per_tier],  # type: ignore
            episodic_memories=filtered_l1[:max_per_tier],
            semantic_memories=filtered_l2[:max_per_tier],
            graph_memories=filtered_l3[:max_per_tier],
            spectral_metrics=spectral_metrics,
        )
        prompt = ctx.to_prompt_block()
        ctx.total_chars = len(prompt)
        ctx.total_tokens = self._get_token_count(prompt)

        logger.info(
            f"[HLSM] Retrieved (Tri-Hybrid RRF): L0={len(ctx.working_memories)}, "
            f"L1={len(ctx.episodic_memories)}, "
            f"L2={len(ctx.semantic_memories)}, "
            f"L3={len(ctx.graph_memories)} "
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

        # ── L1 Promotion and Pruning with Topological Barcode Persistence ─────
        l1_entries = await asyncio.to_thread(self._load_all_l1_for_consolidation)
        now = time.time()

        from .. import services
        clock = getattr(services, "barcode_clock", None)

        promote_ids: List[str] = []
        prune_ids: List[str] = []

        for entry in l1_entries:
            retention = self.decay.calculate_retention(
                last_accessed=entry.last_accessed,
                topological_importance=entry.topological_importance,
                betti_1_support=entry.betti_1_support,
            )

            # Check if entry has high topological persistence in Barcode Clock
            barcode_persistence = clock.get_persistence(entry.id) if clock else None
            is_persistently_anchored = barcode_persistence is not None and barcode_persistence > 10

            if self.decay.should_prune(retention, L1_PRUNE_THRESHOLD) and not is_persistently_anchored:
                prune_ids.append(entry.id)
            elif (
                not entry.promoted_to_l2
                and (
                    (entry.access_count >= PROMOTION_ACCESS_COUNT and retention >= PROMOTION_RETENTION_MIN)
                    or is_persistently_anchored
                )
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
                
                rows = _extract_kuzu_rows(raw_results)
                for row in rows:
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

        # ── 4-Tier Memory Deduplication & Orphan GC Sweep ─────────────────────
        try:
            dedup_res = await self.deduplicate(dry_run=False)
            deleted_recs = dedup_res.get("deleted_records", {})
            summary["deduplicated_l0"] = deleted_recs.get("l0_working", 0)
            summary["deduplicated_l1"] = deleted_recs.get("l1_episodic", 0)
            summary["deduplicated_l3"] = deleted_recs.get("l3_graph", 0)
            summary["freed_bytes"] = dedup_res.get("freed_bytes_total", 0)
            summary["health_score"] = dedup_res.get("health_score_after", 1.0)

            from ..metrics import HLSM_HEALTH_SCORE, HLSM_DUPLICATE_CLUSTERS, HLSM_SELF_HEALING_TOTAL
            HLSM_HEALTH_SCORE.set(dedup_res.get("health_score_after", 1.0))
            HLSM_DUPLICATE_CLUSTERS.set(dedup_res.get("remaining_duplicates", 0))
            if dedup_res.get("freed_bytes_total", 0) > 0:
                HLSM_SELF_HEALING_TOTAL.inc()
        except Exception as dedup_err:
            logger.debug(f"[HLSM] Consolidation deduplication notice: {dedup_err}")

        logger.info(
            f"[HLSM] Consolidation complete: "
            f"promoted={summary['promoted']}, "
            f"pruned_l1={summary['pruned_l1']}, "
            f"pruned_l2={summary['pruned_l2']}, "
            f"pruned_l0={summary['pruned_l0']}, "
            f"dedup_freed_bytes={summary.get('freed_bytes', 0)}, "
            f"health_score={summary.get('health_score', 1.0)}"
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
                l2_rows = _extract_kuzu_rows(raw_results)
                if l2_rows:
                    l2_count = l2_rows[0][0]
                
                raw_results_l3 = await asyncio.to_thread(self.kuzu_conn.execute, "MATCH (n:L3Memory) RETURN COUNT(n)")
                l3_rows = _extract_kuzu_rows(raw_results_l3)
                if l3_rows:
                    l3_count = l3_rows[0][0]
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
                count_rows = _extract_kuzu_rows(raw_count)
                total = count_rows[0][0] if count_rows else 0
                formatted = []
                for row in _extract_kuzu_rows(raw_results):
                    formatted.append({"id": row[0], "content": row[1], "source": row[2], "tier": 2, "created_at": row[3], "promoted_to_l2": True})
        elif tier == 3:
            if not self.kuzu_conn:
                formatted = []
            else:
                query = "MATCH (m:L3Memory) RETURN m.id, m.content, m.source, m.created_at SKIP $offset LIMIT $limit"
                count_query = "MATCH (m:L3Memory) RETURN COUNT(m)"
                raw_results = await asyncio.to_thread(self.kuzu_conn.execute, query, {"offset": offset, "limit": limit})
                raw_count = await asyncio.to_thread(self.kuzu_conn.execute, count_query)
                count_rows = _extract_kuzu_rows(raw_count)
                total = count_rows[0][0] if count_rows else 0
                formatted = []
                for row in _extract_kuzu_rows(raw_results):
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

    async def ingest_distilled_intent(
        self,
        session_key: str,
        message_id: str,
        prompt: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Distills the core intent, objective, and entities from a chat turn and indexes them into
        L2 Semantic Memory and L3 KùzuDB Graph Memory, with DB pointers (session_key & message_id)
        back to the primary message_log table.
        """
        if not prompt and not response:
            return None

        clean_prompt = _sanitize_hlsm_text(prompt)
        clean_resp = _sanitize_hlsm_text(response[:500])
        distilled_content = f"INTENT OBJECTIVE: {clean_prompt}\nSUMMARY OUTCOME: {clean_resp}"

        entry_id = f"mem_intent_{uuid.uuid4().hex[:12]}"
        now = time.time()

        if self.kuzu_conn:
            try:
                query = (
                    "CREATE (m:SemanticMemory {"
                    "id: $id, content: $content, source: 'distilled_intent', session_key: $session_key, "
                    "psi_at_encoding: 0.0, topological_importance: 1.0, betti_1_support: 0.0, "
                    "betti_signature: '', access_count: 1, created_at: $created_at, l1_id: $message_id, "
                    "is_barcode: false, uri: $uri, blob_path: '', ttl: 0.0"
                    "})"
                )
                await asyncio.to_thread(
                    self.kuzu_conn.execute,
                    query,
                    {
                        "id": entry_id,
                        "content": distilled_content[:1500],
                        "session_key": session_key or "",
                        "created_at": now,
                        "message_id": message_id or "",
                        "uri": f"message_log:{message_id}"
                    }
                )
                logger.info(f"[HLSM] Distilled chat intent stored into L2 Semantic Memory (ID: {entry_id}, pointer: message_log:{message_id})")
            except Exception as e:
                logger.warning(f"[HLSM] L2 Semantic Memory store failed: {e}")

        try:
            words = [w.strip(".,!?\"'") for w in clean_prompt.split() if len(w) > 4 and w.isalnum()]
            key_entities = list(set(words))[:3]
            if key_entities and self.kuzu_conn:
                for entity in key_entities:
                    node_q = "MERGE (g:GraphNode {name: $name})"
                    await asyncio.to_thread(self.kuzu_conn.execute, node_q, {"name": entity.capitalize()})
                if len(key_entities) >= 2:
                    rel_q = (
                        "MATCH (a:GraphNode {name: $source}), (b:GraphNode {name: $target}) "
                        "MERGE (a)-[r:RELATES_TO {predicate: 'CO_OCCURS_IN_INTENT', source_memory: $mem_id, weight: 1.0}]->(b)"
                    )
                    await asyncio.to_thread(
                        self.kuzu_conn.execute,
                        rel_q,
                        {"source": key_entities[0].capitalize(), "target": key_entities[1].capitalize(), "mem_id": entry_id}
                    )
        except Exception as graph_err:
            logger.debug(f"[HLSM] L3 Graph entity extraction notice: {graph_err}")

        return entry_id

    async def ingest_document_payload(
        self,
        filename: str,
        content: str,
        session_key: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Asynchronously fingerprints, deduplicates (CAS), and indexes an uploaded document into
        L1 Episodic (FTS5), L2 Semantic Memory, and L3 Knowledge Graph with DocumentNode & KeyPointNode.
        """
        if not content or not content.strip():
            return []

        clean_text = _sanitize_hlsm_text(content)
        meta = metadata or {}
        now = time.time()
        
        # 1. Content-Addressable Cryptographic SHA-256 Fingerprint
        doc_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
        doc_node_id = f"doc_{doc_sha256[:16]}"
        local_path = meta.get("file_path", "") or f"workspace/uploads/{filename}"
        mime_type = meta.get("mime_type", "") or "application/octet-stream"

        # 2. Check for Duplicate Document in KùzuDB (Zero-Storage Bloat Law)
        if self.kuzu_conn:
            try:
                dup_check_q = "MATCH (d:DocumentNode {sha256: $sha256}) RETURN d.id, d.name, d.access_count"
                raw_dup = await asyncio.to_thread(self.kuzu_conn.execute, dup_check_q, {"sha256": doc_sha256})
                dup_rows = _extract_kuzu_rows(raw_dup)
                if dup_rows:
                    existing_id = str(dup_rows[0][0])
                    upd_q = "MATCH (d:DocumentNode {id: $id}) SET d.access_count = d.access_count + 1, d.session_key = $session_key"
                    await asyncio.to_thread(self.kuzu_conn.execute, upd_q, {"id": existing_id, "session_key": session_key or ""})
                    logger.info(f"[HLSM] Deduplication hit for '{filename}' (SHA: {doc_sha256[:8]}). Updated access count for {existing_id}.")
                    return [existing_id]
            except Exception as dup_err:
                logger.debug(f"[HLSM] Deduplication lookup notice: {dup_err}")

        # 3. Single-Pass Semantic Distillation & Acronym Extraction
        distilled = _distill_document_metadata(filename, clean_text)
        doc_title = distilled["title"]
        doc_summary = distilled["summary"]
        doc_acronyms = distilled["acronyms"]
        key_points = distilled["key_points"]

        # 4. Ingest L3 DocumentNode and KeyPointNode entities
        if self.kuzu_conn:
            try:
                # Merge DocumentNode
                create_doc_q = (
                    "MERGE (d:DocumentNode {id: $id}) "
                    "SET d.name = $name, d.title = $title, d.sha256 = $sha256, d.local_path = $local_path, "
                    "d.mime_type = $mime_type, d.summary = $summary, d.acronyms = $acronyms, "
                    "d.created_at = $created_at, d.session_key = $session_key, d.access_count = 1"
                )
                await asyncio.to_thread(self.kuzu_conn.execute, create_doc_q, {
                    "id": doc_node_id,
                    "name": filename,
                    "title": doc_title,
                    "sha256": doc_sha256,
                    "local_path": local_path,
                    "mime_type": mime_type,
                    "summary": doc_summary,
                    "acronyms": doc_acronyms,
                    "created_at": now,
                    "session_key": session_key or "",
                })

                # Merge KeyPointNodes & HAS_KEY_POINT relations
                for kp_idx, kp_text in enumerate(key_points):
                    kp_id = f"kp_{doc_sha256[:12]}_{kp_idx}"
                    create_kp_q = (
                        "MERGE (k:KeyPointNode {id: $id}) "
                        "SET k.text = $text, k.document_id = $doc_id"
                    )
                    await asyncio.to_thread(self.kuzu_conn.execute, create_kp_q, {
                        "id": kp_id,
                        "text": str(kp_text)[:500],
                        "doc_id": doc_node_id,
                    })
                    rel_q = (
                        "MATCH (d:DocumentNode {id: $doc_id}), (k:KeyPointNode {id: $kp_id}) "
                        "MERGE (d)-[:HAS_KEY_POINT]->(k)"
                    )
                    await asyncio.to_thread(self.kuzu_conn.execute, rel_q, {
                        "doc_id": doc_node_id,
                        "kp_id": kp_id,
                    })

                # Also insert high-level summary as an L3Memory entity
                l3_summary_id = f"l3_doc_{doc_sha256[:12]}"
                l3_doc_content = f"[DOCUMENT SUMMARY: {doc_title} ({filename}) | Acronyms: {doc_acronyms}]\n{doc_summary}"
                create_l3_q = (
                    "MERGE (m:L3Memory {id: $id}) "
                    "SET m.content = $content, m.source = 'document_ingest', m.l1_id = $filename, "
                    "m.session_key = $session_key, m.created_at = $created_at"
                )
                await asyncio.to_thread(self.kuzu_conn.execute, create_l3_q, {
                    "id": l3_summary_id,
                    "content": l3_doc_content[:1500],
                    "filename": filename,
                    "session_key": session_key or "",
                    "created_at": now,
                })
            except Exception as l3_err:
                logger.error(f"[HLSM] Failed to store DocumentNode into L3: {l3_err}", exc_info=True)

        # 5. Chunk and Ingest into L1 (FTS5 Episodic) and L2 (SemanticMemory)
        words = clean_text.split()
        chunk_size = 500
        overlap = 100
        chunks = []
        start = 0
        while start < len(words):
            chunk_words = words[start:start + chunk_size]
            chunks.append(" ".join(chunk_words))
            start += (chunk_size - overlap)

        ingested_ids = [doc_node_id]

        for idx, chunk in enumerate(chunks[:25]):
            chunk_id = f"doc_{doc_sha256[:8]}_c{idx}"
            chunk_header = f"[DOCUMENT: {filename} | Title: {doc_title} | Acronyms: {doc_acronyms} | Chunk {idx+1}/{len(chunks)}]\n{chunk}"

            # Store in L1 Episodic Memory for SQLite FTS5 instant lexical match
            try:
                l1_entry = HLSMEpisodicEntry(
                    id=chunk_id,
                    content=chunk_header,
                    source="document_ingest",
                    session_key=session_key or "",
                    psi_at_encoding=0.0,
                    topological_importance=1.2,
                    extra_metadata=json.dumps({
                        "filename": filename,
                        "title": doc_title,
                        "sha256": doc_sha256,
                        "chunk_index": idx,
                        "total_chunks": len(chunks),
                        "local_path": local_path
                    })
                )
                self._l1_sql_insert(l1_entry)
            except Exception as l1_err:
                logger.debug(f"[HLSM] L1 SQL insert notice for chunk {chunk_id}: {l1_err}")

            # Store in L2 SemanticMemory in KùzuDB
            if self.kuzu_conn:
                try:
                    betti_sig = self.dpk.get_betti_signature(self.dpk.project_state(chunk_header))
                    query = (
                        "CREATE (m:SemanticMemory {"
                        "id: $id, content: $content, source: 'document_ingest', session_key: $session_key, "
                        "psi_at_encoding: 0.0, topological_importance: 1.2, betti_1_support: 0.0, "
                        "betti_signature: $betti_signature, access_count: 1, created_at: $created_at, l1_id: $filename, "
                        "is_barcode: false, uri: $uri, blob_path: '', ttl: 0.0"
                        "})"
                    )
                    await asyncio.to_thread(
                        self.kuzu_conn.execute,
                        query,
                        {
                            "id": chunk_id,
                            "content": chunk_header[:1500],
                            "session_key": session_key or "",
                            "betti_signature": betti_sig,
                            "created_at": now,
                            "filename": filename or "",
                            "uri": f"file:{filename}:chunk_{idx}"
                        }
                    )
                    ingested_ids.append(chunk_id)
                except Exception as e:
                    logger.warning(f"[HLSM] Failed to store document chunk into L2: {e}")

        logger.info(f"[HLSM] Ingested document '{filename}' (SHA: {doc_sha256[:8]}) into L1 (FTS5), L2 (Semantic), and L3 (DocumentNode '{doc_title}').")
        return ingested_ids

    async def delete_by_pattern(self, pattern: str, session_key: Optional[str] = None) -> Dict[str, int]:
        """
        Searches all H-LSM memory tiers (L0 Working, L1 Episodic, L2 Semantic, L3 Graph) for entries
        containing matching pattern strings (e.g. '[IMESSAGE] From +1-555-0199' or a phone number)
        and permanently deletes them.
        """
        if not pattern or not pattern.strip():
            return {"deleted_l0": 0, "deleted_l1": 0, "deleted_l2": 0, "deleted_l3": 0, "total_deleted": 0}

        search_pat = pattern.strip()
        counts = {"deleted_l0": 0, "deleted_l1": 0, "deleted_l2": 0, "deleted_l3": 0, "total_deleted": 0}

        # Extract digit patterns if searching for phone numbers
        raw_digits = re.sub(r'\D', '', search_pat)
        digit_variants = []
        if len(raw_digits) >= 6:
            digit_variants.append(raw_digits)
            if len(raw_digits) > 10:
                digit_variants.append(raw_digits[-10:])

        try:
            def _purge_l1():
                from sqlalchemy import or_
                with Session(self.db_engine) as session:
                    conditions = [
                        col(HLSMEpisodicEntry.content).like(f"%{search_pat}%"),
                        col(HLSMEpisodicEntry.source).like(f"%{search_pat}%"),
                        col(HLSMEpisodicEntry.session_key).like(f"%{search_pat}%"),
                    ]
                    for d in digit_variants:
                        conditions.append(col(HLSMEpisodicEntry.content).like(f"%{d}%"))
                        conditions.append(col(HLSMEpisodicEntry.session_key).like(f"%{d}%"))

                    stmt = select(HLSMEpisodicEntry).where(or_(*conditions))
                    if session_key:
                        stmt = stmt.where(HLSMEpisodicEntry.session_key == session_key)
                    matching = session.exec(stmt).all()
                    c = len(matching)
                    for m in matching:
                        session.delete(m)
                    session.commit()
                    return c
            counts["deleted_l1"] = await asyncio.to_thread(_purge_l1)
        except Exception as e:
            logger.error(f"[HLSM] L1 pattern deletion error: {e}")

        try:
            def _purge_l0():
                from sqlalchemy import or_
                with Session(self.db_engine) as session:
                    conditions = [
                        col(HLSMWorkingEntry.content).like(f"%{search_pat}%"),
                        col(HLSMWorkingEntry.source).like(f"%{search_pat}%"),
                        col(HLSMWorkingEntry.session_key).like(f"%{search_pat}%"),
                    ]
                    for d in digit_variants:
                        conditions.append(col(HLSMWorkingEntry.content).like(f"%{d}%"))
                        conditions.append(col(HLSMWorkingEntry.session_key).like(f"%{d}%"))

                    stmt = select(HLSMWorkingEntry).where(or_(*conditions))
                    if session_key:
                        stmt = stmt.where(HLSMWorkingEntry.session_key == session_key)
                    matching = session.exec(stmt).all()
                    c = len(matching)
                    for m in matching:
                        session.delete(m)
                    session.commit()
                    return c
            counts["deleted_l0"] = await asyncio.to_thread(_purge_l0)
        except Exception as e:
            logger.error(f"[HLSM] L0 pattern deletion error: {e}")

        if self.kuzu_conn:
            try:
                q_l2 = "MATCH (n:SemanticMemory) WHERE n.content CONTAINS $pat DELETE n"
                await asyncio.to_thread(self.kuzu_conn.execute, q_l2, {"pat": search_pat})
                counts["deleted_l2"] = 1

                q_l3 = "MATCH (n:L3Memory) WHERE n.content CONTAINS $pat DELETE n"
                await asyncio.to_thread(self.kuzu_conn.execute, q_l3, {"pat": search_pat})
                counts["deleted_l3"] = 1
            except Exception as k_err:
                logger.debug(f"[HLSM] KùzuDB pattern deletion notice: {k_err}")

        counts["total_deleted"] = counts["deleted_l0"] + counts["deleted_l1"] + counts["deleted_l2"] + counts["deleted_l3"]
        logger.info(f"[HLSM] Pattern memory deletion complete for '{search_pat}': {counts}")
        return counts

    async def run_deep_audit(self) -> Dict[str, Any]:
        """
        [ Deep 4-Tier Memory Auditor ]
        Runs an asynchronous non-destructive forensic audit across L0, L1, L2, and L3.
        Returns health score, duplicate clusters, orphan counts, and retrieval bias risk.
        """
        if getattr(self, "auditor", None) is None:
            from .hlsm_auditor import HLSMDeepAuditor
            self.auditor = HLSMDeepAuditor(db_engine=self.db_engine, kuzu_conn=self.kuzu_conn)
        self.auditor.db_engine = self.db_engine
        self.auditor.kuzu_conn = self.kuzu_conn
        report = await self.auditor.run_deep_audit(self)
        return report.to_dict()

    async def deduplicate(
        self,
        dry_run: bool = False,
        cluster_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        [ Dynamic 4-Tier Memory Deduplicator & GC ]
        Executes atomic deduplication and orphan garbage collection across all memory tiers.
        Preserves authoritative canonical master records while eliminating bloat and retrieval bias.
        """
        if getattr(self, "deduplicator", None) is None:
            from .hlsm_deduplicator import HLSMDeduplicator
            self.deduplicator = HLSMDeduplicator(db_engine=self.db_engine, kuzu_conn=self.kuzu_conn)
        self.deduplicator.db_engine = self.db_engine
        self.deduplicator.kuzu_conn = self.kuzu_conn
        return await self.deduplicator.deduplicate_all(self, dry_run=dry_run, cluster_ids=cluster_ids)

