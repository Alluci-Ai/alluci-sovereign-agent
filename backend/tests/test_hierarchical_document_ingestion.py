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
    # Verify that dynamic extraction captured tuple C and mapping kernels
    has_tuple = any("C = (" in c.get("math_formula", "") or "C" in c.get("name", "") for c in concepts)
    has_kernel = any("P:" in c.get("math_formula", "") or "Mapping Kernel" in c.get("name", "") for c in concepts)
    assert has_tuple or has_kernel


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
    grounding, doc_sha, doc_name = await _check_document_page_grounding(prompt)

    assert grounding is not None
    assert "[AUTHENTIC SOURCE DOCUMENT PAGE GROUNDING" in grounding
    assert "PAGE 6" in grounding
    assert "PAGE 7" in grounding
    assert "PAGE 8" in grounding
    assert "PAGE 9" in grounding


def test_distill_document_metadata_academic_banner_stripping():
    sample_academic_text = (
        "ORIGINAL RESEARCH ARTICLE\n"
        "published: 17 June 2014\n"
        "doi: 10.3389/fpsyg.2014.00577\n"
        "Objects of consciousness\n"
        "Donald D. Hoffman 1* and Chetan Prakash 2\n"
        "1 Department of Cognitive Sciences, University of California, Irvine, CA, USA\n"
        "2 Department of Mathematics, California State University, San Bernardino, CA, USA\n\n"
        "ABSTRACT\n"
        "We present a mathematical model of consciousness, focusing on what we call conscious agents. "
        "We define a conscious agent as a 7-tuple (W, X, G, P, D, A, N) where P, D, and A are Markovian transition kernels. "
        "We discuss the interface theory of perception and show that evolutionary games favor fitness over truth."
    )
    distilled = _distill_document_metadata("Hoffman_Objects of Consciousness.pdf", sample_academic_text)
    assert distilled["title"] == "Objects of consciousness"
    assert "We present a mathematical model of consciousness" in distilled["abstract"]
    assert "ORIGINAL RESEARCH ARTICLE" not in distilled["title"]


def test_select_optimal_local_model_glm_routing():
    from backend.inference.router import ModelRouter
    from backend.config import settings
    router = ModelRouter(settings)
    
    # 1. Long document request -> routes to local GLM-4
    model_long = router.select_optimal_local_model("Please provide a comprehensive overview and explain the 30-page whitepaper in detail", estimated_tokens=12000)
    assert model_long is not None and "GLM-4" in model_long

    # 2. Mathematical proof request -> routes to local GLM-4-32B or 31B
    model_proof = router.select_optimal_local_model("Formulate the mathematical proof and simplicial complex topology for conscious agents")
    assert model_proof is not None and ("GLM-4" in model_proof or "31b" in model_proof)


@pytest.mark.asyncio
async def test_dynamic_research_artifact_packaging(tmp_path):
    from backend.routers.gemini import _process_dynamic_artifact_block
    
    mock_response = (
        "# Objects of Consciousness — Comprehensive Treatise Analysis\n\n"
        "## Executive Summary\n"
        "This dossier provides an exhaustive analysis of the Conscious Realism framework.\n\n"
        "## Mathematical Foundations\n"
        "A conscious agent is formalized as a 7-tuple $C = ((X, \\mathcal{X}), (G, \\mathcal{G}), W, P, D, A, N)$."
        + "\n\n" + "Detailed exposition of theorems and evolutionary fitness simulations."
    )
    mock_prompt = "Please provide a comprehensive overview and deep analysis of the Hoffman Objects of Consciousness paper"
    
    await _process_dynamic_artifact_block(mock_response, mock_prompt, output_dir=str(tmp_path))
    
    # Check that artifact triad was persisted in isolated tmp_path
    import glob
    matching_dirs = glob.glob(f"{str(tmp_path)}/research/*_objects_of_consciousness*")
    assert len(matching_dirs) >= 1
    art_dir = matching_dirs[-1]
    assert os.path.exists(os.path.join(art_dir, "metadata.json"))
    assert os.path.exists(os.path.join(art_dir, "source.md"))
    assert os.path.exists(os.path.join(art_dir, "source.html"))
    
    with open(os.path.join(art_dir, "source.md"), "r") as f:
        md_text = f.read()
        assert "Conscious Realism" in md_text
    
    with open(os.path.join(art_dir, "source.html"), "r") as f:
        html_text = f.read()
        assert "<h1>Objects of Consciousness — Comprehensive Treatise Analysis</h1>" in html_text


@pytest.mark.asyncio
async def test_sha256_scoped_memory_isolation(temp_hlsm_manager):
    """Verifies that scoping retrieval to a specific document SHA-256 blocks cross-document memory bleeding."""
    # Ingest Document A (Hoffman)
    doc_a_content = (
        "--- [DOCUMENT: Hoffman.pdf | PAGE 1/1] ---\n"
        "Conscious agents 7-tuple model and interface theory of perception."
    )
    ids_a = await temp_hlsm_manager.ingest_document_payload(
        filename="Hoffman.pdf", content=doc_a_content, session_key="session_a"
    )
    
    # Ingest Document B (CIMC)
    doc_b_content = (
        "--- [DOCUMENT: CIMC.pdf | PAGE 1/1] ---\n"
        "Integrated Information Theory with Tononi Phi metric and Karl Friston Free Energy Principle."
    )
    ids_b = await temp_hlsm_manager.ingest_document_payload(
        filename="CIMC.pdf", content=doc_b_content, session_key="session_b"
    )

    import hashlib
    sha_a = hashlib.sha256(doc_a_content.encode("utf-8")).hexdigest()
    sha_b = hashlib.sha256(doc_b_content.encode("utf-8")).hexdigest()

    # Query with sha_a scope: should retrieve only Hoffman, zero Tononi/FEP
    res_a = await temp_hlsm_manager.retrieve_context(
        objective="Extract mathematical formulas and models of consciousness",
        doc_sha256=sha_a
    )
    prompt_block_a = res_a.to_prompt_block()
    assert "Tononi" not in prompt_block_a
    assert "Free Energy Principle" not in prompt_block_a



