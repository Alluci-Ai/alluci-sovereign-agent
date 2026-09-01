"""
Cognitive Directive Registry & Adaptive Prompt Synthesis Engine
================================================================
Implements dynamic, intent-adaptive prompt directive synthesizers and artifact metadata strategies
across all 9 Cognitive Directive Modalities (G).
Zero hardcoding, parameterized source provenance, and strict grounding laws.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
from .intent_decomposer import DirectiveModality


class BaseDirectiveStrategy(ABC):
    """Abstract Strategy for synthesizing dynamic cognitive directives."""

    @abstractmethod
    def build_directive(self, source_label: str) -> str:
        """Constructs the authoritative prompt directive instruction."""
        pass

    @abstractmethod
    def get_artifact_category(self) -> str:
        """Returns the artifact directory category (e.g. comparisons, critiques, articles, narratives)."""
        pass

    @abstractmethod
    def get_default_artifact_title(self, source_label: str) -> str:
        """Returns a publication-grade fallback title for generated artifact triads."""
        pass


class MultiDocumentComparisonStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR MULTI-SOURCE COMPARATIVE MONOGRAPH ({source_label.upper()}):\n"
            "Author an exhaustive, publication-grade comparative research monograph synthesizing and contrasting the provided reference sources.\n"
            "Structure your analysis across the following multi-chapter academic architecture:\n"
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

    def get_artifact_category(self) -> str:
        return "comparisons"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Comparative Monograph — {source_label}"


class CriticalAnalysisStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR CRITICAL ANALYSIS, DIALECTICAL AUDIT & PEER REVIEW ({source_label.upper()}):\n"
            "Perform an adversarial, publication-grade critical audit and peer review of the source document(s) or framework(s) above.\n"
            "Structure your evaluation across the following multi-chapter scholarly architecture:\n"
            "1. Source Scope & Epistemic Boundary Declaration: Clarify the exact scope of the audit and establish evidentiary standards.\n"
            "2. Executive Abstract & Core Theoretical Claims: Synthesize the primary thesis and construct boxed dependency chains (\\boxed{A \\to B}).\n"
            "3. Epistemic Status Matrix: Construct a markdown table categorizing Definitions, Theorems, Hypotheses, Conjectures, and Unresolved Limits.\n"
            "4. Formal Axiomatic & Mathematical Stress-Testing: Reconstruct core lemmas, state spaces, transition kernels, and optimization bounds in LaTeX ($...$ and $$...$$) and audit for hidden mathematical vulnerabilities.\n"
            "5. Logical Coherence & Epistemic Gap Analysis: Expose tautologies, circular definitions, unproven inferences, or unstated assumptions.\n"
            "6. Taxonomical Precision & Category Errors: Build taxonomy tables isolating distinct concepts and formalize non-implications ($A \\not\\Rightarrow B$).\n"
            "7. Empirical & Theoretical Boundary Condition Failures: Audit where the model breaks down under extreme parameters or counter-examples.\n"
            "8. Dialectical Engagement with Alternative Paradigms: Rigorously analyze why alternative or competing frameworks challenge this model.\n"
            "9. Concrete Falsification Criteria & Constructive Reformulation: Detail explicit numbered falsifiers and proposed mathematical resolutions.\n"
            "10. Condensed Formal Mathematical Spine & Final Peer Review Synthesis.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground all critiques in authentic textual statements and equations from the reference data.\n"
            "2. Use formal scientific and mathematical argumentation rather than superficial commentary."
        )

    def get_artifact_category(self) -> str:
        return "critiques"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Critical Epistemic Audit — {source_label}"


class CreativeWritingStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR IMMERSIVE CREATIVE WRITING & CONCEPTUAL WORLDBUILDING ({source_label.upper()}):\n"
            "Transform the core concepts, philosophies, and dynamics from the reference grounding context above into a captivating, publication-grade creative narrative, philosophical allegory, or speculative exploration.\n"
            "Guidelines for Narrative Craft:\n"
            "1. Engage evocative sensory detail, dynamic pacing, and genuine emotional/intellectual depth.\n"
            "2. Translate complex scientific, philosophical, or mathematical concepts into organic plot dynamics, metaphors, character dilemmas, or world rules.\n"
            "3. Maintain absolute conceptual fidelity to the underlying source ideas while demonstrating master-level narrative imagination.\n"
            "4. Avoid dry academic disclaimers or meta-commentary—deliver a pure, compelling narrative experience."
        )

    def get_artifact_category(self) -> str:
        return "creative"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Narrative Exploration — {source_label}"


class AcademicArticleStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR SCHOLARLY JOURNAL ARTICLE & ACADEMIC MONOGRAPH ({source_label.upper()}):\n"
            "Author an exhaustive, publication-grade scholarly research paper and monograph strictly based on the provided reference grounding context.\n"
            "Enforce the 10-Layer Publication Monograph Architecture:\n"
            "1. Source Boundary & Epistemic Declaration: Explicitly declare the primary evidentiary basis and distinguish author statements from analytical reconstructions.\n"
            "2. Abstract & Core Ontological Inversion: Provide a self-contained scholarly abstract and construct boxed conceptual causal chains (\\boxed{A \\to B}).\n"
            "3. Epistemic Status Classification Matrix: Construct a markdown table separating Definitions, Axioms, Hypotheses, Constructive Theorems, Conjectures, and Open Limits.\n"
            "4. Mathematical State Space Modeling & Formal Derivations: Formulate all state spaces $\\mathcal{S}$, transition kernels $\\mathcal{L}$, operators $\\mathcal{P}$, constraint functionals $\\mathcal{C}$, and optimization bounds in standard LaTeX display math ($...$ and $$...$$).\n"
            "5. Domain-to-Domain Isomorphism Alignment Tables: Construct explicit tables mapping parameters and variables across domains.\n"
            "6. Taxonomical Decompositions & Non-Implications: Construct category definition tables with explicit non-implications ($A \\not\\Rightarrow B$).\n"
            "7. Dialectical Paradigm Audits: Systematically evaluate allied and rejected theories with precise functional reasons for agreement or rejection.\n"
            "8. Concrete Engineering Platforms: Detail computational mechanisms and architectures (e.g. NCAs, RCNs, attractor manifolds).\n"
            "9. Empirical Falsification Criteria & Staged Roadmap: Formulate explicit numbered falsification conditions and staged research phases.\n"
            "10. Condensed Formal Mathematical Spine & Scholarly Synthesis: Compile the complete consolidated LaTeX equation block at the conclusion.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground all formalisms, lemmas, and proofs strictly in the authentic reference data provided above.\n"
            "2. Maintain formal academic tone, high information density, and precise LaTeX notation throughout."
        )

    def get_artifact_category(self) -> str:
        return "articles"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Academic Monograph — {source_label}"


class NonConsensusContrarianStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR NON-CONSENSUS CONTRARIAN THESIS & FIRST-PRINCIPLES REFRAMING ({source_label.upper()}):\n"
            "Formulate an uncompromising, first-principles contrarian analysis of the consensus paradigm presented in the source context.\n"
            "Structure your thesis across the following analytical architecture:\n"
            "1. The Orthodox Consensus Narrative: Identify what mainstream thinking takes for granted.\n"
            "2. Institutional & Epistemic Blind Spots: Expose unexamined assumptions, flawed incentives, or ignored anomalies.\n"
            "3. First-Principles Counter-Thesis: Construct a rigorous, logically sound alternative hypothesis grounded in anomalous edge cases (using boxed causal flows \\boxed{A \\to B}).\n"
            "4. Mathematical State Space & Formal Reconstruction: Reconstruct the counter-thesis in LaTeX ($...$ and $$...$$).\n"
            "5. Epistemic Status & Falsification Matrix: Provide a markdown table of empirical conditions that would prove or disprove the thesis.\n"
            "6. Asymmetric Second-Order Strategic Implications: Cascading scientific, technological, and governance consequences.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground the contrarian critique in authentic empirical anomalies and mathematical constraints from the source data.\n"
            "2. Ensure the thesis is intellectually rigorous, logically sound, and actionable."
        )

    def get_artifact_category(self) -> str:
        return "contrarian"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Non-Consensus Thesis — {source_label}"


class ViralPublicNarrativeStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR HIGH-IMPACT VIRAL ESSAY & THOUGHT LEADERSHIP PUBLICATION ({source_label.upper()}):\n"
            "Craft an exceptionally engaging, high-signal public publication (Substack essay, X thread, or LinkedIn thought leadership article) distilling the core breakthrough of the source text.\n"
            "Rhetorical Architecture:\n"
            "1. Irresistible Hook: Open with a provocative paradox, counter-intuitive insight, or paradigm shift that grabs immediate attention.\n"
            "2. High-Signal Concept Distillation: Translate dense jargon and mathematical models into intuitive, unforgettable visual analogies without losing technical accuracy.\n"
            "3. Pacing & Whitespace: Use modular bullet points, bold callouts, and clean formatting for effortless readability.\n"
            "4. The 'So What?' (Real-world stakes): Explain why this matters for the future of AI, science, technology, or humanity.\n"
            "5. Actionable Conclusion & Discussion Spark: Conclude with a thought-provoking inquiry that triggers viral discourse.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. All factual assertions and core mechanisms must be 100% faithful to the authentic source reference.\n"
            "2. Maximize clarity and punch without sacrificing scientific integrity."
        )

    def get_artifact_category(self) -> str:
        return "narratives"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Executive Thought Leadership — {source_label}"


class FormulaExtractionStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR COMPREHENSIVE MATHEMATICAL FORMALISM & DERIVATION MONOGRAPH ({source_label.upper()}):\n"
            "Extract, formulate, derive, and rigorously explain all formal mathematical objects, state spaces, measurable spaces, "
            "Markov transition kernels, dynamical equations, asymptotic properties, and theorems from the authentic source text above.\n"
            "Structure your mathematical treatise across the following formal architecture:\n"
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

    def get_artifact_category(self) -> str:
        return "mathematics"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Mathematical Formalisms — {source_label}"


class ComprehensiveOverviewStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR EXHAUSTIVE PUBLICATION-GRADE RESEARCH MONOGRAPH ({source_label.upper()}):\n"
            "Provide an exhaustive, publication-grade academic synthesis and treatise based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
            "DO NOT write a superficial 5-paragraph summary. Enforce the 10-Layer Publication Monograph Architecture across granular, logically progressive thematic chapters:\n"
            "1. Source Boundary & Epistemic Declaration: Explicitly declare the primary evidentiary basis and distinguish direct source claims from formal analytical reconstructions.\n"
            "2. Abstract & Core Ontological Inversion: Formulate the foundational thesis, explanatory target, and construct boxed conceptual causal chains (\\boxed{A \\to B}) and vertical dependency diagrams.\n"
            "3. Epistemic Status Classification Matrix: Construct a comprehensive markdown table categorizing every major proposition as a Definition, Axiom, Hypothesis, Constructive Theorem, Conjecture, or Unresolved Open Limit.\n"
            "4. Formal Mathematical State Space Modeling: Derive and reconstruct all state spaces $\\mathcal{S}$, transition operators $\\mathcal{T}$, convolution kernels $\\mathcal{L}$, constraint functionals $\\mathcal{C}$, and optimization bounds in standard LaTeX display math ($...$ and $$...$$).\n"
            "5. Domain-to-Domain Isomorphism Alignment Tables: Construct explicit tables mapping parameters and variables across domains (e.g. Dynamical States $\\leftrightarrow$ Quantum Observables).\n"
            "6. Taxonomical Decompositions & Logical Non-Implications: Construct category definition tables with explicit non-implication relations ($A \\not\\Rightarrow B$, e.g. $\\text{consciousness} \\not\\Rightarrow \\text{self}$).\n"
            "7. Dialectical Paradigm Audits: Systematically evaluate allied and rejected theories (e.g. GWT, HOT, FEP, AST, IIT, Searle) with precise functional reasons for agreement or rejection.\n"
            "8. Concrete Experimental Platforms & Distributed Architectures: Formulate computational mechanisms for experimental platforms (e.g. NCAs, RCNs, attractor manifolds in artificial psychology).\n"
            "9. Empirical Falsification Criteria & Staged Research Roadmap: Formulate explicit numbered falsification conditions and a staged engineering roadmap.\n"
            "10. Ethical Asymmetry, Governance & Condensed Formal Mathematical Spine: Detail ethical risk profiles, the distributed governance trigger (\\boxed{\\text{architect} \\neq \\text{sovereign}}), and compile the complete consolidated LaTeX equation block at the conclusion.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground every claim and formula strictly in the authentic reference data provided above.\n"
            "2. DO NOT mention external frameworks unless directly relevant to the document's dialectical positioning.\n"
            "3. Maintain exhaustive academic depth, rigorous information density, and publication-grade LaTeX formatting throughout."
        )

    def get_artifact_category(self) -> str:
        return "research"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Comprehensive Treatise — {source_label}"


class ConceptualQAStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION: Answer the User Directive directly, comprehensively, and factually based exclusively on the provided text for {source_label}.\n"
            "Ground all factual claims strictly in the authentic reference data provided above."
        )

    def get_artifact_category(self) -> str:
        return "research"

    def get_default_artifact_title(self, source_label: str) -> str:
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

    def synthesize_directive(self, modality: DirectiveModality, source_label: str) -> str:
        strategy = self.get_strategy(modality)
        return strategy.build_directive(source_label)

    def get_artifact_metadata(self, modality: DirectiveModality, source_label: str) -> Tuple[str, str]:
        strategy = self.get_strategy(modality)
        return strategy.get_artifact_category(), strategy.get_default_artifact_title(source_label)
