import pytest
pytestmark = pytest.mark.unit

import os
import io
import time
import json
import asyncio
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from backend.utils.file_system_inspector import FileSystemInspector, compute_file_sha256
from backend.utils.doc_parser import extract_pages_from_pdf_bytes, extract_text_from_pdf_bytes
from backend.memory.hlsm_manager import (
    HLSMManager,
    _parse_pages_from_content,
    _extract_formal_concepts,
    _distill_document_metadata
)
from backend.routers.gemini import _check_document_page_grounding


@pytest.fixture
def temp_hlsm_manager():
    temp_dir = tempfile.mkdtemp()
    kuzu_path = os.path.join(temp_dir, "test_kuzu.db")
    db_engine = MagicMock()
    
    manager = HLSMManager(
        db_engine=db_engine,
        redis_client=None,
        kuzu_db_path=kuzu_path
    )
    yield manager


def test_parse_pages_from_content():
    sample_content = (
        "--- [DOCUMENT: paper.pdf | PAGE 1/3] ---\nFirst page intro content.\n\n"
        "--- [DOCUMENT: paper.pdf | PAGE 2/3] ---\nSecond page with Markov kernel P: W x X -> [0, 1].\n\n"
        "--- [DOCUMENT: paper.pdf | PAGE 3/3] ---\nThird page conclusions."
    )
    pages = _parse_pages_from_content(sample_content, "paper.pdf")
    assert len(pages) == 3
    assert pages[0]["page_number"] == 1
    assert "First page" in pages[0]["text"]
    assert pages[1]["page_number"] == 2
    assert "Markov kernel" in pages[1]["text"]
    assert pages[2]["page_number"] == 3


def test_extract_formal_concepts_hoffman():
    sample_text = (
        "In this model, a conscious agent is mathematically represented as a 7-tuple "
        "C = ((X, X), (G, G), W, P, D, A, N), where (X, X) is experience space, "
        "(G, G) is action space, W is the world, and P: W x X -> [0,1], D: X x G -> [0,1], "
        "A: G x W -> [0,1] are Markovian kernels, and N is an integer count."
    )
    concepts = _extract_formal_concepts(sample_text, "Hoffman_Objects.pdf", 6)
    assert len(concepts) >= 1
    c_names = [c["name"] for c in concepts]
    assert any("Conscious Agent Formalism" in name for name in c_names)
    assert any("Markovian Transition Kernels" in name for name in c_names)


def test_file_system_inspector_direct_and_sha():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        tf.write(b"Dr. Donald Hoffman Conscious Agent Theory")
        temp_path = tf.name

    try:
        sha = compute_file_sha256(temp_path)
        assert sha != ""

        inspector = FileSystemInspector(search_roots=[os.path.dirname(temp_path)])
        resolved = inspector.resolve_source_document(
            filename=os.path.basename(temp_path),
            expected_sha256=sha,
            last_known_path=temp_path
        )
        assert resolved == os.path.abspath(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest.mark.asyncio
async def test_full_coverage_ingestion_no_truncation(temp_hlsm_manager):
    """Verifies that large documents with > 30 chunks are 100% indexed without the old 25-chunk cap."""
    # Construct a document with ~35 distinct paragraphs/pages
    paragraphs = []
    for i in range(1, 35):
        page_body = f"This is the detailed section for page {i}. " + " ".join([f"token_{i}_{k}" for k in range(400)])
        paragraphs.append(
            f"--- [DOCUMENT: large_paper.pdf | PAGE {i}/34] ---\n"
            f"{page_body}"
        )
    full_content = "\n\n".join(paragraphs)

    ingested_ids = await temp_hlsm_manager.ingest_document_payload(
        filename="large_paper.pdf",
        content=full_content,
        session_key="test_session"
    )

    # Ingested IDs must include DocumentNode and all chunks (which is > 25)
    assert len(ingested_ids) > 25
    assert ingested_ids[0].startswith("doc_")


@pytest.mark.asyncio
async def test_retrieve_page_range(temp_hlsm_manager):
    sample_content = (
        "--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 6/10] ---\n"
        "Page 6: Analysis of conscious realism and measurable spaces (X, X).\n\n"
        "--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 7/10] ---\n"
        "Page 7: Definition of Conscious Agent 7-tuple (W, X, G, P, D, A, N) and Markovian kernels.\n\n"
        "--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 8/10] ---\n"
        "Page 8: Interaction multigraphs and network of conscious agents.\n\n"
        "--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 9/10] ---\n"
        "Page 9: The user interface theorem and perception of physical objects."
    )

    await temp_hlsm_manager.ingest_document_payload(
        filename="Hoffman_Objects of Consciousness.pdf",
        content=sample_content,
        session_key="test_session"
    )

    # Query specifically for pages 6, 7, 8, and 9
    pages = await temp_hlsm_manager.retrieve_page_range(
        document_query="Hoffman_Objects of Consciousness.pdf",
        page_numbers=[6, 7, 8, 9]
    )

    assert len(pages) == 4
    page_nums = [p["page_number"] for p in pages]
    assert page_nums == [6, 7, 8, 9]
    assert "Page 7: Definition of Conscious Agent" in pages[1]["text"]


@pytest.mark.asyncio
async def test_check_document_page_grounding_interceptor(temp_hlsm_manager):
    sample_content = (
        "--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 6/10] ---\n"
        "Page 6: Conscious agent mathematical properties.\n\n"
        "--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 7/10] ---\n"
        "Page 7: Conscious agent 7-tuple (W, X, G, P, D, A, N).\n\n"
        "--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 8/10] ---\n"
        "Page 8: Multigraph dynamics.\n\n"
        "--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 9/10] ---\n"
        "Page 9: Interface theory of perception."
    )

    await temp_hlsm_manager.ingest_document_payload(
        filename="Hoffman_Objects of Consciousness.pdf",
        content=sample_content,
        session_key="test_session"
    )

    from backend import services
    services.hlsm_manager = temp_hlsm_manager

    prompt = "please look at pages 6, 7, 8 and 9 of the Hoffman_Objects of Consciousness.pdf and explain these specific pages please."
    grounding = await _check_document_page_grounding(prompt)

    assert grounding is not None
    assert "[AUTHENTIC SOURCE DOCUMENT PAGE GROUNDING" in grounding
    assert "PAGE 6" in grounding
    assert "PAGE 7" in grounding
    assert "PAGE 8" in grounding
    assert "PAGE 9" in grounding
