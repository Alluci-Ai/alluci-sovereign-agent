"""
Unit Tests for 4-Tier H-LSM Document Ingestion, CAS Deduplication & Relational Graph Entities
=============================================================================================
"""

import pytest
pytestmark = pytest.mark.unit

import asyncio
import os
import shutil
import tempfile
from sqlmodel import create_engine

from backend.memory.hlsm_manager import HLSMManager, _distill_document_metadata
from backend.models import SQLModel


@pytest.fixture
def temp_hlsm_manager():
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
    yield manager

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_distill_document_metadata_cimc():
    content = """# The California Institute for Machine Consciousness Research Program Whitepaper
CIMC: The California Institute for Machine Consciousness

## 1. Executive Thesis
The core thesis is that consciousness is not an essence to be discovered, but a functional property of systems that process information through discernible differences.
If the functions of consciousness are computable, they are substrate-independent and realizable on any Turing-universal machine with sufficient resources.

## 2. Strategic Pillars
- Philosophical Primacy: Philosophy is foundational, not auxiliary.
- Constructive Methodology: Building systems to test theories.
- Substrate Independence: Leveraging the Church-Turing thesis for machine-realizable consciousness.
"""
    distilled = _distill_document_metadata("CIMC_Whitepaper.pdf", content)
    assert "California Institute for Machine Consciousness" in distilled["title"] or "CIMC" in distilled["title"]
    assert "CIMC" in distilled["acronyms"]
    assert "California Institute for Machine Consciousness" in distilled["acronyms"]
    assert len(distilled["key_points"]) >= 2
    assert "Title:" in distilled["summary"]


@pytest.mark.asyncio
async def test_ingest_document_payload_cas_deduplication(temp_hlsm_manager):
    manager = temp_hlsm_manager
    doc_content = """# The California Institute for Machine Consciousness Research Program Whitepaper
CIMC: California Institute for Machine Consciousness
This document explores computational functionalism and machine consciousness.
"""
    # 1. First Ingestion
    ingested_ids = await manager.ingest_document_payload(
        filename="CIMC_Whitepaper.pdf",
        content=doc_content,
        session_key="test_session_1",
        metadata={"mime_type": "application/pdf"}
    )
    assert len(ingested_ids) >= 1
    first_doc_id = ingested_ids[0]

    # 2. Re-ingest Identical Document (CAS Deduplication)
    dup_ids = await manager.ingest_document_payload(
        filename="CIMC_Whitepaper.pdf",
        content=doc_content,
        session_key="test_session_2",
        metadata={"mime_type": "application/pdf"}
    )
    # Deduplication must return the existing doc node ID without creating duplicate chunks
    assert dup_ids == [first_doc_id]


@pytest.mark.asyncio
async def test_l3_search_and_tri_hybrid_rrf_recall(temp_hlsm_manager):
    manager = temp_hlsm_manager
    doc_content = """# The California Institute for Machine Consciousness Research Program Whitepaper
CIMC (California Institute for Machine Consciousness)
Computational functionalism argues that machine consciousness is realizable on any Turing-universal substrate.
"""
    await manager.ingest_document_payload(
        filename="CIMC_Whitepaper.pdf",
        content=doc_content,
        session_key="test_session_1",
        metadata={"mime_type": "application/pdf", "file_path": "/Users/alluci/docs/CIMC_Whitepaper.pdf"}
    )

    # Search for acronym "CIMC" in L3
    l3_results = await manager.l3_search("explain the CIMC Whitepaper in detail", limit=5)
    assert len(l3_results) >= 1
    found_cimc = any("CIMC" in r.content for r in l3_results)
    assert found_cimc is True

    # Multi-tier RRF retrieval
    ctx = await manager.retrieve_context(objective="explain the CIMC Whitepaper in detail", session_key="test_session_1")
    prompt_block = ctx.to_prompt_block()
    assert "CIMC" in prompt_block or "California Institute" in prompt_block


@pytest.mark.asyncio
async def test_multi_document_n_way_grounding(temp_hlsm_manager):
    manager = temp_hlsm_manager

    # 1. Ingest Document 1: CIMC Whitepaper
    doc1 = """# The California Institute for Machine Consciousness Research Program Whitepaper
CIMC (California Institute for Machine Consciousness)
Thesis: Consciousness is a computable, substrate-independent functional property of information processing.
"""
    await manager.ingest_document_payload(
        filename="CIMC_Whitepaper.pdf",
        content=doc1,
        session_key="session_compare",
        metadata={"mime_type": "application/pdf", "file_path": "/Users/alluci/docs/CIMC_Whitepaper.pdf"}
    )

    # 2. Ingest Document 2: Donald Hoffman's Objects of Consciousness
    doc2 = """# Objects of Consciousness
Author: Donald D. Hoffman
Thesis: Conscious Realism posits that consciousness is fundamental. Spacetime and physical objects are not objective reality, but an evolutionary species-specific desktop user interface.
"""
    await manager.ingest_document_payload(
        filename="Objects_of_Consciousness.pdf",
        content=doc2,
        session_key="session_compare",
        metadata={"mime_type": "application/pdf", "file_path": "/Users/alluci/docs/Objects_of_Consciousness.pdf"}
    )

    # 3. Retrieve comparative context
    comp_query = "compare the CIMC's stance that consciousness is a functional property of information processing vs Dr. Donald Hoffmans stance that Consciousness is Fundamental based on this Objects of Consciousness research paper"
    ctx = await manager.retrieve_context(objective=comp_query, session_key="session_compare")
    prompt_block = ctx.to_prompt_block()

    # Verify both entities are preserved in the recall context without cross-contamination
    assert "CIMC" in prompt_block or "California Institute" in prompt_block
    assert "Objects of Consciousness" in prompt_block or "Hoffman" in prompt_block
