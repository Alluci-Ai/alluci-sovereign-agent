import pytest
from backend.engine.intent_decomposer import (
    IntentDecomposer, 
    DirectiveModality, 
    ConversationalBandwidth, 
    DocumentGenre,
    detect_document_genre,
    detect_conversational_bandwidth
)
from backend.engine.directive_registry import CognitiveDirectiveRegistry

def test_exhaustive_academic_intent_classification():
    decomposer = IntentDecomposer()
    prompt = (
        "write a full comprehensive and exhaustive, publication-grade academic analysis, and explanation "
        "covering the foundational thesis, core frameworks, chapter corridors, formal mathematics, supporting "
        "figure image diagrams and strategic implications strictly grounded in this Hoffman_Objects of Consciousness document."
    )
    goal = decomposer.decompose(prompt)
    
    assert goal.directive_modality in [DirectiveModality.COMPREHENSIVE_OVERVIEW, DirectiveModality.ACADEMIC_ARTICLE], (
        f"Expected COMPREHENSIVE_OVERVIEW or ACADEMIC_ARTICLE, got {goal.directive_modality}"
    )
    assert goal.detected_bandwidth == ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    assert goal.detected_genre == DocumentGenre.SCIENTIFIC_MATHEMATICAL


def test_formula_only_intent_classification():
    decomposer = IntentDecomposer()
    prompt = "Extract only the formulas, equations, and mathematical kernels from this paper."
    goal = decomposer.decompose(prompt)
    
    assert goal.directive_modality == DirectiveModality.FORMULA_EXTRACTION


def test_research_monograph_directive_contains_figure_embedding_and_math():
    registry = CognitiveDirectiveRegistry()
    directive = registry.synthesize_directive(
        DirectiveModality.COMPREHENSIVE_OVERVIEW,
        "Hoffman_Objects of Consciousness.pdf",
        document_genre=DocumentGenre.SCIENTIFIC_MATHEMATICAL,
        conversational_bandwidth=ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    )
    
    assert "10-Layer Publication Monograph Architecture" in directive
    assert "Supporting Technical Figure Walkthroughs" in directive
    assert "![Caption](/api/v1/artifacts/extracted_figures/...)" in directive
    assert "Formal Mathematical State Space Modeling" in directive
    assert "Epistemic Status Classification Matrix" in directive


def test_universal_generalizability_across_genres():
    registry = CognitiveDirectiveRegistry()
    
    # Financial Monograph
    fin_dir = registry.synthesize_directive(
        DirectiveModality.COMPREHENSIVE_OVERVIEW,
        "Q3_Financials.pdf",
        document_genre=DocumentGenre.BUSINESS_FINANCIAL,
        conversational_bandwidth=ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    )
    assert "8-Layer Strategic & Financial Analysis Architecture" in fin_dir
    assert "Unit Economics" in fin_dir

    # Engineering Monograph
    eng_dir = registry.synthesize_directive(
        DirectiveModality.COMPREHENSIVE_OVERVIEW,
        "System_Architecture_RFC.md",
        document_genre=DocumentGenre.ENGINEERING_SYSTEMS,
        conversational_bandwidth=ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    )
    assert "8-Layer Systems Architecture Blueprint" in eng_dir
    assert "Fault Tolerance" in eng_dir
