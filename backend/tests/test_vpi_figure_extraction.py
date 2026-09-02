import pytest
import os
import shutil
import tempfile
import asyncio
from unittest.mock import MagicMock, patch
from sqlmodel import create_engine
from backend.engine.vpi import VisualPolytopeIngestor
from backend.models import FigureType, FigureExtractionMetadata, FigureRecord, SQLModel
from backend.memory.hlsm_manager import HLSMManager, HLSMContext


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


def test_vpi_pass1_geometric_filtering():
    vpi = VisualPolytopeIngestor()
    candidates = [
        # 1. Tiny icon (width < 100, height < 100, no caption) -> Should be pruned
        {
            "id": "icon_1",
            "page_number": 1,
            "width": 32,
            "height": 32,
            "caption": "",
            "sha256": "hash_icon_1",
            "is_vector": False
        },
        # 2. Extreme aspect ratio banner (aspect ratio > 12.0) -> Should be pruned
        {
            "id": "banner_1",
            "page_number": 2,
            "width": 1200,
            "height": 40,
            "caption": "",
            "sha256": "hash_banner_1",
            "is_vector": False
        },
        # 3. Substantive Technical Diagram with Caption -> Should be retained
        {
            "id": "fig_tech_1",
            "page_number": 3,
            "width": 800,
            "height": 600,
            "caption": "Figure 1: High-Altitude Polytope Topology and Geodesic Flow",
            "sha256": "hash_fig_1",
            "file_path": "workspace/artifacts/extracted_figures/doc/fig1.png",
            "is_vector": False,
            "extracted_text": "Figure 1: High-Altitude Polytope Topology"
        },
        # 4. Data Chart -> Should be retained
        {
            "id": "chart_1",
            "page_number": 4,
            "width": 640,
            "height": 480,
            "caption": "Chart 2.1: Performance Throughput vs Context Length",
            "sha256": "hash_chart_1",
            "file_path": "workspace/artifacts/extracted_figures/doc/chart1.png",
            "is_vector": False,
            "extracted_text": "Chart 2.1: Performance Throughput"
        }
    ]

    filtered = vpi.filter_and_caption_figures(candidates, document_id="doc_test")
    assert len(filtered) == 2
    ids = [f["id"] for f in filtered]
    assert "fig_tech_1" in ids
    assert "chart_1" in ids
    assert "icon_1" not in ids
    assert "banner_1" not in ids


def test_vpi_recurring_watermark_pruning():
    vpi = VisualPolytopeIngestor()
    # Identical uncaptioned image hash appearing across 4 pages (header logo / watermark)
    candidates = [
        {"id": f"logo_p{i}", "page_number": i, "width": 200, "height": 80, "caption": "", "sha256": "shared_watermark_hash"}
        for i in range(1, 5)
    ]
    # And one substantive figure on page 2
    candidates.append({
        "id": "real_fig",
        "page_number": 2,
        "width": 700,
        "height": 500,
        "caption": "Figure 3: System Architecture",
        "sha256": "unique_fig_hash",
        "file_path": "workspace/artifacts/extracted_figures/doc/fig3.png"
    })

    filtered = vpi.filter_and_caption_figures(candidates, document_id="doc_test")
    assert len(filtered) == 1
    assert filtered[0]["id"] == "real_fig"


@pytest.mark.asyncio
async def test_hlsm_figure_ingestion_and_rrf_retrieval(temp_hlsm_manager):
    figures = [
        {
            "id": "fig_arch_001",
            "page_number": 1,
            "figure_type": "SYSTEM_DIAGRAM",
            "caption": "Figure 1: Polytope State Machine Architecture",
            "visual_summary": "Topological state space (W, X, G, N) showing affine boundary operators.",
            "file_path": "workspace/artifacts/extracted_figures/paper/fig_p1_0.png",
            "width": 800,
            "height": 600,
            "is_vector": False,
            "sha256": "sha_fig_arch_001"
        }
    ]

    doc_content = (
        "--- [DOCUMENT: spec.pdf | PAGE 1/1] ---\n"
        "This document describes the sovereign architecture.\n"
        "Figure 1: Polytope State Machine Architecture illustrates the core transition dynamics."
    )

    ingested = await temp_hlsm_manager.ingest_document_payload(
        filename="spec.pdf",
        content=doc_content,
        session_key="test_sess",
        metadata={"figures": figures, "file_path": "workspace/uploads/spec.pdf"}
    )
    assert len(ingested) >= 1

    # Retrieve context with a figure-related query
    ctx: HLSMContext = await temp_hlsm_manager.retrieve_context(
        objective="Explain the state machine architecture and show Figure 1",
        session_key="test_sess"
    )

    # Verify context to_prompt_block contains figure metadata and markdown embedding guidance
    prompt = ctx.to_prompt_block()
    assert "Substantive Technical Figures & Visual Assets" in prompt
    assert "Figure 1: Polytope State Machine Architecture" in prompt
    assert "workspace/artifacts/extracted_figures/paper/fig_p1_0.png" in prompt
    assert "![Caption](<file_path>)" in prompt
