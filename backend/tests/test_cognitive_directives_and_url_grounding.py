import pytest
pytestmark = pytest.mark.unit

import os
import io
import json
import asyncio
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from backend.engine.intent_decomposer import IntentDecomposer, DirectiveModality, IntentType
from backend.engine.directive_registry import CognitiveDirectiveRegistry
from backend.routers.gemini import (
    _check_url_grounding,
    _check_document_grounding,
    _process_dynamic_artifact_block
)
from backend.memory.hlsm_manager import HLSMManager


@pytest.fixture
def temp_hlsm_manager():
    temp_dir = tempfile.mkdtemp()
    kuzu_path = os.path.join(temp_dir, "test_kuzu.db")
    db_engine = MagicMock()
    manager = HLSMManager(db_engine=db_engine, redis_client=None, kuzu_db_path=kuzu_path)
    yield manager


def test_intent_decomposer_directive_modalities():
    decomposer = IntentDecomposer()

    # 1. Multi Document Comparison
    res1 = decomposer.decompose("Compare and contrast the Hoffman Conscious Realism paper with the CIMC Whitepaper")
    assert res1.directive_modality == DirectiveModality.MULTI_DOCUMENT_COMPARISON

    # 2. Critical Analysis & Critique
    res2 = decomposer.decompose("Critique the theoretical proofs and highlight flaws and limitations in this paper")
    assert res2.directive_modality == DirectiveModality.CRITICAL_ANALYSIS

    # 3. Creative Writing
    res3 = decomposer.decompose("Write a creative story and philosophical allegory exploring conscious agent worldbuilding")
    assert res3.directive_modality == DirectiveModality.CREATIVE_WRITING

    # 4. Academic Article
    res4 = decomposer.decompose("Author an academic research paper and formal treatise on Markovian kernels")
    assert res4.directive_modality == DirectiveModality.ACADEMIC_ARTICLE

    # 5. Non-Consensus / Contrarian
    res5 = decomposer.decompose("Write a non-consensus contrarian breakdown challenging the mainstream consensus on machine consciousness")
    assert res5.directive_modality == DirectiveModality.NON_CONSENSUS_CONTRARIAN

    # 6. Viral Public Narrative
    res6 = decomposer.decompose("Write a viral Twitter thread and engaging Substack post explaining this paper")
    assert res6.directive_modality == DirectiveModality.VIRAL_PUBLIC_NARRATIVE

    # 7. Formula Extraction
    res7 = decomposer.decompose("Extract all the mathematical formulas and LaTeX equations from this document")
    assert res7.directive_modality == DirectiveModality.FORMULA_EXTRACTION

    # 8. Comprehensive Overview
    res8 = decomposer.decompose("Provide a comprehensive overview and deep treatise breakdown of this whitepaper")
    assert res8.directive_modality == DirectiveModality.COMPREHENSIVE_OVERVIEW

    # 9. URL Extraction
    res_url = decomposer.decompose("Analyze the findings at https://arxiv.org/abs/1406.5777 and compare with https://example.com/paper")
    assert len(res_url.detected_urls) == 2
    assert "https://arxiv.org/abs/1406.5777" in res_url.detected_urls
    assert res_url.directive_modality == DirectiveModality.MULTI_DOCUMENT_COMPARISON


def test_cognitive_directive_registry_synthesizers():
    registry = CognitiveDirectiveRegistry()

    # Multi-doc comparison
    dir_comp = registry.synthesize_directive(DirectiveModality.MULTI_DOCUMENT_COMPARISON, "Hoffman.pdf & CIMC.pdf")
    assert "MULTI-SOURCE COMPARATIVE" in dir_comp
    assert "HOFFMAN.PDF & CIMC.PDF" in dir_comp
    assert "STRICT FACTUAL GROUNDING LAWS" in dir_comp

    # Critical analysis
    dir_crit = registry.synthesize_directive(DirectiveModality.CRITICAL_ANALYSIS, "Quantum Realism")
    assert "CRITICAL ANALYSIS, DIALECTICAL AUDIT" in dir_crit
    assert "QUANTUM REALISM" in dir_crit

    # Non-consensus contrarian
    dir_contr = registry.synthesize_directive(DirectiveModality.NON_CONSENSUS_CONTRARIAN, "Deep Learning AGI")
    assert "NON-CONSENSUS CONTRARIAN THESIS" in dir_contr

    # Viral narrative
    dir_viral = registry.synthesize_directive(DirectiveModality.VIRAL_PUBLIC_NARRATIVE, "Objects of Consciousness")
    assert "HIGH-IMPACT VIRAL ESSAY" in dir_viral

    # Artifact metadata check
    cat_comp, _ = registry.get_artifact_metadata(DirectiveModality.MULTI_DOCUMENT_COMPARISON, "Paper")
    assert cat_comp == "comparisons"

    cat_crit, _ = registry.get_artifact_metadata(DirectiveModality.CRITICAL_ANALYSIS, "Paper")
    assert cat_crit == "critiques"

    cat_art, _ = registry.get_artifact_metadata(DirectiveModality.ACADEMIC_ARTICLE, "Paper")
    assert cat_art == "articles"

    cat_contr, _ = registry.get_artifact_metadata(DirectiveModality.NON_CONSENSUS_CONTRARIAN, "Paper")
    assert cat_contr == "contrarian"


@pytest.mark.asyncio
async def test_url_grounding_live_extraction(temp_hlsm_manager):
    from backend import services
    services.hlsm_manager = temp_hlsm_manager

    with patch("backend.ingestion_services.scraper.fetch_and_extract_markdown", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (
            "# California Institute for Machine Consciousness\n\n"
            "The CIMC Whitepaper introduces empirical benchmarks for autonomous subjective agency and Markov Trace filters."
        )

        test_url = "https://cimc.ai/whitepaper"
        grounding, shas, titles = await _check_url_grounding([test_url])

        assert grounding is not None
        assert "VERIFIED REAL-TIME URL SOURCE GROUNDING" in grounding
        assert test_url in grounding
        assert len(shas) == 1
        assert "California Institute for Machine Consciousness" in titles[0]


@pytest.mark.asyncio
async def test_multi_document_grounding_isolation(temp_hlsm_manager):
    from backend import services
    services.hlsm_manager = temp_hlsm_manager

    # Ingest Document 1 (Hoffman)
    await temp_hlsm_manager.ingest_document_payload(
        filename="Hoffman_Objects of Consciousness.pdf",
        content="--- [DOCUMENT: Hoffman_Objects of Consciousness.pdf | PAGE 1/1] ---\nConscious Realism agent formalism 7-tuple.",
        session_key="test_session"
    )

    # Ingest Document 2 (CIMC)
    await temp_hlsm_manager.ingest_document_payload(
        filename="CIMC_Whitepaper.pdf",
        content="--- [DOCUMENT: CIMC_Whitepaper.pdf | PAGE 1/1] ---\nMachine consciousness empirical tests and IIT Phi.",
        session_key="test_session"
    )

    prompt = "Please compare the Hoffman_Objects of Consciousness.pdf with the CIMC_Whitepaper.pdf"
    grounding, sha, label = await _check_document_grounding(prompt)

    assert grounding is not None
    assert "Hoffman" in grounding
    assert "CIMC" in grounding
    assert "AUTHENTIC SOURCE DOCUMENT" in grounding


@pytest.mark.asyncio
async def test_dynamic_artifact_packaging_modalities(tmp_path):
    # 1. Test Multi-Doc Comparison packaging
    comp_response = (
        "# Comparative Analysis: Conscious Realism vs. Integrated Information Theory\n\n"
        "## 1. Ontological Foundations\n"
        "Hoffman posits conscious agents as fundamental, whereas IIT posits integrated information Phi."
    )
    comp_prompt = "Compare Hoffman with CIMC in a comprehensive comparative dossier"
    await _process_dynamic_artifact_block(comp_response, comp_prompt, output_dir=str(tmp_path))

    import glob
    matching_comp = glob.glob(f"{str(tmp_path)}/comparisons/*_comparative_analysis*")
    assert len(matching_comp) >= 1
    assert os.path.exists(os.path.join(matching_comp[-1], "metadata.json"))
    assert os.path.exists(os.path.join(matching_comp[-1], "source.html"))

    # 2. Test Critique packaging
    crit_response = (
        "# Critical Epistemic Audit of the Free Energy Principle\n\n"
        "## 1. Boundary Condition Vulnerabilities\n"
        "FEP assumes ergodic Markov blankets which may not hold in non-stationary evolutionary regimes."
    )
    crit_prompt = "Critique the FEP whitepaper and highlight all unstated assumptions"
    await _process_dynamic_artifact_block(crit_response, crit_prompt, output_dir=str(tmp_path))

    matching_crit = glob.glob(f"{str(tmp_path)}/critiques/*_critical_epistemic*")
    assert len(matching_crit) >= 1
    assert os.path.exists(os.path.join(matching_crit[-1], "metadata.json"))
