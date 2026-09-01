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
            f"INSTRUCTION FOR MULTI-SOURCE COMPARATIVE ANALYSIS ({source_label.upper()}):\n"
            "Conduct an exhaustive, multidimensional comparative analysis across all referenced source documents, URLs, or frameworks provided above.\n"
            "Structure your analysis to clearly address:\n"
            "1. Core Ontological & Methodological Foundations (Where do the paradigms agree vs. fundamentally clash?).\n"
            "2. Mathematical Formalism & Empirical Architecture Concordance (Compare specific equations, kernels, metric spaces, or architectures).\n"
            "3. Key Assumptions & Boundary Condition Matrix (Tabular or structured breakdown of unstated assumptions, scope limits, and axioms).\n"
            "4. Theoretical Synthesis & Strategic Trade-Offs.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground all comparative statements strictly in the corresponding reference sections provided above.\n"
            "2. DO NOT attribute concepts from Source A to Source B unless explicitly stated in the source text.\n"
            "3. Clearly cite specific section numbers, page corridors, or URLs for each comparative claim."
        )

    def get_artifact_category(self) -> str:
        return "comparisons"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Comparative Analysis — {source_label}"


class CriticalAnalysisStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR CRITICAL ANALYSIS, DIALECTICAL AUDIT & PEER REVIEW ({source_label.upper()}):\n"
            "Perform an adversarial, epistemically rigorous critical audit of the source document(s), URL(s), or framework(s) above.\n"
            "Structure your evaluation across the following analytical dimensions:\n"
            "1. Axiomatic & Methodological Stress-Testing (Audit core lemmas, definitions, and experimental/theoretical setups for hidden vulnerabilities).\n"
            "2. Logical Coherence & Epistemic Gaps (Identify tautologies, unproven inferences, circular definitions, or unstated assumptions).\n"
            "3. Empirical & Theoretical Boundary Condition Failures (Where does this model break down under extreme parameters or counter-examples?).\n"
            "4. Alternative Paradigms & Constructive Epistemic Reformulation.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Directly quote or reference exact statements, equations, or theorems from the text before presenting your critique.\n"
            "2. Ensure critiques are grounded in formal scientific, mathematical, or empirical reasoning rather than generic skepticism.\n"
            "3. Do not misrepresent the author's stated positions."
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
            "Author a formal, publication-grade scholarly research paper based on the provided reference grounding context.\n"
            "Follow standard academic journal/preprint structure:\n"
            "# [Paper Title]\n"
            "## Abstract (Rigorous, self-contained mathematical/conceptual summary)\n"
            "## 1. Introduction & Epistemic Problem Formulation\n"
            "## 2. Theoretical Foundations & Related Literature Positioning\n"
            "## 3. Mathematical State Space Modeling & Formal Definitions (Use LaTeX notation $...$ and $$...$$)\n"
            "## 4. Analytical Results, Proofs & Theoretical Corroboration\n"
            "## 5. Discussion, Limitations & Future Research Directions\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Derive all mathematical formalisms, lemmas, and proofs strictly from the authentic source text.\n"
            "2. Maintain formal academic tone, high information density, and precise notation throughout."
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
            "Structure your thesis to illuminate:\n"
            "1. The Orthodox Consensus Narrative (What does mainstream thinking take for granted?).\n"
            "2. Institutional & Epistemic Blind Spots (Where are the hidden assumptions, flawed incentive structures, or unexamined anomalies?).\n"
            "3. First-Principles Counter-Thesis (Construct a rigorous, logically sound alternative hypothesis grounded in anomalous edge cases).\n"
            "4. Asymmetric Second-Order Implications (If the contrarian thesis holds, what are the cascading scientific, technological, or strategic consequences?).\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground the contrarian critique in authentic empirical anomalies and mathematical constraints from the source data.\n"
            "2. Ensure the thesis is intellectually rigorous, logically sound, and actionable rather than superficial contrarianism."
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
            f"INSTRUCTION FOR MATHEMATICAL EXTRACTION & FORMAL ANALYSIS ({source_label.upper()}):\n"
            "Extract, formulate, and rigorously explain all formal mathematical definitions, tuples, measurable spaces, "
            "Markov transition kernels, dynamical equations, asymptotic properties, and theorems from the authentic source text above.\n"
            "For each mathematical object:\n"
            "1. State the exact formula using standard LaTeX notation ($...$ or $$...$$).\n"
            "2. Provide an exhaustive, rigorous explanation of every variable, space, kernel, and operational mechanic strictly grounded in this paper.\n"
            "3. Detail its theoretical purpose and proof structure directly from the text.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground every formula and definition strictly in the authentic reference data provided above.\n"
            "2. DO NOT mention or blend external frameworks unless explicitly present in this specific document."
        )

    def get_artifact_category(self) -> str:
        return "mathematics"

    def get_default_artifact_title(self, source_label: str) -> str:
        return f"Mathematical Formalisms — {source_label}"


class ComprehensiveOverviewStrategy(BaseDirectiveStrategy):
    def build_directive(self, source_label: str) -> str:
        return (
            f"INSTRUCTION FOR COMPREHENSIVE RESEARCH ANALYSIS ({source_label.upper()}):\n"
            "Provide an exhaustive, publication-grade academic analysis based STRICTLY AND EXCLUSIVELY on the authentic source document text provided above.\n"
            "Synthesize the core executive thesis, theoretical paradigms, chapter corridors, mathematical formalisms, and strategic implications.\n\n"
            "STRICT FACTUAL GROUNDING LAWS:\n"
            "1. Ground every claim strictly in the authentic reference data provided above.\n"
            "2. DO NOT mention or blend external frameworks unless explicitly named in this specific document.\n"
            "3. Quote exact formulas and definitions directly from the text."
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
