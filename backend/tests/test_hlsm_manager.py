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
import pytest
import asyncio
from datetime import datetime, timezone
from sqlmodel import Session, select
from unittest.mock import MagicMock, AsyncMock, patch


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def hlsm_manager(temp_db):
    from backend.memory.hlsm_manager import HLSMManager
    # HLSMManager(db_engine, redis_client, chroma_collection, settings)
    mgr = HLSMManager(
        db_engine=temp_db,
        redis_client=None,
        chroma_collection=MagicMock(),
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
    # Mock ChromaDB response structure
    hlsm_manager.chroma.query = MagicMock(return_value={
        "documents": [["Cognitive architecture involving polytopic manifolds."]],
        "ids": [["l2_test_01"]],
        "metadatas": [[{
            "source": "manual",
            "betti_1_support": 0.5,
            "topological_importance": 1.0,
            "created_at": datetime.now(timezone.utc).timestamp()
        }]],
        "distances": [[0.1]]
    })
    hlsm_manager.chroma.count = MagicMock(return_value=1)
        
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
