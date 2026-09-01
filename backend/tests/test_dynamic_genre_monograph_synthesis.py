import pytest
import os
import json
import tempfile
from backend.engine.intent_decomposer import (
    IntentDecomposer,
    DirectiveModality,
    DocumentGenre,
    ConversationalBandwidth,
    detect_document_genre,
    detect_conversational_bandwidth,
)
from backend.engine.directive_registry import CognitiveDirectiveRegistry
from backend.routers.gemini import _process_dynamic_artifact_block


def test_document_genre_detection_scientific():
    """Verify that scientific papers, LaTeX math, and formal theorems are classified as SCIENTIFIC_MATHEMATICAL."""
    sci_text = (
        "We formalize the conscious agent tuple C = ((X, \\mathcal{X}), (G, \\mathcal{G}), P, D, A, N). "
        "The perception kernel P: W \\times \\mathcal{X} \\to [0,1] is a Markovian transition operator. "
        "Theorem 1 proves that the asymptotic dynamics converge to a stationary manifold."
    )
    genre = detect_document_genre(sci_text, filename="hoffman_paper.pdf", raw_prompt="Analyze the mathematical state spaces")
    assert genre == DocumentGenre.SCIENTIFIC_MATHEMATICAL


def test_document_genre_detection_biomedical_clinical():
    """Verify that clinical trials, pharmacology, and oncology reports are classified as BIOMEDICAL_CLINICAL."""
    bio_text = (
        "In this Phase III randomized controlled clinical trial, we evaluated overall survival (OS) and progression-free survival (PFS). "
        "The Hazard Ratio (HR) was 0.68 (95% CI 0.54-0.85, p < 0.001). "
        "Treatment-emergent adverse events (TEAEs) of Grade 3 or higher occurred in 14% of patients."
    )
    genre = detect_document_genre(bio_text, filename="Keynote_Phase3_Trial.pdf", raw_prompt="Evaluate clinical trial efficacy and toxicity endpoints")
    assert genre == DocumentGenre.BIOMEDICAL_CLINICAL


def test_document_genre_detection_business_financial():
    """Verify that financial statements, SEC filings, and pitch decks are classified as BUSINESS_FINANCIAL."""
    biz_text = (
        "In Q3, the company generated $42M in ARR with an 84% Gross Margin and 125% Net Retention. "
        "Customer Acquisition Cost (CAC) was $12,500 against an LTV of $85,000, yielding a 6.8x LTV/CAC ratio. "
        "The current monthly burn rate of $1.2M provides 28 months of runway on the existing balance sheet."
    )
    genre = detect_document_genre(biz_text, filename="Q3_Financial_Model.xlsx", raw_prompt="Evaluate unit economics and valuation")
    assert genre == DocumentGenre.BUSINESS_FINANCIAL


def test_document_genre_detection_legal_regulatory():
    """Verify that contracts, MSAs, NDAs, and statutory audits are classified as LEGAL_REGULATORY."""
    legal_text = (
        "This Master Services Agreement ('Agreement') contains affirmative covenants and indemnification obligations. "
        "Section 8 limits total liability to the aggregate fees paid in the preceding 12 months, with carve-outs for gross negligence. "
        "Disputes shall be settled by binding arbitration in Delaware under Delaware General Corporation Law."
    )
    genre = detect_document_genre(legal_text, filename="Enterprise_MSA_v2.docx", raw_prompt="Review legal liabilities and covenants")
    assert genre == DocumentGenre.LEGAL_REGULATORY


def test_document_genre_detection_engineering_systems():
    """Verify that engineering RFCs, microservice topologies, and API specs are classified as ENGINEERING_SYSTEMS."""
    eng_text = (
        "RFC 402: Distributed Event Ingestion Pipeline. "
        "The system enforces a 99.99% availability SLA with P99 latency under 25ms at 50,000 RPS. "
        "Kafka brokers stream events to Redis cluster caches, with circuit breakers and failover clusters protecting gRPC endpoints."
    )
    genre = detect_document_genre(eng_text, filename="rfc_402_pipeline.md", raw_prompt="Review systems architecture and latency budgets")
    assert genre == DocumentGenre.ENGINEERING_SYSTEMS


def test_document_genre_detection_strategic_policy():
    """Verify that public policy documents, institutional charters, and geopolitical analyses are classified as STRATEGIC_POLICY."""
    policy_text = (
        "This institutional whitepaper addresses public policy governance for sovereign AI infrastructure. "
        "We evaluate stakeholder impact across labor markets, regulatory oversight mechanisms, and treaty agreements for international compliance."
    )
    genre = detect_document_genre(policy_text, filename="AI_Governance_Charter.pdf", raw_prompt="Analyze public policy and stakeholder impact")
    assert genre == DocumentGenre.STRATEGIC_POLICY


def test_document_genre_detection_educational_pedagogical():
    """Verify that curricula, tutorials, and masterclasses are classified as EDUCATIONAL_PEDAGOGICAL."""
    edu_text = (
        "Curriculum Overview: Deep Learning from First Principles. "
        "Learning Objectives include understanding backpropagation via worked examples and overcoming common misconceptions in gradient descent. "
        "Includes active recall exercises, quiz rubrics, and step-by-step problem sets."
    )
    genre = detect_document_genre(edu_text, filename="CS231_Curriculum_Syllabus.pdf", raw_prompt="Design a step-by-step tutorial with practice problems")
    assert genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL


def test_document_genre_detection_narrative_literary():
    """Verify that literary works, memoirs, and novels are classified as NARRATIVE_LITERARY."""
    lit_text = (
        "In Chapter 4 of the novel, the protagonist navigates an existential dilemma in post-war Prague. "
        "The thematic motif of recursive mirrors reflects the psychological alienation and emotional arc of the character."
    )
    genre = detect_document_genre(lit_text, filename="The_Silent_Echo.epub", raw_prompt="Explore the thematic motifs and narrative arc")
    assert genre == DocumentGenre.NARRATIVE_LITERARY


def test_conversational_bandwidth_detection():
    """Verify the 5-Tier Conversational Bandwidth classifier."""
    # 1. Direct Precision QA
    bw_qa = detect_conversational_bandwidth("What is the formula for the perception kernel in Hoffman 2014?")
    assert bw_qa == ConversationalBandwidth.DIRECT_PRECISION_QA
    
    bw_ebitda = detect_conversational_bandwidth("What was the EBITDA margin in Q3?")
    assert bw_ebitda == ConversationalBandwidth.DIRECT_PRECISION_QA

    # 2. Executive Briefing
    bw_brief = detect_conversational_bandwidth("Give me an executive summary and TL;DR of this quarter's numbers")
    assert bw_brief == ConversationalBandwidth.EXECUTIVE_BRIEFING

    # 3. Exhaustive Monograph
    bw_mono = detect_conversational_bandwidth("Synthesize an exhaustive academic monograph on the CIMC whitepaper")
    assert bw_mono == ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH

    # 4. Natural Conversation
    bw_nat = detect_conversational_bandwidth("Hi! What do you think about the concept of synthetic consciousness? Let's discuss.")
    assert bw_nat == ConversationalBandwidth.NATURAL_CONVERSATION


def test_scientific_monograph_synthesis_architecture():
    """Verify that scientific documents receive the 10-layer publication monograph with exact math and open limits."""
    registry = CognitiveDirectiveRegistry()
    directive = registry.synthesize_directive(
        DirectiveModality.COMPREHENSIVE_OVERVIEW,
        "Hoffman Objects of Consciousness",
        document_genre=DocumentGenre.SCIENTIFIC_MATHEMATICAL
    )
    
    assert "10-Layer Publication Monograph Architecture" in directive
    assert "Source Boundary & Epistemic Declaration" in directive
    assert "Abstract & Core Ontological Inversion" in directive
    assert "Epistemic Status Classification Matrix" in directive
    assert "Formal Mathematical State Space Modeling & Exact Derivations" in directive
    assert "Domain-to-Domain Isomorphism Alignment Tables" in directive
    assert "Taxonomical Decompositions & Logical Non-Implications" in directive
    assert "Dialectical Paradigm Audits" in directive
    assert "Concrete Experimental Platforms & Distributed Architectures" in directive
    assert "Empirical Falsification Criteria, Staged Roadmap & Explicit Catalog of Unresolved Open Limits" in directive
    assert "Ethical Asymmetry, Governance & Condensed Formal Mathematical Spine" in directive
    assert "Universal Hybrid Standard" in directive


def test_biomedical_clinical_monograph_synthesis_architecture():
    """Verify that biomedical/clinical documents receive the 8-layer clinical trial analysis architecture."""
    registry = CognitiveDirectiveRegistry()
    directive = registry.synthesize_directive(
        DirectiveModality.COMPREHENSIVE_OVERVIEW,
        "Keynote-042 Clinical Study",
        document_genre=DocumentGenre.BIOMEDICAL_CLINICAL
    )
    
    assert "8-Layer Biomedical & Clinical Architecture" in directive
    assert "Trial Protocol, Primary Endpoints & Evidentiary Scope" in directive
    assert "Patient Cohort, Baseline Demographics & Stratification Matrix" in directive
    assert "Efficacy & Statistical Outcomes Matrix" in directive
    assert "Safety Profile, Adverse Events (AEs/SAEs) & Toxicity Matrix" in directive
    assert "Pharmacokinetics, Pharmacodynamics & Molecular Mechanism Deep-Dive" in directive
    assert "Standard-of-Care Concordance & Comparative Therapeutics Matrix" in directive
    assert "Trial Limitations, Confounding Biases & Subgroup Vulnerabilities Table" in directive
    assert "Translational Roadmap, Regulatory Milestones & Clinical Bottom Line" in directive
    assert "Universal Hybrid Standard" in directive


def test_business_financial_monograph_synthesis_architecture():
    """Verify that financial documents receive the 8-layer financial analysis architecture with unit economics & moats."""
    registry = CognitiveDirectiveRegistry()
    directive = registry.synthesize_directive(
        DirectiveModality.COMPREHENSIVE_OVERVIEW,
        "Q3 Venture Model",
        document_genre=DocumentGenre.BUSINESS_FINANCIAL
    )
    
    assert "8-Layer Strategic & Financial Analysis Architecture" in directive
    assert "Executive Thesis, Strategic Positioning & Core Value Proposition" in directive
    assert "Market Opportunity (TAM/SAM/SOM) & Customer Segmentation Matrix" in directive
    assert "Unit Economics, Margin Structure & Financial Performance Table" in directive
    assert "Competitive Moats, Network Effects & Defensibility Flywheel" in directive
    assert "Capital Allocation, Runway & Scenario Sensitivity Analysis Table" in directive
    assert "Competitor Landscape & Feature/Pricing Differentiation Matrix" in directive
    assert "Critical Unmitigated Risks, Concentration Hazards & Macro Mitigation Table" in directive
    assert "Strategic Execution Roadmap & Quantitative Milestone Ledger" in directive
    assert "Universal Hybrid Standard" in directive


def test_educational_pedagogical_curriculum_synthesis_architecture():
    """Verify that educational documents receive the 8-layer pedagogical architecture."""
    registry = CognitiveDirectiveRegistry()
    directive = registry.synthesize_directive(
        DirectiveModality.COMPREHENSIVE_OVERVIEW,
        "CS231 Advanced Deep Learning",
        document_genre=DocumentGenre.EDUCATIONAL_PEDAGOGICAL
    )
    
    assert "8-Layer Pedagogical Architecture" in directive
    assert "Learning Objectives, Core Intuition & Concept Map" in directive
    assert "Prerequisites & Knowledge Dependency Matrix" in directive
    assert "Visual Analogies, Mental Models & Intuitive Scaffolding" in directive
    assert "Step-by-Step Worked Derivations & Problem Walkthroughs Table" in directive
    assert "Common Misconceptions, Pitfalls & Diagnostic Matrix" in directive
    assert "Active Recall Exercises, Scaffolding Questions & Practice Problems" in directive
    assert "Real-World Applications & Cross-Disciplinary Case Studies Table" in directive
    assert "Mastery Assessment Rubric & Self-Evaluation Ledger" in directive


def test_bandwidth_directive_synthesis_modes():
    """Verify that directives adapt to Conversational Bandwidth tiers."""
    registry = CognitiveDirectiveRegistry()
    
    # 1. Direct Precision QA
    dir_qa = registry.synthesize_directive(
        DirectiveModality.CONCEPTUAL_QA, "Hoffman Paper",
        conversational_bandwidth=ConversationalBandwidth.DIRECT_PRECISION_QA
    )
    assert "INSTRUCTION: Answer the User Directive directly, factually, and concisely" in dir_qa
    assert "Zero fluff" in dir_qa

    # 2. Executive Briefing
    dir_brief = registry.synthesize_directive(
        DirectiveModality.COMPREHENSIVE_OVERVIEW, "Q3 Earnings",
        conversational_bandwidth=ConversationalBandwidth.EXECUTIVE_BRIEFING
    )
    assert "HIGH-DENSITY EXECUTIVE BRIEFING" in dir_brief
    assert "Key Metrics, Trade-offs & Critical Risks Matrix" in dir_brief

    # 3. Natural Conversation
    dir_nat = registry.synthesize_directive(
        DirectiveModality.CONCEPTUAL_QA, "General Discussion",
        conversational_bandwidth=ConversationalBandwidth.NATURAL_CONVERSATION
    )
    assert "NATURAL CONVERSATIONAL DIALOGUE" in dir_nat
    assert "DO NOT force unprompted markdown table stubs" in dir_nat


def test_artifact_category_and_title_resolution_per_genre():
    """Verify that artifact categories and titles dynamically map across all 9 genres."""
    registry = CognitiveDirectiveRegistry()
    
    # Clinical
    cat_bio, title_bio = registry.get_artifact_metadata(
        DirectiveModality.COMPREHENSIVE_OVERVIEW, "Keynote Study", document_genre=DocumentGenre.BIOMEDICAL_CLINICAL
    )
    assert cat_bio == "clinical"
    assert "Clinical Monograph" in title_bio
    
    # Educational
    cat_edu, title_edu = registry.get_artifact_metadata(
        DirectiveModality.COMPREHENSIVE_OVERVIEW, "Linear Algebra", document_genre=DocumentGenre.EDUCATIONAL_PEDAGOGICAL
    )
    assert cat_edu == "education"
    assert "Pedagogical Curriculum" in title_edu
    
    # Financial
    cat_fin, title_fin = registry.get_artifact_metadata(
        DirectiveModality.COMPREHENSIVE_OVERVIEW, "Q3 Earnings", document_genre=DocumentGenre.BUSINESS_FINANCIAL
    )
    assert cat_fin == "finance"
    
    # Legal
    cat_leg, title_leg = registry.get_artifact_metadata(
        DirectiveModality.COMPREHENSIVE_OVERVIEW, "MSA Agreement", document_genre=DocumentGenre.LEGAL_REGULATORY
    )
    assert cat_leg == "legal"


@pytest.mark.asyncio
async def test_multi_genre_dynamic_artifact_triad_persistence():
    """Verify that multi-genre responses are correctly routed and persisted as atomic triad bundles."""
    with tempfile.TemporaryDirectory() as sandbox_dir:
        # 1. Clinical trial report
        bio_response = (
            "# Phase III Clinical Study on Biomarker Efficacy\n\n"
            "## Efficacy Outcomes\n"
            "| Metric | Result |\n"
            "| :--- | :--- |\n"
            "| Hazard Ratio | 0.65 |\n"
            "| Median OS | 24.2 months |\n"
            "| 12-month PFS | 68% |\n"
        )
        bio_prompt = "Synthesize an exhaustive clinical trial monograph analyzing survival endpoints and adverse event toxicity"
        await _process_dynamic_artifact_block(bio_response, bio_prompt, output_dir=sandbox_dir)
        
        bio_cat_dir = os.path.join(sandbox_dir, "clinical")
        assert os.path.exists(bio_cat_dir)
        bio_subdirs = os.listdir(bio_cat_dir)
        assert len(bio_subdirs) >= 1
        bio_bundle = os.path.join(bio_cat_dir, bio_subdirs[0])
        assert os.path.exists(os.path.join(bio_bundle, "metadata.json"))
        assert os.path.exists(os.path.join(bio_bundle, "source.md"))
        assert os.path.exists(os.path.join(bio_bundle, "source.html"))
        with open(os.path.join(bio_bundle, "metadata.json"), "r") as f:
            meta = json.load(f)
            assert meta["category"] == "clinical"

        # 2. Financial report
        fin_response = (
            "# Q3 Executive Financial Monograph\n\n"
            "## Unit Economics\n"
            "| Metric | Value |\n"
            "| :--- | :--- |\n"
            "| ARR | $45M |\n"
            "| Gross Margin | 82% |\n"
            "| Net Retention | 128% |\n"
        )
        fin_prompt = "Synthesize an exhaustive strategic analysis of the Q3 EBITDA and revenue numbers"
        await _process_dynamic_artifact_block(fin_response, fin_prompt, output_dir=sandbox_dir)
        
        fin_cat_dir = os.path.join(sandbox_dir, "finance")
        assert os.path.exists(fin_cat_dir)
        fin_subdirs = os.listdir(fin_cat_dir)
        assert len(fin_subdirs) >= 1
        fin_bundle = os.path.join(fin_cat_dir, fin_subdirs[0])
        assert os.path.exists(os.path.join(fin_bundle, "metadata.json"))
        assert os.path.exists(os.path.join(fin_bundle, "source.md"))
        assert os.path.exists(os.path.join(fin_bundle, "source.html"))
        with open(os.path.join(fin_bundle, "metadata.json"), "r") as f:
            meta = json.load(f)
            assert meta["category"] == "finance"
