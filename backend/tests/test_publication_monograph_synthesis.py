import pytest
import os
import json
import tempfile
import asyncio
from backend.memory.hlsm_manager import _extract_formal_concepts
from backend.engine.intent_decomposer import DirectiveModality
from backend.engine.directive_registry import CognitiveDirectiveRegistry
from backend.routers.gemini import _build_html5_research_dossier, _process_dynamic_artifact_block


def test_dynamic_formula_extraction_no_hardcoded_contamination():
    """Verify that _extract_formal_concepts does not inject hardcoded Tononi Phi or Friston F."""
    # Text that mentions IIT and FEP without giving formulas
    sample_text = (
        "In this chapter we review Integrated Information Theory (IIT) and the Free Energy Principle (FEP). "
        "We argue that both frameworks have conceptual limitations when applied to synthetic agents."
    )
    concepts = _extract_formal_concepts(sample_text, "test_doc.pdf", page_num=5)
    
    # Assert zero hardcoded formulas were injected
    for c in concepts:
        assert "\\Phi = \\min" not in c.get("math_formula", "")
        assert "D_{\\text{KL}}" not in c.get("math_formula", "")
        assert "F = \\mathbb{E}" not in c.get("math_formula", "")


def test_dynamic_formula_extraction_genuine_tuples_and_mappings():
    """Verify that authentic tuples and mappings in page text are dynamically extracted."""
    page_text = (
        "Definition 1: Conscious Agent.\n"
        "A conscious agent is defined by the tuple C = ((X, \\mathcal{X}), (G, \\mathcal{G}), P, D, A, N). "
        "Where the perception kernel is defined as P: W \\times \\mathcal{X} \\to [0,1].\n"
        "Theorem 2: Combination of Agents.\n"
        "Any two conscious agents can be combined into a single unified conscious agent."
    )
    concepts = _extract_formal_concepts(page_text, "hoffman.pdf", page_num=3)
    
    assert len(concepts) >= 1
    found_tuple = any("C = (" in c.get("math_formula", "") or "C = (" in c.get("formal_definition", "") for c in concepts)
    found_mapping = any("P:" in c.get("math_formula", "") or "P:" in c.get("name", "") for c in concepts)
    assert found_tuple or found_mapping


def test_cognitive_directive_registry_10_layer_architecture():
    """Verify that ComprehensiveOverviewStrategy enforces the 10-layer monograph requirements."""
    registry = CognitiveDirectiveRegistry()
    directive = registry.synthesize_directive(DirectiveModality.COMPREHENSIVE_OVERVIEW, "CIMC Hypothesis")
    
    # Assert critical 10-layer components are present in the directive
    assert "10-Layer Publication Monograph Architecture" in directive
    assert "Source Boundary & Epistemic Declaration" in directive
    assert "Abstract & Core Ontological Inversion" in directive
    assert "Epistemic Status Classification Matrix" in directive
    assert "Formal Mathematical State Space Modeling" in directive
    assert "LaTeX display math" in directive or "LaTeX" in directive
    assert "Domain-to-Domain Isomorphism Alignment Tables" in directive
    assert "Taxonomical Decompositions & Logical Non-Implications" in directive
    assert "Dialectical Paradigm Audits" in directive
    assert "Concrete Experimental Platforms" in directive
    assert "Empirical Falsification Criteria" in directive
    assert "Condensed Formal Mathematical Spine" in directive


def test_formula_extraction_directive_enforces_latex_and_isomorphisms():
    """Verify that FormulaExtractionStrategy directs active LaTeX derivations and isomorphism tables."""
    registry = CognitiveDirectiveRegistry()
    directive = registry.synthesize_directive(DirectiveModality.FORMULA_EXTRACTION, "Hoffman Objects of Consciousness")
    
    assert "MATHEMATICAL FORMALISM & DERIVATION MONOGRAPH" in directive
    assert "LaTeX" in directive
    assert "Domain-to-Domain Isomorphism Mapping Tables" in directive
    assert "Condensed Formal Mathematical Spine" in directive


def test_build_html5_research_dossier_katex_and_table_rendering():
    """Verify that _build_html5_research_dossier produces valid HTML5 with KaTeX and rendered tables."""
    title = "Test Monograph on Consciousness"
    markdown_content = (
        "# Test Monograph\n\n"
        "## Abstract\n\n"
        "We formalize the core state space $\\mathcal{S}$ and transition operator $\\mathcal{T}$.\n\n"
        "$$\\min_{\\theta} \\mathcal{V}(M) \\iff \\max \\mathcal{C}(M)$$\n\n"
        "### Epistemic Status Matrix\n\n"
        "| Proposition | Epistemic Status |\n"
        "| :--- | :--- |\n"
        "| Conscious Agent 6-tuple | Formal Definition |\n"
        "| Agent Join Theorem | Theorem 1 (Proven) |\n\n"
        "> The architect is not the sovereign.\n\n"
        "- First component: $X$\n"
        "- Second component: $G$\n"
    )
    html_output = _build_html5_research_dossier(title, markdown_content)
    
    assert "<!DOCTYPE html>" in html_output
    assert "katex.min.css" in html_output
    assert "auto-render.min.js" in html_output
    assert "<h1>Test Monograph</h1>" in html_output
    assert "<table>" in html_output
    assert "<th>Proposition</th>" in html_output
    assert "<blockquote>" in html_output
    assert "<ul>" in html_output
    assert "<li>First component: $X$</li>" in html_output


@pytest.mark.asyncio
async def test_process_dynamic_artifact_block_sandboxed_triad():
    """Verify atomic triad generation in a sandboxed directory."""
    with tempfile.TemporaryDirectory() as sandbox_dir:
        sample_response = (
            "# Objects of Consciousness — Comprehensive Treatise\n\n"
            "## 1. Executive Abstract\n"
            "This monograph formalizes the conscious agent architecture.\n\n"
            "$$\\mathcal{L}(e, B) = \\int_B A_2 D_1 A_1 D_2$$\n"
        )
        prompt = "Synthesize an exhaustive, publication-grade academic analysis of Hoffman Objects of Consciousness"
        
        await _process_dynamic_artifact_block(sample_response, prompt, output_dir=sandbox_dir)
        
        # Check that artifacts directory contains the category and triad bundle
        cat_dir = os.path.join(sandbox_dir, "research")
        assert os.path.exists(cat_dir)
        
        subdirs = os.listdir(cat_dir)
        assert len(subdirs) >= 1
        
        bundle_dir = os.path.join(cat_dir, subdirs[0])
        assert os.path.exists(os.path.join(bundle_dir, "metadata.json"))
        assert os.path.exists(os.path.join(bundle_dir, "source.md"))
        assert os.path.exists(os.path.join(bundle_dir, "source.html"))
        
        with open(os.path.join(bundle_dir, "metadata.json"), "r", encoding="utf-8") as mf:
            meta = json.load(mf)
            assert meta["category"] == "research"
            assert "triad_bundle" in meta
        
        with open(os.path.join(bundle_dir, "source.html"), "r", encoding="utf-8") as hf:
            html_text = hf.read()
            assert "katex" in html_text
