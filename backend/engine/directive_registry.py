"""
Cognitive Directive Registry & Adaptive Prompt Synthesis Engine
================================================================
Implements dynamic, intent-adaptive prompt directive synthesizers and artifact metadata strategies
across all 9 Cognitive Directive Modalities (G), 9 Document Epistemic Genres, and 5 Conversational Bandwidth Tiers.
Zero hardcoding, parameterized source provenance, and strict grounding laws.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from .intent_decomposer import DirectiveModality, DocumentGenre, ConversationalBandwidth


class BaseDirectiveStrategy(ABC):
    """Abstract Strategy for synthesizing dynamic cognitive directives."""

    @abstractmethod
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        """Constructs the authoritative prompt directive instruction."""
        pass

    @abstractmethod
    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        """Returns the artifact directory category (e.g. comparisons, critiques, articles, narratives, finance, legal, clinical, education)."""
        pass

    @abstractmethod
    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        """Returns a publication-grade fallback title for generated artifact triads."""
        pass


class MultiDocumentComparisonStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        if conversational_bandwidth == ConversationalBandwidth.DIRECT_PRECISION_QA:
            return (
                f"INSTRUCTION FOR DIRECT PRECISION COMPARISON ({source_label.upper()}):\n"
                "Provide a direct, razor-sharp comparative answer contrasting the specified sources.\n"
                "State the exact differences, values, or formula discrepancies immediately in a clear comparison table or bullet points.\n"
                "Follow with 1 concise explanatory paragraph strictly derived from authentic source evidence. Zero fluff."
            )
        elif conversational_bandwidth == ConversationalBandwidth.EXECUTIVE_BRIEFING:
            return (
                f"INSTRUCTION FOR HIGH-DENSITY EXECUTIVE COMPARATIVE BRIEFING ({source_label.upper()}):\n"
                "Provide a high-signal executive comparative briefing strictly derived from the authentic source documents.\n"
                "1. Core Comparative Divergence: Boxed contrast of foundational theses (\\boxed{\\text{Source A}} \\text{ vs } \\boxed{\\text{Source B}}).\n"
                "2. Strategic Trade-offs & Feature Matrix: High-density Markdown table comparing key parameters, metrics, or covenants.\n"
                "3. Strategic Decision Ledger: Numbered actionable takeaways and bottom-line verdict.\n"
                "Ground all claims strictly in authentic source text."
            )

        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return (
                f"INSTRUCTION FOR STRATEGIC & FINANCIAL COMPARATIVE DOSSIER ({source_label.upper()}):\n"
                "Author an exhaustive, publication-grade comparative business and financial analysis contrasting the provided sources.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth analytical paragraphs directly below.\n"
                "1. Executive Comparative Thesis & Strategic Positioning: Contrast foundational value propositions and market vectors in display boxes (\\boxed{A \\to B}).\n"
                "2. Comparative Market & Customer Segmentation Matrix: Markdown table comparing TAM/SAM/SOM, ICPs, and target customer segments.\n"
                "3. Financial Metrics & Unit Economics Comparison Table: Compare ARR, CAC, LTV, Gross Margins, Net Retention, Payback Periods, and Burn Rates.\n"
                "4. Competitive Moats & Defensibility Matrix: Deep audit of network effects, switching costs, proprietary data, and scale economies.\n"
                "5. Capital Efficiency & Runway Sensitivity Analysis Table: Scenario modeling across both frameworks.\n"
                "6. Strategic Friction & Trade-Off Matrix: Direct comparative analysis of execution risks, platform dependencies, and vulnerabilities.\n"
                "7. Comparative Execution Roadmaps & Milestone Ledgers: Contrasting quarter-by-quarter rollouts.\n"
                "8. Definitive Strategic Verdict & Synthesis: Bottom-line executive recommendation.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all financial figures and market claims strictly in the authentic reference data.\n"
                "2. DO NOT fabricate unstated financial ratios or metrics."
            )
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return (
                f"INSTRUCTION FOR COMPARATIVE LEGAL & REGULATORY AUDIT ({source_label.upper()}):\n"
                "Author an exhaustive, publication-grade comparative legal audit contrasting the provided agreements, covenants, or regulatory frameworks.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth legal analysis paragraphs directly below.\n"
                "1. Scope, Purpose & Jurisdictional Alignment: Executive summary contrasting legal scopes and governing jurisdictions.\n"
                "2. Comparative Rights & Covenants Matrix: Side-by-side Markdown table detailing affirmative, negative, and operational obligations.\n"
                "3. Liability, Indemnification & Risk Allocation Table: Comparative analysis of liability caps, indemnification triggers, and consequential damages carve-outs.\n"
                "4. Termination, Default & Breach Comparison: Contrasting cure periods, convenience vs. cause triggers, and transition covenants.\n"
                "5. Ambiguity & Exposure Audit Table: Isolating conflicting schedules, cross-indemnity risks, and asymmetric terms.\n"
                "6. Statutory & Regulatory Precedent Alignment Matrix: Evaluating alignment with relevant statutory bodies (e.g. GDPR, HIPAA, UCC, SEC).\n"
                "7. Dispute Resolution & Governing Law Comparison: Forum selection, arbitration rules, and fee-shifting provisions.\n"
                "8. Actionable Redline Reconciliation Ledger: Harmonized redline recommendations.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground every clause and legal claim strictly in the authentic reference text."
            )
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return (
                f"INSTRUCTION FOR COMPARATIVE SYSTEMS ARCHITECTURE BLUEPRINT ({source_label.upper()}):\n"
                "Author an exhaustive, publication-grade comparative engineering review contrasting the provided architectures, specs, or protocols.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth architectural paragraphs directly below.\n"
                "1. Architectural Scope & SLA/SLO Comparison: Contrasting system goals, availability targets, and latency budgets.\n"
                "2. Topological Architecture & Component Decompositions: High-level comparison of service boundaries and interaction models.\n"
                "3. Data Flow, Storage & State Machine Matrix: Side-by-side comparison of storage engines, schemas, and message queues.\n"
                "4. API Contract & Schema Concordance Table: Endpoint, payload, authentication, and error code mappings.\n"
                "5. Fault Tolerance & Chaos Recovery Matrix: Comparing circuit breakers, failover topologies, and split-brain defenses.\n"
                "6. Performance, Latency & Capacity Budgets: P50/P99 latency benchmarks and throughput capacity.\n"
                "7. Security, Zero-Trust & Secrets Isolation Matrix: RBAC, mutual TLS, and cryptographic boundaries.\n"
                "8. Staged Engineering Roadmap & Technical Debt Ledger.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all architectural specifications strictly in the authentic reference text."
            )
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return (
                f"INSTRUCTION FOR COMPARATIVE CLINICAL TRIAL & THERAPEUTICS MONOGRAPH ({source_label.upper()}):\n"
                "Author an exhaustive, publication-grade comparative clinical monograph contrasting the provided clinical trials or biomedical regimens.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth medical analysis paragraphs directly below.\n"
                "1. Trial Protocols & Primary Endpoint Concordance: Side-by-side comparison of study designs, phases, and endpoints in display boxes (\\boxed{A \\text{ vs } B}).\n"
                "2. Patient Population & Stratification Comparison Matrix: Table comparing cohort sample sizes, age distributions, and inclusion/exclusion criteria.\n"
                "3. Efficacy & Statistical Comparison Table: Direct comparison of Hazard Ratios (HR), Overall Survival (OS), Progression-Free Survival (PFS), and p-values.\n"
                "4. Safety & Toxicity Profile Matrix: Comparing treatment-emergent adverse events (TEAEs), Grade 3/4 toxicities, and discontinuation rates.\n"
                "5. Pharmacokinetic & Pharmacodynamic Concordance: Bioavailability, half-life ($t_{1/2}$), and target receptor engagement.\n"
                "6. Standard-of-Care Concordance & Clinical Superiority Matrix.\n"
                "7. Methodological Limitations & Confounding Risk Comparison.\n"
                "8. Definitive Clinical Recommendation & Regulatory Summary.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all clinical figures, hazard ratios, and toxicity rates strictly in authentic source data."
            )
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return (
                f"INSTRUCTION FOR COMPARATIVE PEDAGOGICAL CURRICULUM & METHODOLOGY ANALYSIS ({source_label.upper()}):\n"
                "Author an exhaustive comparative educational treatise contrasting the provided curricula, tutorials, or methodologies.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth pedagogical paragraphs directly below.\n"
                "1. Learning Objectives & Conceptual Inversions Comparison: Display box comparison (\\boxed{\\text{Curriculum A} \\text{ vs } \\text{Curriculum B}}).\n"
                "2. Prerequisite & Pedagogical Scaffolding Matrix: Comparing sequencing, scaffolding steps, and concept dependencies.\n"
                "3. Mental Models & Intuitive Analogy Comparison Table: Evaluating explanatory power and intuitive clarity.\n"
                "4. Worked Example & Problem-Solving Methodology Comparison.\n"
                "5. Common Misconception Remediation Matrix.\n"
                "6. Active Recall & Assessment Rigor Comparison Table.\n"
                "7. Practical Implementation & Real-World Utility Matrix.\n"
                "8. Pedagogical Synthesis & Curriculum Recommendations."
            )
        else:
            return (
                f"INSTRUCTION FOR MULTI-SOURCE COMPARATIVE MONOGRAPH ({source_label.upper()}):\n"
                "Author an exhaustive, publication-grade comparative research monograph synthesizing and contrasting the provided reference sources.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth analytical paragraphs directly below.\n"
                "1. Source Boundary & Epistemic Declaration: Declare the exact scope and distinguish direct source claims from comparative reconstructions.\n"
                "2. Executive Comparative Synthesis & Boxed Ontological Inversions: Contrast foundational assumptions and paradigm shifts in display boxes (e.g. \\boxed{A \\to B}).\n"
                "3. Comparative Epistemic Status Matrix: Markdown table comparing Definitions, Theorems, Hypotheses, Conjectures, and Open Limits across all sources.\n"
                "4. Mathematical State Space & Formal Concordance: Derive and compare mathematical formalisms, operators, kernels, and metric spaces in standard LaTeX ($...$ and $$...$$).\n"
                "5. Domain-to-Domain Isomorphism Alignment Tables: Construct explicit Markdown tables mapping parameters, variables, and state mappings across both frameworks.\n"
                "6. Taxonomical Decomposition & Non-Implications: Construct category definition tables with explicit non-implication relations ($A \\not\\Rightarrow B$).\n"
                "7. Dialectical Friction & Trade-Off Matrix: Deep comparative audit of where the paradigms agree, clash, or exhibit epistemic blind spots.\n"
                "8. Concrete Engineering & Empirical Implementations: Compare computational platforms, architectures, and experimental platforms.\n"
                "9. Empirical Falsification & Critical Roadmaps: Explicit numbered failure conditions and validation pathways.\n"
                "10. Condensed Formal Mathematical Spine & Scholarly Assessment: Compile the consolidated mathematical pipeline and final bottom-line assessment.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all comparative statements strictly in the corresponding reference text provided above.\n"
                "2. DO NOT blend or attribute concepts across sources unless explicitly present in the text.\n"
                "3. Maintain rigorous publication-grade academic prose throughout."
            )

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return "finance"
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return "legal"
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return "engineering"
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return "clinical"
        elif document_genre == DocumentGenre.STRATEGIC_POLICY:
            return "policy"
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return "education"
        return "comparisons"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return f"Strategic Business Comparison — {source_label}"
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return f"Legal Regulatory Comparison — {source_label}"
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return f"Systems Architecture Comparison — {source_label}"
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return f"Comparative Clinical Review — {source_label}"
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return f"Comparative Curriculum Analysis — {source_label}"
        return f"Comparative Monograph — {source_label}"


class CriticalAnalysisStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        if conversational_bandwidth == ConversationalBandwidth.DIRECT_PRECISION_QA:
            return (
                f"INSTRUCTION FOR DIRECT PRECISION CRITIQUE ({source_label.upper()}):\n"
                "State the core critical vulnerability, flaw, or analytical limitation directly and concisely based strictly on authentic source evidence.\n"
                "Provide 1-2 sharp, evidence-grounded paragraphs with zero unsolicited scaffolding."
            )
        elif conversational_bandwidth == ConversationalBandwidth.EXECUTIVE_BRIEFING:
            return (
                f"INSTRUCTION FOR EXECUTIVE CRITICAL AUDIT BRIEFING ({source_label.upper()}):\n"
                "Provide a high-signal executive critical review strictly derived from the authentic source text.\n"
                "1. Core Vulnerability / Risk Statement (\\boxed{\\text{Critical Risk}}).\n"
                "2. Risk Severity & Stress-Testing Matrix: High-density Markdown table detailing vulnerabilities, impact levels, and mitigations.\n"
                "3. Strategic Remediation Ledger: Numbered actionable fixes."
            )

        return (
            f"INSTRUCTION FOR CRITICAL ANALYSIS, DIALECTICAL AUDIT & PEER REVIEW ({source_label.upper()}):\n"
            "Perform an adversarial, publication-grade critical audit and peer review of the source document(s) or framework(s) above.\n"
            "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth evaluative paragraphs directly below.\n"
            "1. Source Scope & Epistemic Boundary Declaration: Clarify the exact scope of the audit and establish evidentiary standards.\n"
            "2. Executive Abstract & Core Claims: Synthesize the primary thesis and construct boxed dependency chains (\\boxed{A \\to B}).\n"
            "3. Epistemic Status & Stress-Testing Matrix: Construct a markdown table categorizing Definitions, Assumptions, Assertions, and Vulnerabilities.\n"
            "4. Formal & Analytical Stress-Testing: Audit core models, metrics, or arguments for hidden vulnerabilities and unstated constraints.\n"
            "5. Logical Coherence & Gap Analysis: Expose tautologies, circular reasoning, unproven inferences, or unexamined dependencies.\n"
            "6. Taxonomical Precision & Category Errors: Build taxonomy tables isolating distinct concepts and formalize non-implications ($A \\not\\Rightarrow B$).\n"
            "7. Empirical & Boundary Condition Failures: Audit where the model breaks down under extreme parameters or real-world counter-examples.\n"
            "8. Dialectical Engagement with Alternative Paradigms: Rigorously analyze why competing approaches challenge this framework.\n"
            "9. Concrete Falsification Criteria & Constructive Reformulation: Detail explicit numbered failure conditions and actionable resolutions.\n"
            "10. Final Critical Synthesis & Peer Review Bottom-Line.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground all critiques in authentic textual statements and figures from the reference data.\n"
            "2. Use formal scientific, financial, or legal argumentation rather than superficial commentary."
        )

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return "finance"
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return "legal"
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return "engineering"
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return "clinical"
        elif document_genre == DocumentGenre.STRATEGIC_POLICY:
            return "policy"
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return "education"
        return "critiques"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return f"Critical Epistemic Audit — {source_label}"


class CreativeWritingStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        return (
            f"INSTRUCTION FOR IMMERSIVE CREATIVE WRITING & CONCEPTUAL WORLDBUILDING ({source_label.upper()}):\n"
            "Transform the core concepts, philosophies, and dynamics from the reference grounding context above into a captivating, publication-grade creative narrative, philosophical allegory, or speculative exploration.\n"
            "Guidelines for Narrative Craft:\n"
            "1. Engage evocative sensory detail, dynamic pacing, and genuine emotional/intellectual depth.\n"
            "2. Translate complex scientific, philosophical, or mathematical concepts into organic plot dynamics, metaphors, character dilemmas, or world rules.\n"
            "3. Maintain absolute conceptual fidelity to the underlying source ideas while demonstrating master-level narrative imagination.\n"
            "4. Avoid dry academic disclaimers or meta-commentary—deliver a pure, compelling narrative experience."
        )

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return "creative"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return f"Narrative Exploration — {source_label}"


class AcademicArticleStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        return ComprehensiveOverviewStrategy().build_directive(source_label, document_genre=document_genre, conversational_bandwidth=conversational_bandwidth)

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return "finance"
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return "legal"
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return "engineering"
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return "clinical"
        elif document_genre == DocumentGenre.STRATEGIC_POLICY:
            return "policy"
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return "education"
        return "articles"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return f"Academic Publication — {source_label}"


class NonConsensusContrarianStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        if conversational_bandwidth == ConversationalBandwidth.DIRECT_PRECISION_QA:
            return (
                f"INSTRUCTION FOR DIRECT CONTRARIAN THESIS ({source_label.upper()}):\n"
                "State the core non-consensus, contrarian insight directly and precisely based on authentic source text.\n"
                "Deliver 1-2 punchy, evidence-backed paragraphs with zero fluff."
            )

        return (
            f"INSTRUCTION FOR HETERODOX & NON-CONSENSUS CONTRARIAN THESIS ({source_label.upper()}):\n"
            "Develop a rigorous, publication-grade heterodox or contrarian essay challenging mainstream consensus based on the breakthrough ideas in the reference text.\n"
            "Structure:\n"
            "1. The Consensus Orthodoxy: Clearly define the widespread consensus assumption.\n"
            "2. The Flaw in Consensus: Systematically expose why conventional wisdom fails using source evidence.\n"
            "3. The Radical Counter-Model: Present the alternative model in display boxes (\\boxed{A \\to B}).\n"
            "4. Asymmetric Opportunities & Unexplored Frontiers: Analyze non-obvious implications.\n"
            "5. The Litmus Test: Concrete conditions that will prove or disprove this contrarian thesis.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground every contrarian argument strictly in authentic source evidence."
        )

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return "contrarian"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return f"Non-Consensus Synthesis — {source_label}"


class ViralPublicNarrativeStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        return (
            f"INSTRUCTION FOR HIGH-IMPACT VIRAL ESSAY & THOUGHT LEADERSHIP PUBLICATION ({source_label.upper()}):\n"
            "Craft an exceptionally engaging, high-signal public publication (Substack essay, X thread, or LinkedIn thought leadership article) distilling the core breakthrough of the source text.\n"
            "Rhetorical Architecture:\n"
            "1. Irresistible Hook: Open with a provocative paradox, counter-intuitive insight, or paradigm shift that grabs immediate attention.\n"
            "2. High-Signal Concept Distillation: Translate dense jargon and formal models into intuitive, unforgettable visual analogies without losing technical accuracy.\n"
            "3. Pacing & Whitespace: Use modular bullet points, bold callouts, and clean formatting for effortless readability.\n"
            "4. The 'So What?' (Real-world stakes): Explain why this matters for the future of the industry, technology, or humanity.\n"
            "5. Actionable Conclusion & Discussion Spark: Conclude with a thought-provoking inquiry that triggers viral discourse.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. All factual assertions and core mechanisms must be 100% faithful to the authentic source reference.\n"
            "2. Maximize clarity and punch without sacrificing integrity."
        )

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return "narratives"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return f"Executive Thought Leadership — {source_label}"


class FormulaExtractionStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        if conversational_bandwidth == ConversationalBandwidth.DIRECT_PRECISION_QA:
            return (
                f"INSTRUCTION FOR DIRECT FORMULA EXTRACTION ({source_label.upper()}):\n"
                "Extract and formulate the exact mathematical equation, transition kernel, or operator requested directly in standard display LaTeX ($...$ and $$...$$).\n"
                "Follow immediately with a concise definition table of all variables and parameters. Zero conversational fluff."
            )

        return (
            f"INSTRUCTION FOR COMPREHENSIVE MATHEMATICAL FORMALISM & DERIVATION MONOGRAPH ({source_label.upper()}):\n"
            "Extract, formulate, derive, and rigorously explain all formal mathematical objects, state spaces, measurable spaces, "
            "Markov transition kernels, dynamical equations, asymptotic properties, and theorems from the authentic source text above.\n"
            "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth mathematical derivations directly below.\n"
            "1. Source Evidentiary Boundary: Declare all extracted mathematical objects and distinguish literal definitions from analytical reconstructions.\n"
            "2. Epistemic Status Matrix: Markdown table categorizing Definitions, Axioms, Hypotheses, Constructive Theorems, Conjectures, and Open Limits.\n"
            "3. Complete Mathematical Architecture & LaTeX Derivations: Formulate all state spaces $\\mathcal{S}$, measurable tuples $((X, \\mathcal{X}), (G, \\mathcal{G}))$, transition operators $\\mathcal{L}$, convolution integrals, and optimization functionals in explicit LaTeX ($...$ and $$...$$).\n"
            "4. Domain-to-Domain Isomorphism Mapping Tables: Explicit table mapping dynamical system parameters to physical observables (e.g. Markov states $\\leftrightarrow$ Quantum basis $|x\\rangle$, period $\\leftrightarrow$ wavelength $\\lambda$).\n"
            "5. Taxonomical Variable & Space Dictionary: Comprehensive table defining every variable, domain, codomain, dimension, and physical/information unit.\n"
            "6. Asymptotic Dynamics, Convergence & Proof Structures: Rigorous step-by-step mathematical derivation of long-term limits ($n \\to \\infty$).\n"
            "7. Condensed Formal Mathematical Spine: Compiling the entire mathematical pipeline into an authoritative, consolidated display LaTeX equation block at the conclusion.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Derive every formula and definition strictly from the authentic reference data provided above.\n"
            "2. DO NOT omit equations or replace math with qualitative commentary—deliver full, explicit LaTeX derivations throughout."
        )

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return "mathematics"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        return f"Mathematical Formalisms — {source_label}"


class ComprehensiveOverviewStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        if conversational_bandwidth == ConversationalBandwidth.DIRECT_PRECISION_QA:
            return (
                f"INSTRUCTION FOR DIRECT PRECISION Q&A ({source_label.upper()}):\n"
                "Answer the user's specific factual or mathematical query directly, razor-sharp, and factually based exclusively on the provided text.\n"
                "State the exact value, formula, mathematical operator, ratio, or clause citation immediately in clear formatting.\n"
                "Follow with 1 concise explanatory paragraph strictly derived from authentic source evidence.\n"
                "DO NOT generate unprompted outline headers, long multi-layer document scaffolds, or conversational pleasantries."
            )
        elif conversational_bandwidth == ConversationalBandwidth.EXECUTIVE_BRIEFING:
            return (
                f"INSTRUCTION FOR HIGH-DENSITY EXECUTIVE BRIEFING ({source_label.upper()}):\n"
                "Provide a high-signal executive briefing strictly derived from the authentic source text.\n"
                "1. Executive Causal Thesis & Core Impact: Formulate the primary strategic takeaway in a boxed flow (\\boxed{A \\to B}).\n"
                "2. Key Metrics, Trade-offs & Critical Risks Matrix: High-density Markdown table summarizing core performance figures, liabilities, and trade-offs.\n"
                "3. Strategic Decision Ledger & Actionable Next Steps: Numbered bottom-line recommendations.\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground every metric and strategic assertion strictly in authentic reference data.\n"
                "2. Deliver maximum signal density with zero fluff."
            )
        elif conversational_bandwidth == ConversationalBandwidth.NATURAL_CONVERSATION:
            return (
                f"INSTRUCTION FOR NATURAL CONVERSATIONAL DISCOURSE & CO-CREATION ({source_label.upper()}):\n"
                "Engage in a natural, intellectually rich, and fluid dialogue strictly grounded in authentic knowledge.\n"
                "Maintain an empathetic, peer-level conversational tone. Structure response with clear, readable prose paragraphs.\n"
                "DO NOT force unprompted markdown table stubs, multi-layer headers, or rigid document templates unless explicitly requested.\n"
                "Actively support iterative turn-taking and user steering for collaborative tasks."
            )
        elif conversational_bandwidth == ConversationalBandwidth.TECHNICAL_DOSSIER:
            return (
                f"INSTRUCTION FOR MODULAR TECHNICAL DOSSIER & SPECIFICATION ({source_label.upper()}):\n"
                "Provide a focused, publication-grade technical specification based STRICTLY AND EXCLUSIVELY on authentic source text.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth analytical paragraphs directly below.\n"
                "1. System Objective & Functional Scope: Core operational target and SLA/SLO bounds (\\boxed{A \\to B}).\n"
                "2. Data Flows, State Machines & Entity Transition Matrix: Markdown table detailing schemas, transition kernels, and pipelines.\n"
                "3. API Contract & Interface Specification Matrix: Structured table detailing endpoints, schemas, methods, and error codes.\n"
                "4. Fault Tolerance, Edge Cases & Chaos Defense Table: Error handling, recovery mechanisms, and circuit breakers.\n"
                "5. Concrete Implementation Milestones & Verification Ledger: Phased technical deliverables.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all specifications and formulas strictly in authentic reference text."
            )

        # Tier 1: EXHAUSTIVE_MONOGRAPH
        if document_genre == DocumentGenre.GENERAL_DOCUMENT:
            from .intent_decomposer import detect_document_genre
            inferred = detect_document_genre(source_label, raw_prompt=source_label)
            if inferred != DocumentGenre.GENERAL_DOCUMENT:
                document_genre = inferred

        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return (
                f"INSTRUCTION FOR EXHAUSTIVE STRATEGIC & FINANCIAL MONOGRAPH ({source_label.upper()}):\n"
                "Provide an exhaustive, publication-grade strategic and financial dossier based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
                "DO NOT write a superficial 5-paragraph summary. Enforce the 8-Layer Strategic & Financial Analysis Architecture across granular, progressive chapters.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth analytical paragraphs directly below.\n"
                "1. Executive Thesis, Strategic Positioning & Core Value Proposition: Formulate the core market opportunity, disruption vector, and construct boxed causal flywheels (\\boxed{A \\to B}).\n"
                "2. Market Opportunity (TAM/SAM/SOM) & Customer Segmentation Matrix: Construct a comprehensive markdown table sizing the market, detailing ICP profiles, and segmenting demand vectors.\n"
                "3. Unit Economics, Margin Structure & Financial Performance Table: Build a structured matrix detailing ARR/MRR, CAC, LTV, Gross Margins, Operating Margins, Payback Periods, Net Retention, and Burn Multiples.\n"
                "4. Competitive Moats, Network Effects & Defensibility Flywheel: Construct a matrix evaluating switching costs, proprietary data advantages, brand equity, and economies of scale.\n"
                "5. Capital Allocation, Runway & Scenario Sensitivity Analysis Table: Detailed scenario modeling matrix (Bear, Base, Bull cases) evaluating cash runway, hiring plan, and churn sensitivity.\n"
                "6. Competitor Landscape & Feature/Pricing Differentiation Matrix: Direct side-by-side comparison table against key incumbents and emerging alternatives.\n"
                "7. Critical Unmitigated Risks, Concentration Hazards & Macro Mitigation Table: Comprehensive risk audit covering regulatory, customer concentration, key-person, and market headwinds.\n"
                "8. Strategic Execution Roadmap & Quantitative Milestone Ledger: Phased quarter-by-quarter execution plan with explicit quantitative KPIs and deliverables.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all financial figures, market sizes, and strategic claims strictly in the authentic reference data provided above.\n"
                "2. DO NOT fabricate financial data or invent customer metrics not substantiated by the source text."
            )
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return (
                f"INSTRUCTION FOR EXHAUSTIVE LEGAL & REGULATORY COMPLIANCE AUDIT ({source_label.upper()}):\n"
                "Provide an exhaustive, publication-grade legal review and compliance dossier based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
                "DO NOT write a superficial summary. Enforce the 8-Layer Legal & Regulatory Architecture across granular, progressive chapters.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth legal analysis paragraphs directly below.\n"
                "1. Purpose, Scope & Parties Declaration: Explicitly declare the legal parties, effective dates, recitals, and jurisdictional framework.\n"
                "2. Core Rights, Obligations & Covenants Matrix: Construct a comprehensive Markdown table categorizing affirmative, negative, operational, and financial covenants.\n"
                "3. Liability, Indemnification & Risk Allocation Table: Construct a structured table detailing indemnification triggers, liability caps (super-caps vs standard caps), consequential damages waivers, and carve-outs.\n"
                "4. Termination, Default & Breach Triggers Table: Construct a matrix detailing cure periods, termination for convenience vs cause, material breach definitions, and post-termination transition obligations.\n"
                "5. Ambiguity & Legal Exposure Audit: Systematically isolate undefined terms, conflicting schedules, unilateral provisions, and cross-indemnity liabilities.\n"
                "6. Precedent, Statutory & Regulatory Alignment Matrix: Evaluate alignment against relevant statutory bodies (e.g. GDPR, HIPAA, UCC, Delaware General Corporation Law, SEC regulations).\n"
                "7. Dispute Resolution, Forum Selection & Governing Law Analysis: Detail choice of law, mandatory arbitration clauses, venue selection, and fee-shifting terms.\n"
                "8. Actionable Redline Recommendations & Risk Remediation Ledger: Provide concrete, numbered redline suggestions to balance risk exposure and protect sovereign rights.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground every legal interpretation and clause citation strictly in the authentic source text provided above.\n"
                "2. Maintain formal legal and regulatory analytical rigor throughout."
            )
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return (
                f"INSTRUCTION FOR EXHAUSTIVE SYSTEMS ARCHITECTURE BLUEPRINT ({source_label.upper()}):\n"
                "Provide an exhaustive, publication-grade engineering specification and architecture blueprint based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
                "DO NOT write a superficial summary. Enforce the 8-Layer Systems Architecture Blueprint across granular, progressive chapters.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth engineering paragraphs directly below.\n"
                "1. System Objective, Architectural Scope & SLA / SLO Contracts: State the core engineering objectives, availability contracts (99.99%), and latency bounds in display boxes (\\boxed{A \\to B}).\n"
                "2. Topological Architecture Diagram & Component Boundaries: High-level component decomposition detailing service boundaries, dependencies, and communication protocols.\n"
                "3. Data Flows, Storage & State Machine Transition Matrix: Construct a structured Markdown table detailing ingestion pipelines, database schemas, message queues, and state transitions.\n"
                "4. API Contract & Schema Definition Matrix: Construct a comprehensive table detailing endpoints, HTTP/gRPC methods, request/response schemas, authentication, and error code specifications.\n"
                "5. Fault Tolerance, Chaos Scenarios & Split-Brain Recovery Table: Construct a matrix evaluating circuit breakers, rate limiters, failover mechanisms, backoff algorithms, and disaster recovery.\n"
                "6. Performance, Latency & Capacity Budgets Table: Detail P50/P99 latency constraints, throughput capacity (RPS), caching strategies, and scale bottlenecks.\n"
                "7. Security, Zero-Trust Isolation & Secrets Management Matrix: Detail RBAC policies, mutual TLS encryption, token lifecycles, and audit logging.\n"
                "8. Staged Engineering Roadmap & Technical Debt Ledger: Phased implementation milestones and architectural debt tracking.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all architectural specifications, schemas, and performance constraints strictly in the authentic reference data provided above."
            )
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return (
                f"INSTRUCTION FOR EXHAUSTIVE BIOMEDICAL & CLINICAL MONOGRAPH ({source_label.upper()}):\n"
                "Provide an exhaustive, publication-grade clinical trial and biomedical synthesis based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
                "DO NOT write a superficial summary. Enforce the 8-Layer Biomedical & Clinical Architecture across granular, progressive chapters.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth analytical paragraphs directly below.\n"
                "1. Trial Protocol, Primary Endpoints & Evidentiary Scope: Core clinical hypothesis, phase design, and therapeutic intervention in display boxes (\\boxed{\\text{Intervention} \\to \\text{Target Pathway}}).\n"
                "2. Patient Cohort, Baseline Demographics & Stratification Matrix: Construct a comprehensive markdown table detailing sample size, age, biomarkers, and inclusion/exclusion criteria.\n"
                "3. Efficacy & Statistical Outcomes Matrix: Structured table detailing Hazard Ratios (HR), Overall Survival (OS), Progression-Free Survival (PFS), p-values, and 95% Confidence Intervals.\n"
                "4. Safety Profile, Adverse Events (AEs/SAEs) & Toxicity Matrix: Comprehensive table detailing treatment-emergent adverse events, Grade 3/4 toxicities, and dose-limiting toxicities.\n"
                "5. Pharmacokinetics, Pharmacodynamics & Molecular Mechanism Deep-Dive: Biochemical mechanism of action, receptor binding affinity, bioavailability, and clearance kinetics.\n"
                "6. Standard-of-Care Concordance & Comparative Therapeutics Matrix: Direct comparison table against established standards of care and active comparators.\n"
                "7. Trial Limitations, Confounding Biases & Subgroup Vulnerabilities Table: Critical audit of statistical power, attrition bias, and demographic generalizability.\n"
                "8. Translational Roadmap, Regulatory Milestones & Clinical Bottom Line: Regulatory approval pathways (FDA/EMA), post-market commitments, and definitive clinical verdict.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all clinical figures, hazard ratios, and endpoints strictly in authentic reference data.\n"
                "2. DO NOT fabricate statistical results or patient counts not substantiated by the source text."
            )
        elif document_genre == DocumentGenre.STRATEGIC_POLICY:
            return (
                f"INSTRUCTION FOR EXHAUSTIVE PUBLIC POLICY & INSTITUTIONAL GOVERNANCE REVIEW ({source_label.upper()}):\n"
                "Provide an exhaustive, publication-grade policy review and governance dossier based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
                "DO NOT write a superficial summary. Enforce the 8-Layer Policy & Governance Architecture across granular, progressive chapters.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth policy analysis paragraphs directly below.\n"
                "1. Policy Problem Statement & Executive Summary: Formulate the core public interest challenge and construct boxed societal causal chains (\\boxed{\\text{Policy Intervention} \\to \\text{Systemic Impact}}).\n"
                "2. Stakeholder Impact & Distributional Cost-Benefit Matrix: Construct a comprehensive table analyzing costs, benefits, and distributional effects across affected citizen/industry stakeholder groups.\n"
                "3. Policy Mechanisms, Statutes & Regulatory Instruments Table: Construct a structured matrix detailing specific statutes, tax incentives, standards, and enforcement mechanisms deployed.\n"
                "4. Incentive Alignment & Unintended Consequences Audit: Systematically identify perverse incentives, regulatory capture risks, and second-order systemic spillovers.\n"
                "5. Policy Trade-Off & Alternative Approaches Comparison Table: Rigorously compare the proposed policy against alternative regulatory or market-based mechanisms.\n"
                "6. Institutional Governance, Oversight & Fiduciary Principles: Detail principles of oversight, transparency, independent auditing, and democratic accountability (5 Governance Standards).\n"
                "7. Implementation Roadmap & Staged Inter-Agency Milestones: Phased regulatory rollout, pilot programs, and inter-agency coordination schedule.\n"
                "8. Monitoring, Key Performance Indicators (KPIs) & Sunsetting Triggers Table: Concrete quantitative metrics to trigger periodic reviews or sunset clauses.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all policy analyses and stakeholder impacts strictly in the authentic reference data provided above."
            )
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return (
                f"INSTRUCTION FOR EXHAUSTIVE PEDAGOGICAL CURRICULUM & STUDY GUIDE ({source_label.upper()}):\n"
                "Provide an exhaustive, publication-grade pedagogical curriculum and educational masterclass based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
                "DO NOT write a superficial summary. Enforce the 8-Layer Pedagogical Architecture across granular, progressive chapters.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth educational paragraphs directly below.\n"
                "1. Learning Objectives, Core Intuition & Concept Map: Foundational mental model and learning outcomes in display boxes (\\boxed{\\text{Foundational Concept} \\to \\text{Advanced Mastery}}).\n"
                "2. Prerequisites & Knowledge Dependency Matrix: Structured markdown table mapping required skills, concepts, and proficiency levels.\n"
                "3. Visual Analogies, Mental Models & Intuitive Scaffolding: Translating complex formal abstractions into unforgettable visual analogies.\n"
                "4. Step-by-Step Worked Derivations & Problem Walkthroughs Table: Granular step-by-step problem-solving sequence with explicit intermediate states.\n"
                "5. Common Misconceptions, Pitfalls & Diagnostic Matrix: Comprehensive table pairing frequent cognitive errors with underlying root causes and corrective insights.\n"
                "6. Active Recall Exercises, Scaffolding Questions & Practice Problems: Tiered problem sets (Foundational, Intermediate, Advanced) with solution hints.\n"
                "7. Real-World Applications & Cross-Disciplinary Case Studies Table: Concrete real-world implementations demonstrating practical utility.\n"
                "8. Mastery Assessment Rubric & Self-Evaluation Ledger: Explicit quantitative grading rubric and advanced study horizons.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all concepts, definitions, and worked examples strictly in authentic reference data."
            )
        elif document_genre == DocumentGenre.NARRATIVE_LITERARY:
            return (
                f"INSTRUCTION FOR EXHAUSTIVE LITERARY & DIALECTICAL TREATISE ({source_label.upper()}):\n"
                "Provide an exhaustive, publication-grade literary and philosophical analysis based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
                "DO NOT write a superficial summary. Enforce the 8-Layer Literary & Dialectical Architecture across granular, progressive chapters.\n"
                "Enforce the Universal Hybrid Standard: Pair every high-density Markdown Table with 2-3 in-depth literary/philosophical paragraphs directly below.\n"
                "1. Core Premise, Thematic Motif & Conceptual Inversion: Foundational philosophical or narrative premise and central metaphor in display boxes (\\boxed{A \\to B}).\n"
                "2. Thematic Decomposition Matrix: Construct a comprehensive markdown table detailing major themes, motifs, symbols, and their narrative evolutions.\n"
                "3. Rhetorical & Dialectical Architecture: Deep analysis of argumentative logic, narrative voice, pacing, and emotional tension arcs.\n"
                "4. Subject Dynamics, Character Arcs & Agency Flows Table: Structured matrix tracing protagonist/subject evolution and interpersonal power dynamics.\n"
                "5. Case Studies, Historical Analogies & Textual Evidence Index: Deep exposition of central narrative episodes and evidentiary examples.\n"
                "6. Stylistic & Structural Analysis: Language mechanics, tone, imagery, and structural innovations.\n"
                "7. Philosophical & Cultural Significance Table: Historical contextualization and broader intellectual implications.\n"
                "8. Comprehensive Synthesis & Critical Assessment: Final holistic evaluation of the work's enduring impact.\n\n"
                "STRICT FACTUAL GROUNDING LAWS:\n"
                "1. Ground all thematic interpretations and narrative citations strictly in the authentic source text provided above."
            )
        else:
            # Default for Research Monograph (SCIENTIFIC_MATHEMATICAL and GENERAL_DOCUMENT)
            return (
                f"INSTRUCTION FOR EXHAUSTIVE PUBLICATION-GRADE RESEARCH MONOGRAPH ({source_label.upper()}):\n"
                "Author an exhaustive, publication-grade academic synthesis and research monograph based STRICTLY AND EXCLUSIVELY on the authentic source document provided above.\n"
                "DO NOT write a superficial summary. Enforce the 10-Layer Publication Monograph Architecture across granular, logically progressive chapters.\n"
                "UNIVERSAL HYBRID STANDARD & DEPTH REQUIREMENT:\n"
                "- For EVERY chapter (1 through 10), deliver minimum 3 to 4 dense, publication-grade analytical paragraphs providing exhaustive exposition, quoting verbatim source claims, and unpacking mechanisms.\n"
                "- Pair every high-density Markdown Table with 2-3 in-depth analytical paragraphs directly below.\n\n"
                "CHAPTER CORRIDORS & MULTIMODAL CONTEXTUAL FIGURE WEAVING:\n"
                "1. Source Boundary & Epistemic Declaration: Explicitly declare the primary evidentiary basis, author citations, publication context, and distinguish direct empirical source claims from analytical reconstructions.\n"
                "2. Abstract & Core Ontological Inversion: Formulate the foundational thesis, explanatory target, and construct boxed conceptual causal chains (\\boxed{A \\to B}) and vertical dependency diagrams. Contextually embed the foundational system architecture or schematic diagrams from the document using raw Markdown image tags and detailed walkthroughs.\n"
                "3. Epistemic Status Classification Matrix: Construct a comprehensive markdown table categorizing every major proposition as a Definition, Axiom, Hypothesis, Constructive Theorem, Conjecture, or Unresolved Open Limit, accompanied by extensive epistemic justifications.\n"
                "4. Formal Mathematical State Space Modeling & Exact Derivations: Quote and derive the exact mathematical operators, state spaces, governing equations, transition kernels, matrices, loss functions, optimization bounds, or algorithmic procedures STRICTLY AND EXCLUSIVELY as presented in the authentic source text in contiguous display LaTeX ($$...$$). Contextually embed relevant formal diagrams and derive step-by-step mathematical integrations.\n"
                "5. Domain-to-Domain Isomorphism Alignment Tables: Construct explicit tables mapping parameters, variables, state spaces, and theoretical constructs across domains as established by the author.\n"
                "6. Taxonomical Decompositions & Logical Non-Implications: Construct category definition tables with explicit non-implication relations ($A \\not\\Rightarrow B$) derived from the document's core principles.\n"
                "7. Dialectical Paradigm Audits: Systematically evaluate allied and competing theories with exhaustive critical paragraphs detailing exact points of convergence and divergence.\n"
                "8. Concrete Experimental Platforms, Computational Architectures & Interaction Graphs: Formulate computational mechanisms, simulation architectures, network topologies, and benchmark platforms. Contextually embed technical architecture and dataflow diagrams from the document with comprehensive structural walkthroughs.\n"
                "9. Empirical Falsification Criteria & Explicit Catalog of Unresolved Open Limits: Formulate numbered empirical falsification conditions, a staged research roadmap, and an exhaustive catalog of core theoretical bottlenecks.\n"
                "10. Ethical Asymmetry, Governance & Condensed Mathematical Spine: Detail ethical implications, institutional governance safeguards (\\boxed{\\text{architect} \\neq \\text{sovereign}}), and compile the complete consolidated LaTeX equation block at the conclusion.\n\n"
                "STRICT CLOSED-WORLD EVIDENTIARY QUARANTINE & RENDERING LAWS:\n"
                "1. CLOSED-WORLD ISOLATION: Ground 100% of mathematical equations, state spaces, definitions, and theorems EXCLUSIVELY in the provided reference text. You are STRICTLY FORBIDDEN from importing, borrowing, or synthesizing mathematical equations or formalisms from external frameworks or other papers unless they appear verbatim in the provided reference text.\n"
                "2. RAW UNESCAPED FIGURE IMAGE TAGS: When technical figures are attached, embed their raw unescaped Markdown image tags: ![Figure Caption](/api/v1/artifacts/extracted_figures/...). DO NOT wrap image tags in backticks, quotes, or code fences. Follow every figure immediately with an italicized structural caption and a clickable link: [🔍 View High-Resolution Diagram](/api/v1/artifacts/extracted_figures/...).\n"
                "3. STRICT KATEX CONTINUITY LAW: All display math blocks ($$...$$ or \\begin{aligned}...\\end{aligned}) must be contiguous with ZERO empty blank lines inside the delimiters to ensure valid KaTeX rendering.\n"
                "4. Ground all assertions strictly in the authentic reference data provided above with zero speculative hallucinations."
            )

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return "finance"
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return "legal"
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return "engineering"
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return "clinical"
        elif document_genre == DocumentGenre.STRATEGIC_POLICY:
            return "policy"
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return "education"
        return "research"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return f"Strategic Business Monograph — {source_label}"
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return f"Legal Compliance Audit — {source_label}"
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return f"Systems Architecture Blueprint — {source_label}"
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return f"Clinical Monograph & Evidence Review — {source_label}"
        elif document_genre == DocumentGenre.STRATEGIC_POLICY:
            return f"Policy & Governance Review — {source_label}"
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return f"Pedagogical Curriculum & Study Guide — {source_label}"
        elif document_genre == DocumentGenre.NARRATIVE_LITERARY:
            return f"Literary Treatise — {source_label}"
        return f"Comprehensive Treatise — {source_label}"


class ConceptualQAStrategy(BaseDirectiveStrategy):
    def build_directive(
        self,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        if conversational_bandwidth == ConversationalBandwidth.DIRECT_PRECISION_QA:
            return (
                f"INSTRUCTION: Answer the User Directive directly, factually, and concisely based exclusively on the provided text for {source_label}.\n"
                "State the exact value, equation, or fact immediately, followed by 1 concise explanatory paragraph.\n"
                "Ground all factual claims strictly in the authentic reference data provided above. Zero fluff."
            )
        elif conversational_bandwidth == ConversationalBandwidth.NATURAL_CONVERSATION:
            return (
                f"INSTRUCTION FOR NATURAL CONVERSATIONAL DIALOGUE ({source_label.upper()}):\n"
                "Engage in a fluid, empathetic, and intellectually rigorous conversation grounded in authentic knowledge.\n"
                "Structure response with natural prose paragraphs. DO NOT force unprompted markdown table stubs or rigid document templates."
            )
        return (
            f"INSTRUCTION: Answer the User Directive directly, comprehensively, and factually based exclusively on the provided text for {source_label}.\n"
            "Ground all factual claims strictly in the authentic reference data provided above."
        )

    def get_artifact_category(self, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return "finance"
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return "legal"
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return "engineering"
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return "clinical"
        elif document_genre == DocumentGenre.STRATEGIC_POLICY:
            return "policy"
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return "education"
        return "research"

    def get_default_artifact_title(self, source_label: str, document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT) -> str:
        if document_genre == DocumentGenre.BUSINESS_FINANCIAL:
            return f"Financial Analysis — {source_label}"
        elif document_genre == DocumentGenre.LEGAL_REGULATORY:
            return f"Legal Analysis — {source_label}"
        elif document_genre == DocumentGenre.ENGINEERING_SYSTEMS:
            return f"Technical Specification — {source_label}"
        elif document_genre == DocumentGenre.BIOMEDICAL_CLINICAL:
            return f"Clinical Analysis — {source_label}"
        elif document_genre == DocumentGenre.STRATEGIC_POLICY:
            return f"Policy Analysis — {source_label}"
        elif document_genre == DocumentGenre.EDUCATIONAL_PEDAGOGICAL:
            return f"Study Notes — {source_label}"
        return f"Technical Response — {source_label}"


class CognitiveDirectiveRegistry:
    """Central registry mapping DirectiveModality to its dedicated directive strategy."""

    def __init__(self):
        self._strategies: Dict[DirectiveModality, BaseDirectiveStrategy] = {
            DirectiveModality.MULTI_DOCUMENT_COMPARISON: MultiDocumentComparisonStrategy(),
            DirectiveModality.CRITICAL_ANALYSIS: CriticalAnalysisStrategy(),
            DirectiveModality.CREATIVE_WRITING: CreativeWritingStrategy(),
            DirectiveModality.ACADEMIC_ARTICLE: AcademicArticleStrategy(),
            DirectiveModality.NON_CONSENSUS_CONTRARIAN: NonConsensusContrarianStrategy(),
            DirectiveModality.VIRAL_PUBLIC_NARRATIVE: ViralPublicNarrativeStrategy(),
            DirectiveModality.FORMULA_EXTRACTION: FormulaExtractionStrategy(),
            DirectiveModality.COMPREHENSIVE_OVERVIEW: ComprehensiveOverviewStrategy(),
            DirectiveModality.CONCEPTUAL_QA: ConceptualQAStrategy(),
        }

    def get_strategy(self, modality: DirectiveModality) -> BaseDirectiveStrategy:
        return self._strategies.get(modality, self._strategies[DirectiveModality.CONCEPTUAL_QA])

    def synthesize_directive(
        self,
        modality: DirectiveModality,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
        conversational_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    ) -> str:
        strategy = self.get_strategy(modality)
        return strategy.build_directive(
            source_label,
            document_genre=document_genre,
            conversational_bandwidth=conversational_bandwidth
        )

    def get_artifact_metadata(
        self,
        modality: DirectiveModality,
        source_label: str,
        document_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT
    ) -> Tuple[str, str]:
        strategy = self.get_strategy(modality)
        return (
            strategy.get_artifact_category(document_genre=document_genre),
            strategy.get_default_artifact_title(source_label, document_genre=document_genre)
        )
