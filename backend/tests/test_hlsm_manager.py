import pytest
pytestmark = pytest.mark.unit

"""
H-LSM Manager (Hierarchical Long-Short Term Memory) — Production Test Suite
========================================================================
Covers:
  - Tiered Storage (L1 Episodic, L2 Semantic, L3 Archival)
  - FTS5 Search (SQLite virtual table integration)
  - ILIKE Fallback (PostgreSQL / Non-FTS5 compatibility)
  - Consolidation Loops (L1 → L2 → L3)
  - Relevance-based retrieval
  - Retention-score decay simulation
  - Metadata preservation
"""
import uuid
import asyncio
from datetime import datetime, timezone
from sqlmodel import Session, select
from unittest.mock import MagicMock, AsyncMock, patch


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def hlsm_manager(temp_db):
    from backend.memory.hlsm_manager import HLSMManager
    mgr = HLSMManager(
        db_engine=temp_db,
        redis_client=None,
        kuzu_db_path=None,
        settings=None
    )
    # Mock embedding generator to avoid external API calls
    mgr.embedding_service = MagicMock()  # type: ignore
    mgr.embedding_service.get_embedding = AsyncMock(return_value=[0.1] * 1536)  # type: ignore
    return mgr


# ─── L1 Episodic Memory ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_l1_store_and_retrieve_recent(hlsm_manager):
    mem_id = await hlsm_manager.store(
        content="System deployed successfully to production-core-01",
        metadata={"source": "deployment_bot", "env": "prod"},
    )
    assert mem_id is not None
    
    recent = await hlsm_manager.l1_get_recent(limit=5)
    assert len(recent) >= 1
    assert recent[0].id == mem_id
    assert recent[0].content == "System deployed successfully to production-core-01"
    assert recent[0].source == "deployment_bot"


@pytest.mark.asyncio
async def test_l1_search_hits_fts5_or_fallback(hlsm_manager):
    # Store multiple entries
    await hlsm_manager.store("Red apple in the kitchen")
    await hlsm_manager.store("Blue berry in the fridge")
    
    # Search for 'apple'
    results = await hlsm_manager.l1_search("apple", limit=5)
    assert len(results) >= 1
    assert "apple" in results[0].content.lower()
    assert "fridge" not in results[0].content.lower()


# ─── Utils ────────────────────────────────────────────────────────────────────

def _init_fts5(engine):
    """Manually initialize the FTS5 virtual table for testing (since SQLModel won't)."""
    with engine.connect() as conn:
        conn.execute(text("CREATE VIRTUAL TABLE IF NOT EXISTS hlsm_episodic_fts USING fts5(id UNINDEXED, content)"))
        conn.execute(text("CREATE TRIGGER IF NOT EXISTS hlsm_episodic_after_insert AFTER INSERT ON hlsm_episodic BEGIN INSERT INTO hlsm_episodic_fts(id, content) VALUES (new.id, new.content); END"))
        conn.commit()


# ─── L2 Semantic Memory ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_l2_search_returns_relevant_matches(hlsm_manager):
    # Mock KùzuDB response structure
    mock_conn = MagicMock()
    mock_result = MagicMock()
    mock_result.has_next.side_effect = [True, False]
    mock_result.get_next.return_value = [
        "l2_test_01", "Cognitive architecture involving polytopic manifolds.", "manual", "sess", 0.0, 1.0, 0.5, 1, time.time(), False, "", "", 0.0
    ]
    mock_conn.execute.return_value = mock_result
    hlsm_manager.kuzu_conn = mock_conn
        
    results = await hlsm_manager.l2_search("cognitive manifold", limit=5)
    assert len(results) >= 1
    assert "polytopic" in results[0].content
    assert results[0].tier == 2


# ─── FTS5 Specifics ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fts5_sync_via_triggers(hlsm_manager):
    """
    Verify that the triggers keep the FTS table in sync.
    We must manually init the virtual table for the temp test DB.
    """
    # This only works on SQLite
    if "sqlite" not in str(hlsm_manager.db_engine.url):
        pytest.skip("Not an SQLite database")
    
    _init_fts5(hlsm_manager.db_engine)
        
    # 1. Insert into episodic
    await hlsm_manager.store("Trigger test content")
    
    # 2. Query FTS table directly via raw SQL
    with hlsm_manager.db_engine.connect() as conn:
        res = conn.execute(text("SELECT content FROM hlsm_episodic_fts WHERE hlsm_episodic_fts MATCH 'Trigger'")).fetchone()
        assert res is not None
        assert "Trigger test content" in res[0]


# ─── Imports ──────────────────────────────────────────────────────────────────
import json
from sqlalchemy import text

# ─── New Tests for High Coverage ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_l0_store_retrieve_clear_sql(hlsm_manager):
    # Test L0 operations falling back to SQL (since redis is None)
    session_key = "sess_123"
    
    # Store
    mem_id = await hlsm_manager.l0_store("User asked for status", session_key)
    assert mem_id is not None
    
    # Retrieve
    entries = await hlsm_manager.l0_retrieve(session_key)
    assert len(entries) == 1
    assert entries[0].content == "User asked for status"
    assert entries[0].tier == 0
    
    # Clear
    await hlsm_manager.l0_clear_session(session_key)
    entries_after = await hlsm_manager.l0_retrieve(session_key)
    assert len(entries_after) == 0

@pytest.mark.asyncio
async def test_hlsm_context_to_prompt_block():
    from backend.memory.hlsm_manager import HLSMContext, HLSMRetrievalResult
    ctx = HLSMContext(
        working_memories=[HLSMRetrievalResult(id="1", content="Working", tier=0, source="s", relevance_score=1.0, retention_score=1.0)],
        episodic_memories=[HLSMRetrievalResult(id="2", content="Episodic", tier=1, source="s", relevance_score=1.0, retention_score=1.0)],
        semantic_memories=[HLSMRetrievalResult(id="3", content="Semantic", tier=2, source="s", relevance_score=1.0, retention_score=1.0)]
    )
    block = ctx.to_prompt_block()
    assert "Working Memory" in block
    assert "Episodic Memory" in block
    assert "Semantic Memory" in block
    assert "Working" in block

@pytest.mark.asyncio
async def test_retrieve_context(hlsm_manager):
    # Pre-populate L0 and L1
    await hlsm_manager.l0_store("Working", "s1")
    await hlsm_manager.l1_store("Episodic goal data")
    
    ctx = await hlsm_manager.retrieve_context("goal", psi=0.5, session_key="s1")
    assert ctx.total_chars > 0
    assert ctx.total_tokens > 0
    # There should be 1 working memory
    assert len(ctx.working_memories) >= 1
    assert len(ctx.episodic_memories) >= 1

@pytest.mark.asyncio
async def test_encode_from_execution(hlsm_manager):
    tasks = {
        "t1": MagicMock(status="completed", result="Test succeeded", action="test_action"),
        "t2": MagicMock(status="failed", result="Test error", action="test_action_2"),
        "t3": MagicMock(status="completed", result="short", action="test_action_3") # too short to encode
    }
    encoded = await hlsm_manager.encode_from_execution(run_id=1, tasks=tasks, objective="Test run", session_key="s1")
    # Should encode t1 and t2. t3 is too short (len < 10)
    assert encoded == 2
    
    # Check L0 got the objective
    l0 = await hlsm_manager.l0_retrieve("s1")
    assert len(l0) >= 1
    assert "Test run" in l0[0].content

@pytest.mark.asyncio
async def test_encode_message(hlsm_manager):
    # Short message -> L0 only
    short_id = await hlsm_manager.encode_message("hello", "s1")
    l1_recent = await hlsm_manager.l1_get_recent()
    assert not any("hello" in r.content for r in l1_recent)
    
    # Long message -> L0 and L1
    long_msg = "This is a very long message that should easily exceed the threshold of one hundred characters required to encode into episodic memory"
    long_id = await hlsm_manager.encode_message(long_msg, "s1")
    l1_recent2 = await hlsm_manager.l1_get_recent()
    assert any(long_msg in r.content for r in l1_recent2)

@pytest.mark.asyncio
async def test_consolidation_sweep(hlsm_manager):
    # Add an expired L0 entry
    now = time.time()
    from backend.models import HLSMWorkingEntry, HLSMEpisodicEntry
    with Session(hlsm_manager.db_engine) as session:
        session.add(HLSMWorkingEntry(id="old_l0", session_key="s", content="c", source="s", created_at=now-4000, expires_at=now-10))
        # Add an L1 entry ready for promotion
        e1 = HLSMEpisodicEntry(id="e1", content="promotable", source="s", session_key="s", objective_hash="",
                              psi_at_encoding=0.5, valence_at_encoding=0.5, topological_importance=1.0,
                              betti_1_support=0, access_count=10, last_accessed=now, created_at=now,
                              retention_score=1.0, promoted_to_l2=False)
        # Add an L1 entry to prune (decayed)
        e2 = HLSMEpisodicEntry(id="e2", content="prunable", source="s", session_key="s", objective_hash="",
                              psi_at_encoding=0.5, valence_at_encoding=0.5, topological_importance=0.1,
                              betti_1_support=0, access_count=0, last_accessed=now-10000000, created_at=now-10000000,
                              retention_score=0.01, promoted_to_l2=False)
        session.add(e1)
        session.add(e2)
        session.commit()
    
    hlsm_manager.l2_store = AsyncMock(return_value="l2_123")
    summary = await hlsm_manager.consolidation_sweep()
    
    assert summary["promoted"] >= 1
    assert summary["pruned_l1"] >= 1
    assert summary["pruned_l0"] >= 1

@pytest.mark.asyncio
async def test_get_stats(hlsm_manager):
    stats = await hlsm_manager.get_stats()
    assert "hlsm_version" in stats
    assert "L0_working" in stats["tiers"]

@pytest.mark.asyncio
async def test_legacy_methods(hlsm_manager):
    mem_id = await hlsm_manager.store("Legacy test", {"source": "test"}, "s1")
    assert mem_id is not None
    
    res = await hlsm_manager.search("Legacy test")
    assert len(res) >= 1
    
    entries = await hlsm_manager.list_entries()
    assert entries["total"] >= 1
    
    deleted = await hlsm_manager.delete(mem_id)
    assert deleted is True

@pytest.mark.asyncio
async def test_redis_branches(hlsm_manager):
    import json
    mock_redis = AsyncMock()
    # lrange should return a valid json entry and an invalid one
    mock_redis.lrange.return_value = [json.dumps({"id": "r1", "content": "redis", "source": "s"}), "invalid_json"]
    hlsm_manager.redis = mock_redis
    
    # store
    await hlsm_manager.l0_store("test redis", "s1")
    mock_redis.lpush.assert_awaited_once()
    
    # retrieve
    results = await hlsm_manager.l0_retrieve("s1")
    assert len(results) == 1
    assert results[0].content == "redis"
    
    # clear
    await hlsm_manager.l0_clear_session("s1")
    mock_redis.delete.assert_awaited_once()

@pytest.mark.asyncio
async def test_l2_store_delete(hlsm_manager):
    from backend.models import HLSMEpisodicEntry
    e = HLSMEpisodicEntry(id="123", content="c", source="s", session_key="s", objective_hash="o", 
                          psi_at_encoding=0.1, valence_at_encoding=0.5, topological_importance=1.0, 
                          betti_1_support=0.0, access_count=1, last_accessed=time.time(), created_at=time.time(), 
                          retention_score=1.0, promoted_to_l2=False)
    
    mock_conn = MagicMock()
    hlsm_manager.kuzu_conn = mock_conn
    
    cid = await hlsm_manager.l2_store(e)
    assert cid == "l2_123"
    mock_conn.execute.assert_called()
    
    success = await hlsm_manager.l2_delete("l2_123")
    assert success is True

@pytest.mark.asyncio
async def test_start_stop_consolidation(hlsm_manager):
    await hlsm_manager.start_consolidation_loop()
    assert hlsm_manager._consolidation_task is not None
    assert not hlsm_manager._consolidation_task.done()
    
    await hlsm_manager.stop_consolidation_loop()
    assert hlsm_manager._consolidation_task.cancelled() or hlsm_manager._consolidation_task.done()

import time
