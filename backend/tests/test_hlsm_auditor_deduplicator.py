"""
Unit & Integration Tests for Deep 4-Tier Memory Auditor & CAS Deduplicator
========================================================================
"""

import pytest
pytestmark = pytest.mark.unit

import asyncio
import os
import shutil
import tempfile
import time
from sqlmodel import create_engine, Session

from backend.memory.hlsm_manager import HLSMManager
from backend.memory.hlsm_auditor import HLSMDeepAuditor
from backend.memory.hlsm_deduplicator import HLSMDeduplicator
from backend.models import SQLModel, HLSMEpisodicEntry, HLSMWorkingEntry


@pytest.fixture
def temp_hlsm_env():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_hlsm.db")
    kuzu_path = os.path.join(temp_dir, "test_kuzu")

    engine = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(engine)

    manager = HLSMManager(
        db_engine=engine,
        redis_client=None,
        kuzu_db_path=kuzu_path,
        settings=None,
    )
    yield manager, engine, kuzu_path

    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_deep_auditor_detects_l1_duplicates(temp_hlsm_env):
    manager, engine, _ = temp_hlsm_env
    auditor = HLSMDeepAuditor(db_engine=engine, kuzu_conn=manager.kuzu_conn)

    # 1. Insert duplicate L1 episodic entries into SQLite
    with Session(engine) as session:
        e1 = HLSMEpisodicEntry(
            id="l1_test_01",
            content="Consciousness is a functional property of information processing.",
            source="user",
            session_key="sess_1",
            created_at=time.time() - 100
        )
        e2 = HLSMEpisodicEntry(
            id="l1_test_02",
            content="Consciousness is a functional property of information processing.",
            source="user",
            session_key="sess_2",
            created_at=time.time() - 50
        )
        session.add(e1)
        session.add(e2)
        session.commit()

    # 2. Run L1 Audit
    l1_res = await auditor.audit_l1()
    assert l1_res["total_records"] == 2
    assert l1_res["duplicate_count"] == 1
    assert len(l1_res["clusters"]) == 1
    cluster = l1_res["clusters"][0]
    assert cluster.canonical_id == "l1_test_01" or cluster.canonical_id == "l1_test_02"
    assert len(cluster.duplicate_ids) == 1


@pytest.mark.asyncio
async def test_deep_auditor_and_deduplicator_full_cycle(temp_hlsm_env):
    manager, engine, _ = temp_hlsm_env

    # 1. Ingest same document payload twice to simulate multiple uploads
    doc_content = """# The California Institute for Machine Consciousness
CIMC Research Program.
Thesis: Consciousness is computational functionalism.
"""
    await manager.ingest_document_payload(
        filename="CIMC_Whitepaper.pdf",
        content=doc_content,
        session_key="sess_1",
        metadata={"file_path": "/docs/CIMC_Whitepaper.pdf"}
    )
    # Manually create a duplicate DocumentNode to test auditor & deduplicator cleanup
    if manager.kuzu_conn:
        q_dup = (
            "MERGE (d:DocumentNode {id: 'doc_duplicate_01'}) "
            "SET d.name = 'CIMC_Whitepaper.pdf', d.title = 'The California Institute for Machine Consciousness', "
            "d.sha256 = 'simulated_sha_123', d.summary = 'CIMC Research Program.', d.created_at = 1000.0, d.access_count = 1"
        )
        manager.kuzu_conn.execute(q_dup)

    # 2. Run Deep Audit
    report = await manager.run_deep_audit()
    assert report["health_score"] <= 1.0
    assert "total_records" in report
    assert "duplicate_clusters" in report

    # 3. Test Dry Run Deduplication
    dry_res = await manager.deduplicate(dry_run=True)
    assert dry_res["status"] == "DRY_RUN"
    assert "clusters_to_prune" in dry_res

    # 4. Test Real Execution Deduplication
    exec_res = await manager.deduplicate(dry_run=False)
    assert exec_res["status"] == "SUCCESS"
    assert exec_res["health_score_after"] >= exec_res["health_score_before"]


@pytest.mark.asyncio
async def test_cas_idempotency_prevents_duplicate_nodes(temp_hlsm_env):
    manager, _, _ = temp_hlsm_env

    doc = """# Donald Hoffman Objects of Consciousness
Conscious Realism posits that consciousness is fundamental. Spacetime is a species-specific desktop user interface.
"""
    # First upload
    res1 = await manager.ingest_document_payload(
        filename="Hoffman_Objects.pdf",
        content=doc,
        session_key="sess_a"
    )
    assert len(res1) == 1
    master_id = res1[0]

    # Second upload of identical document
    res2 = await manager.ingest_document_payload(
        filename="Hoffman_Objects.pdf",
        content=doc,
        session_key="sess_b"
    )
    assert len(res2) == 1
    # Must return existing canonical master ID without creating duplicate nodes
    assert res2[0] == master_id


@pytest.mark.asyncio
async def test_consolidation_sweep_executes_self_healing_deduplication(temp_hlsm_env):
    manager, engine, _ = temp_hlsm_env

    # 1. Insert duplicate L1 episodic entries into SQLite with high retention
    with Session(engine) as session:
        now = time.time()
        e1 = HLSMEpisodicEntry(
            id="l1_sweep_01",
            content="Topological State Spaces (W, X, G, N) are strictly bounded.",
            source="user",
            session_key="sess_sweep",
            topological_importance=1.0,
            access_count=5,
            created_at=now - 2,
            last_accessed=now
        )
        e2 = HLSMEpisodicEntry(
            id="l1_sweep_02",
            content="Topological State Spaces (W, X, G, N) are strictly bounded.",
            source="user",
            session_key="sess_sweep",
            topological_importance=1.0,
            access_count=5,
            created_at=now - 1,
            last_accessed=now
        )
        session.add(e1)
        session.add(e2)
        session.commit()

    # 2. Run Consolidation Sweep
    summary = await manager.consolidation_sweep()
    assert summary["deduplicated_l1"] >= 1
    assert summary["freed_bytes"] > 0
    assert summary["health_score"] >= 0.95


@pytest.mark.asyncio
async def test_heartbeat_memory_integrity_probe(temp_hlsm_env, monkeypatch):
    manager, engine, _ = temp_hlsm_env
    from backend import services
    from backend.heartbeat import _probe_memory_integrity

    monkeypatch.setattr(services, "hlsm_manager", manager)

    # 1. Insert duplicate entry to drop health score
    with Session(engine) as session:
        now = time.time()
        e1 = HLSMEpisodicEntry(
            id="l1_hb_01",
            content="Simplicial Chain-of-Thought (S-CoT) face verification.",
            source="user",
            session_key="sess_hb",
            topological_importance=1.0,
            access_count=5,
            created_at=now - 2,
            last_accessed=now
        )
        e2 = HLSMEpisodicEntry(
            id="l1_hb_02",
            content="Simplicial Chain-of-Thought (S-CoT) face verification.",
            source="user",
            session_key="sess_hb",
            topological_importance=1.0,
            access_count=5,
            created_at=now - 1,
            last_accessed=now
        )
        session.add(e1)
        session.add(e2)
        session.commit()

    # 2. Execute Probe
    fired, detail = await _probe_memory_integrity({})
    assert fired is True
    assert "Self-healed" in detail

    # 3. Second run should be optimal
    fired_second, detail_second = await _probe_memory_integrity({})
    assert fired_second is False
    assert "optimal" in detail_second.lower()

