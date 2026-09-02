"""
Universal Semantic Intent Decomposer & Ambiguity Evaluator
==========================================================
Parses arbitrary end-user prompts into structured Goal Tuples (G), extracting
core objectives, latent constraints, capability domain mappings, sub-agent assignees,
and ambiguity scores to prevent hallucinated generation.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field

from ..logging_config import get_logger

logger = get_logger("Engine.IntentDecomposer")


class IntentType(str, Enum):
    INFORMATIONAL_QA = "INFORMATIONAL_QA"
    STRATEGIC_ADVISORY = "STRATEGIC_ADVISORY"
    DEEP_RESEARCH = "DEEP_RESEARCH"
    CODE_ENGINEERING = "CODE_ENGINEERING"
    FINANCIAL_MODELING = "FINANCIAL_MODELING"
    MULTI_STEP_DAG_EXECUTION = "MULTI_STEP_DAG_EXECUTION"
    SYSTEM_INTROSPECTION = "SYSTEM_INTROSPECTION"
    GOVERNANCE_SECURITY = "GOVERNANCE_SECURITY"
    GENERAL_CONVERSATIONAL = "GENERAL_CONVERSATIONAL"


class DirectiveModality(str, Enum):
    FORMULA_EXTRACTION = "FORMULA_EXTRACTION"
    COMPREHENSIVE_OVERVIEW = "COMPREHENSIVE_OVERVIEW"
    MULTI_DOCUMENT_COMPARISON = "MULTI_DOCUMENT_COMPARISON"
    CRITICAL_ANALYSIS = "CRITICAL_ANALYSIS"
    CREATIVE_WRITING = "CREATIVE_WRITING"
    ACADEMIC_ARTICLE = "ACADEMIC_ARTICLE"
    NON_CONSENSUS_CONTRARIAN = "NON_CONSENSUS_CONTRARIAN"
    VIRAL_PUBLIC_NARRATIVE = "VIRAL_PUBLIC_NARRATIVE"
    CONCEPTUAL_QA = "CONCEPTUAL_QA"


class ConversationalBandwidth(str, Enum):
    EXHAUSTIVE_MONOGRAPH = "exhaustive_monograph"
    TECHNICAL_DOSSIER = "technical_dossier"
    EXECUTIVE_BRIEFING = "executive_briefing"
    DIRECT_PRECISION_QA = "direct_precision_qa"
    NATURAL_CONVERSATION = "natural_conversation"


class DocumentGenre(str, Enum):
    SCIENTIFIC_MATHEMATICAL = "SCIENTIFIC_MATHEMATICAL"
    BIOMEDICAL_CLINICAL = "BIOMEDICAL_CLINICAL"
    BUSINESS_FINANCIAL = "BUSINESS_FINANCIAL"
    LEGAL_REGULATORY = "LEGAL_REGULATORY"
    ENGINEERING_SYSTEMS = "ENGINEERING_SYSTEMS"
    STRATEGIC_POLICY = "STRATEGIC_POLICY"
    EDUCATIONAL_PEDAGOGICAL = "EDUCATIONAL_PEDAGOGICAL"
    NARRATIVE_LITERARY = "NARRATIVE_LITERARY"
    GENERAL_DOCUMENT = "GENERAL_DOCUMENT"


def detect_document_genre(text: str = "", filename: str = "", raw_prompt: str = "") -> DocumentGenre:
    """
    Deterministically profiles the intrinsic epistemic genre of a document or query context
    by analyzing semantic vocabulary, mathematical syntax, financial metrics, legal phrasing,
    engineering terms, and structural markers.
    """
    combined = f"{filename} {raw_prompt} {text[:8000]}".lower()

    # 1. Scientific & Mathematical (Theorems, proofs, physics, math symbols, academic markers)
    math_symbols = ["\\mathcal", "\\int", "\\sum", "\\to", "\\times", "\\in", "\\mathbb", "\\partial", "\\boxed", "$$"]
    math_symbol_hits = sum(1 for sym in math_symbols if sym.lower() in combined)
    sci_keywords = [
        "theorem", "lemma", "proof", "axiom", "hypothesis", "corollary", "quantum",
        "wavefunction", "state space", "measurable space", "markov", "topology", "physics",
        "consciousness", "neuroscience", "eigenvalue", "kernel", "operator", "falsification",
        "empirical study", "methodology", "doi:", "arxiv", "bibtex", "peer review",
        "objects of consciousness", "cimc", "hoffman", "prakash"
    ]
    sci_score = sum(2 for kw in sci_keywords if kw in combined) + math_symbol_hits * 3

    # 2. Biomedical & Clinical (Clinical trials, pharmacology, oncology, endpoints, hazard ratios)
    bio_keywords = [
        "clinical trial", "phase i", "phase ii", "phase iii", "phase iv", "hazard ratio",
        "overall survival", "progression-free", "adverse event", "pharmacology", "pharmacokinetics",
        "pharmacodynamics", "kaplan-meier", "endpoints", "biomarker", "fda approval", "ema",
        "oncology", "randomized controlled", "placebo", "cohort", "inclusion criteria",
        "exclusion criteria", "toxicity", "dose-limiting", "monoclonal antibody", "nejm", "lancet"
    ]
    bio_score = sum(2 for kw in bio_keywords if kw in combined)

    # 3. Business, Financial & Venture (Unit economics, balance sheets, pitch decks, SEC filings)
    biz_keywords = [
        "ebitda", "arr", "mrr", "cac", "ltv", "balance sheet", "cash flow", "income statement",
        "valuation", "cap table", "pitch deck", "tam", "sam", "som", "gross margin", "operating margin",
        "p&l", "financial model", "quarterly results", "10-k", "10-q", "sec filing", "dividend",
        "guidance", "revenue growth", "burn rate", "runway", "go-to-market", "gtm", "market sizing",
        "customer acquisition", "churn rate", "net retention", "series a", "series b", "seed round"
    ]
    biz_score = sum(2 for kw in biz_keywords if kw in combined)

    # 4. Legal, Contractual & Regulatory (MSAs, NDAs, covenants, indemnification, statutes)
    legal_keywords = [
        "agreement", "contract", "nda", "msa", "terms of service", "privacy policy",
        "indemnification", "indemnity", "liability", "jurisdiction", "covenants",
        "representations and warranties", "force majeure", "arbitration", "statute",
        "regulation", "gdpr", "hipaa", "compliance audit", "subcontractor", "governing law",
        "severability", "termination clause", "herein", "hereto", "whereas", "in witness whereof"
    ]
    legal_score = sum(2 for kw in legal_keywords if kw in combined)

    # 5. Engineering & Systems Architecture (RFCs, APIs, SLAs, distributed topologies)
    eng_keywords = [
        "rfc", "api contract", "endpoint", "microservice", "latency", "throughput", "sla",
        "slo", "sli", "kubernetes", "docker", "failover", "circuit breaker", "load balancer",
        "grpc", "protobuf", "graphql", "data pipeline", "database schema", "cache invalidation",
        "concurrency", "distributed system", "message queue", "kafka", "redis cluster"
    ]
    eng_score = sum(2 for kw in eng_keywords if kw in combined)

    # 6. Strategic Policy & Institutional Governance (Charters, whitepapers, geopolitics)
    policy_keywords = [
        "public policy", "geopolitical", "institutional governance", "treaty", "stakeholder impact",
        "charter", "regulatory framework", "ethical guidelines", "socioeconomic", "diplomacy",
        "sovereignty", "policy trade-off", "public sector", "fiduciary stewardship"
    ]
    policy_score = sum(2 for kw in policy_keywords if kw in combined)

    # 7. Educational & Pedagogical (Curricula, tutorials, worked examples, misconceptions)
    edu_keywords = [
        "curriculum", "syllabus", "lesson plan", "tutorial", "textbook", "learning objectives",
        "worked example", "misconceptions", "practice problems", "active recall", "pedagogy",
        "rubric", "study guide", "quiz", "homework", "concept map", "prerequisites",
        "scaffolding", "masterclass", "step-by-step guide"
    ]
    edu_score = sum(2 for kw in edu_keywords if kw in combined)

    # 8. Narrative, Books & Essays (Literary, memoirs, biographies, dialogue)
    narrative_keywords = [
        "novel", "memoir", "biography", "fiction", "character development", "protagonist",
        "narrative arc", "thematic motif", "allegory", "poetic", "screenplay", "prose style",
        "historical narrative", "literary criticism"
    ]
    narrative_score = sum(2 for kw in narrative_keywords if kw in combined)

    scores = {
        DocumentGenre.SCIENTIFIC_MATHEMATICAL: sci_score,
        DocumentGenre.BIOMEDICAL_CLINICAL: bio_score,
        DocumentGenre.BUSINESS_FINANCIAL: biz_score,
        DocumentGenre.LEGAL_REGULATORY: legal_score,
        DocumentGenre.ENGINEERING_SYSTEMS: eng_score,
        DocumentGenre.STRATEGIC_POLICY: policy_score,
        DocumentGenre.EDUCATIONAL_PEDAGOGICAL: edu_score,
        DocumentGenre.NARRATIVE_LITERARY: narrative_score,
    }

    best_genre, best_score = max(scores.items(), key=lambda item: item[1])
    return best_genre if best_score >= 2 else DocumentGenre.GENERAL_DOCUMENT


def detect_conversational_bandwidth(
    raw_prompt: str = "",
    modality: DirectiveModality = DirectiveModality.CONCEPTUAL_QA,
    genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT,
    text_sample: str = ""
) -> ConversationalBandwidth:
    """
    Deterministically profiles the required interaction density and conversational pacing.
    """
    prompt_lower = raw_prompt.lower().strip()

    # 1. Direct Precision QA (Pinpoint facts, formula lookups, single metric queries)
    precision_triggers = [
        "what is the formula", "extract the formula", "what is the equation", "extract equation",
        "what was the ebitda", "what is the ebitda", "what is the arr", "what is the cac",
        "what is the port", "what is the liability cap", "is indemnification",
        "what section", "what page", "exact definition of", "define "
    ]
    if any(pt in prompt_lower for pt in precision_triggers) and len(prompt_lower) < 180:
        return ConversationalBandwidth.DIRECT_PRECISION_QA

    # 2. Executive Briefing (TL;DR, High-level, Executive Summary)
    briefing_triggers = [
        "executive summary", "briefing", "high-level", "tl;dr", "tldr", "quick summary",
        "executive overview", "bullet points", "key takeaways", "highlights", "brief overview", "1-page"
    ]
    if any(bt in prompt_lower for bt in briefing_triggers):
        return ConversationalBandwidth.EXECUTIVE_BRIEFING

    # 3. Exhaustive Monograph (Explicit publication-grade, monograph, treatise requests)
    exhaustive_triggers = [
        "exhaustive", "monograph", "treatise", "publication-grade", "publication grade",
        "comprehensive analysis", "full paper analysis", "deep-dive monograph", "academic synthesis",
        "exhaustive analysis", "complete breakdown"
    ]
    if any(et in prompt_lower for et in exhaustive_triggers) or modality in [
        DirectiveModality.ACADEMIC_ARTICLE, DirectiveModality.MULTI_DOCUMENT_COMPARISON, DirectiveModality.CRITICAL_ANALYSIS
    ]:
        return ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH

    # 4. Natural Conversation (Dialogue, open-ended, brainstorming, co-working, greetings)
    conversational_triggers = [
        "what do you think", "how do you feel", "can we brainstorm", "help me brainstorm",
        "let's work together", "step by step", "step-by-step", "hello", "hi ", "hey",
        "let's discuss", "what are your thoughts", "can you help me understand"
    ]
    if any(ct in prompt_lower for ct in conversational_triggers) or (
        modality == DirectiveModality.CONCEPTUAL_QA and len(prompt_lower) < 250 and not any(w in prompt_lower for w in ["analyze", "evaluate", "breakdown", "dossier", "spec", "architecture"])
    ):
        return ConversationalBandwidth.NATURAL_CONVERSATION

    # 5. Technical Dossier (Default for technical specs, architectural deep-dives, RFCs)
    if modality == DirectiveModality.FORMULA_EXTRACTION:
        return ConversationalBandwidth.TECHNICAL_DOSSIER
    if genre in [DocumentGenre.ENGINEERING_SYSTEMS, DocumentGenre.LEGAL_REGULATORY, DocumentGenre.BUSINESS_FINANCIAL]:
        return ConversationalBandwidth.TECHNICAL_DOSSIER

    return ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH


class CapabilityDomain(str, Enum):
    COMPUTE_INFERENCE = "compute_and_inference"
    TOPOLOGICAL_PHYSICS = "topological_physics"
    AUTONOMOUS_SUBAGENTS = "autonomous_subagents"
    MEMORY_FABRIC = "memory_and_knowledge"
    ZERO_TRUST_SECURITY = "zero_trust_security"
    OMNICHANNEL_BRIDGES = "omnichannel_bridges"
    GENERAL_EXECUTIVE = "general_executive"


class ParsedGoalTuple(BaseModel):
    """
    Structured representation of parsed user intent and objective constraints.
    Grounded in Topological Affordance (G) and S-CoT verification.
    """
    raw_prompt: str
    core_objective: str
    intent_type: IntentType
    directive_modality: DirectiveModality = DirectiveModality.CONCEPTUAL_QA
    detected_genre: DocumentGenre = DocumentGenre.GENERAL_DOCUMENT
    detected_bandwidth: ConversationalBandwidth = ConversationalBandwidth.EXHAUSTIVE_MONOGRAPH
    detected_urls: List[str] = Field(default_factory=list)
    domain: CapabilityDomain
    suggested_agent: str = "executive"
    constraints: List[str] = Field(default_factory=list)
    ambiguity_score: float = 0.0  # 0.0 (crystal clear) to 1.0 (completely ambiguous)
    is_ambiguous: bool = False
    clarification_options: List[str] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    is_actionable_dag: bool = False
    confidence: float = 1.0


class IntentDecomposer:
    """
    Deterministic semantic intent parser and goal extractor.
    Maps continuous prompt spaces (W) into structured simplicial goal complexes (X).
    """

    # Skill routing mapping based on 14 specialized installed skills
    SKILL_MAPPING: Dict[str, Dict[str, Any]] = {
        "codi_opencode_harness": {
            "agent": "codi",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.CODE_ENGINEERING,
            "keywords": ["code", "refactor", "bug", "ast", "test", "python", "typescript", "react", "fastapi", "git diff", "compiler", "lsp", "pull request", "pr", "repo", "function", "class", "syntax", "endpoint", "database schema", "migration", "unittest", "pytest"]
        },
        "strategic_planning_execution": {
            "agent": "spe",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.STRATEGIC_ADVISORY,
            "keywords": ["strategic plan", "okr", "kpi", "balanced scorecard", "workstream", "milestone", "roadmap", "executive dashboard", "strategy", "q1", "q2", "q3", "q4", "initiatives", "performance management"]
        },
        "strategic_workforce_design": {
            "agent": "swd",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.STRATEGIC_ADVISORY,
            "keywords": ["workforce", "headcount", "hiring plan", "contractor", "talent", "team structure", "org chart", "role", "capacity", "staffing", "agent vs human"]
        },
        "use_of_funds_capital_allocation": {
            "agent": "suf",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.FINANCIAL_MODELING,
            "keywords": ["use of funds", "burn rate", "runway", "capital allocation", "gross burn", "net burn", "covenant", "cash flow", "budget", "financial model", "expenses", "opex", "capex"]
        },
        "ownership_capital_strategy": {
            "agent": "oc",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.FINANCIAL_MODELING,
            "keywords": ["cap table", "equity", "dilution", "option pool", "liquidation waterfall", "valuation", "seed round", "series a", "series b", "safe", "convertible note", "shares", "vesting", "ownership"]
        },
        "founder_discovery": {
            "agent": "executive",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.STRATEGIC_ADVISORY,
            "keywords": ["founder discovery", "founder narrative", "mission", "vision", "storytelling", "origin story", "pitch deck narrative", "positioning", "core belief"]
        },
        "founder_insight_market_shift": {
            "agent": "executive",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.STRATEGIC_ADVISORY,
            "keywords": ["market shift", "contrarian belief", "macro trend", "market opportunity", "industry shift", "thesis", "market timing", "disruption"]
        },
        "founding_team_leadership_architecture": {
            "agent": "executive",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.STRATEGIC_ADVISORY,
            "keywords": ["co-founder", "founding team", "decision rights", "raci", "rapid", "reverse vesting", "acceleration", "leadership team", "co-founder equity", "founder conflict"]
        },
        "investment_readiness": {
            "agent": "rocco",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.STRATEGIC_ADVISORY,
            "keywords": ["investor due diligence", "data room", "pitch deck", "investment readiness", "investor memo", "term sheet", "fundraising", "due diligence checklist"]
        },
        "legal_document_lifecycle": {
            "agent": "executive",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.GOVERNANCE_SECURITY,
            "keywords": ["contract", "legal document", "ip assignment", "nda", "bylaws", "incorporation", "board consent", "advisory agreement", "employment agreement", "compliance"]
        },
        "human_resource_onboarding": {
            "agent": "executive",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.STRATEGIC_ADVISORY,
            "keywords": ["employee onboarding", "30-60-90", "new hire", "onboarding roadmap", "ttp", "time to productivity", "employee integration"]
        },
        "organizational_knowledge_document_management": {
            "agent": "executive",
            "domain": CapabilityDomain.MEMORY_FABRIC,
            "intent": IntentType.INFORMATIONAL_QA,
            "keywords": ["knowledge base", "document taxonomy", "organizational memory", "standardized taxonomy", "company wiki", "documentation archive", "knowledge graph asset"]
        },
        "founder_education_decision_intelligence": {
            "agent": "executive",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.STRATEGIC_ADVISORY,
            "keywords": ["decision journal", "mental model", "decision confidence", "learning module", "second-order thinking", "inversion", "first principles", "executive decision"]
        },
        "compensation_strategy": {
            "agent": "swd",
            "domain": CapabilityDomain.AUTONOMOUS_SUBAGENTS,
            "intent": IntentType.FINANCIAL_MODELING,
            "keywords": ["compensation band", "equity incentive", "market percentile", "total rewards", "base salary", "bonus structure", "option grant", "benchmarking"]
        }
    }

    # Tool routing mapping based on 15 installed backend tools
    TOOL_MAPPING: Dict[str, List[str]] = {
        "autonomous_software_engineering_tool": ["code", "refactor", "ast", "syntax", "git diff", "unittest", "pytest", "bug", "patch"],
        "strategic_planning_execution_tool": ["balanced scorecard", "okr", "kpi", "strategic roadmap", "workstream"],
        "strategic_workforce_design_tool": ["workforce", "hiring", "org structure", "headcount", "staffing"],
        "use_of_funds_capital_allocation_tool": ["use of funds", "burn rate", "runway", "cash flow", "capital allocation"],
        "ownership_capital_strategy_tool": ["cap table", "dilution", "liquidation waterfall", "option pool", "valuation"],
        "founder_narrative_tool": ["founder story", "narrative", "origin", "core positioning"],
        "founder_insight_market_shift_tool": ["market shift", "contrarian", "macro trend", "market opportunity"],
        "founding_team_leadership_tool": ["founding team", "co-founder", "raci", "decision rights"],
        "investment_readiness_tool": ["data room", "investor readiness", "due diligence", "pitch deck audit"],
        "legal_document_lifecycle_tool": ["legal contract", "nda", "ip assignment", "compliance agreement"],
        "human_resource_onboarding_tool": ["onboarding", "30-60-90", "new hire integration"],
        "organizational_knowledge_document_tool": ["document archive", "knowledge repository", "taxonomy"],
        "founder_education_decision_tool": ["decision journal", "mental model", "decision intelligence"],
        "compensation_strategy_tool": ["compensation band", "equity pool", "total rewards", "salary benchmark"],
        "agentic_registration_tool": ["register agent", "subagent manifest", "tool registry"]
    }

    def __init__(self):
        pass

    def decompose(self, prompt: str, context: Optional[str] = None) -> ParsedGoalTuple:
        """
        Decomposes an arbitrary natural language prompt into a structured ParsedGoalTuple.
        """
        clean_prompt = prompt.strip()
        body_lower = clean_prompt.lower()

        # 1. Check for Introspection / Capability Queries (Alluci-specific)
        doc_query_patterns = [
            r"\b(paper|whitepaper|white-paper|document|pdf|article|report|study|author|hoffman|cimc|uploaded)\b",
            r"\b(\.pdf|\.docx|\.txt|\.md)\b"
        ]
        is_doc_query = any(re.search(p, body_lower) for p in doc_query_patterns)

        introspection_patterns = [
            r"\b(what|list|explain|show|describe|tell me about)\b.*\b(skill|skills|tool|tools|capability|capabilities|manifest|commands|sub-?agents|what can you do|what makes you different)\b",
            r"\b(who are you|what are you|inventory|what do you do)\b",
            r"\b(your architecture|alluci architecture|alluci codebase|alluci application|alluci system|models\.py|hlsm_manager|verusid|dpk|ppn|pmet filtration|avl gate|s-cot|simplicial chain-of-thought)\b"
        ]
        is_introspection = any(re.search(p, body_lower) for p in introspection_patterns) and not is_doc_query
        
        # 2. Check for Deep Web Research Intent (Requires explicit external web harvesting directives)
        research_patterns = [
            r"\b(deep research|search the web|scour the web|scour the internet|find online|latest news online|harvest web data|search online for|look up online|deep web research)\b"
        ]
        is_research = any(re.search(p, body_lower) for p in research_patterns)

        # 3. Check for Code / Engineering Intent
        code_patterns = [
            r"\b(code|refactor|debug|fix the bug|syntax error|write a function|write a script|create an endpoint|test|pytest|ast|git|pull request)\b",
            r"\b(python|typescript|javascript|react|fastapi|sqlmodel|kuzudb|sqlite|css|html)\b",
            r"```|\.py\b|\.ts\b|\.tsx\b|\.json\b|\.md\b"
        ]
        is_code = any(re.search(p, body_lower) for p in code_patterns)

        # 4. Check for Negation Directives (e.g., "do not apply", "without frameworks", "never run", "avoid DAG")
        negation_pattern = r'\b(do not|don\'t|dont|never|without|avoid|refrain from|omit|skip)\s+([a-z\s]{0,20})?(apply|use|execute|run|implement|build|model|framework|skill|dag|tools?)\b'
        has_negation = bool(re.search(negation_pattern, body_lower))

        # 5. Check for Comparative Intent (e.g., "compare X vs Y", "contrast A and B")
        comparative_patterns = [
            r"\b(compare|contrast|versus|\bvs\b|evaluate against|differentiate between|comparison between|distinguish between)\b"
        ]
        is_comparative = any(re.search(p, body_lower) for p in comparative_patterns)

        # 6. Check for Informational / Explanatory / Summarization Intent
        informational_patterns = [
            r"\b(explain|summarize|summary|overview|what is|tell me about|walk me through|clarify|elaborate|read and summarize|break down|synthesize)\b"
        ]
        is_informational = any(re.search(p, body_lower) for p in informational_patterns) or is_comparative

        # 7. Check for Actionable Multi-Step Execution (DAG Plan)
        action_verbs = [
            r"\b(run|execute|build|implement|create|generate a plan|model|calculate|analyze and draft|audit and report|prepare a data room|set up|automate|conduct)\b"
        ]
        if not has_negation and not is_informational:
            action_verbs.append(r"\b(use|apply|discover)\b")

        is_actionable = any(re.search(p, body_lower) for p in action_verbs) and not is_informational and not has_negation

        # 8. Extract Domain, Matched Skills & Tools
        matched_skills: List[str] = []
        matched_tools: List[str] = []
        suggested_agent = "executive"
        domain = CapabilityDomain.GENERAL_EXECUTIVE
        intent_type = IntentType.GENERAL_CONVERSATIONAL

        # Explicit skill ID matching (e.g. fnd_02, codi_01, spe_01, auth_01)
        if not has_negation and not is_informational:
            explicit_skill_ids = re.findall(r'\b([a-z]{2,5}_\d{2})\b', body_lower)
            for sid in explicit_skill_ids:
                if sid not in matched_skills:
                    matched_skills.append(sid)
                    domain = CapabilityDomain.AUTONOMOUS_SUBAGENTS

            # Explicit tool ID matching (e.g. fnd_tool_02, founder_insight_market_shift_tool)
            explicit_tool_ids = re.findall(r'\b([a-z0-9_]+_tool(?:_[0-9]+)?)\b', body_lower)
            for tid in explicit_tool_ids:
                if tid not in matched_tools:
                    matched_tools.append(tid)

            for skill_id, meta in self.SKILL_MAPPING.items():
                for kw in meta["keywords"]:
                    if re.search(rf"\b{re.escape(kw)}\b", body_lower):
                        if skill_id not in matched_skills:
                            matched_skills.append(skill_id)
                            suggested_agent = meta["agent"]
                            domain = meta["domain"]
                            intent_type = meta["intent"]
                        break

            for tool_name, keywords in self.TOOL_MAPPING.items():
                for kw in keywords:
                    if re.search(rf"\b{re.escape(kw)}\b", body_lower):
                        if tool_name not in matched_tools:
                            matched_tools.append(tool_name)
                        break

        # Refine Intent Type
        if is_code:
            intent_type = IntentType.CODE_ENGINEERING
            suggested_agent = "codi"
            domain = CapabilityDomain.AUTONOMOUS_SUBAGENTS
        elif is_introspection and not (is_actionable and (matched_skills or matched_tools)):
            intent_type = IntentType.SYSTEM_INTROSPECTION
            domain = CapabilityDomain.AUTONOMOUS_SUBAGENTS
        elif is_informational:
            intent_type = IntentType.INFORMATIONAL_QA
            domain = CapabilityDomain.GENERAL_EXECUTIVE
            suggested_agent = "executive"
        elif is_research and not matched_skills:
            intent_type = IntentType.DEEP_RESEARCH
            suggested_agent = "rocco"
            domain = CapabilityDomain.AUTONOMOUS_SUBAGENTS
        elif is_actionable and len(matched_skills) >= 1 and not has_negation:
            intent_type = IntentType.MULTI_STEP_DAG_EXECUTION

        # 8. Extract Constraints
        constraints: List[str] = []
        # Budget constraint
        budget_match = re.search(r'(\$\s*[\d,]+(?:\.\d+)?|\b\d+(?:\.\d+)?\s*(?:k|m|million|billion|thousand)\s*(?:dollars?|usd)?|\bbudget of\s*[^,\.]+)', body_lower)
        if budget_match:
            constraints.append(f"Budget: {budget_match.group(0).strip()}")

        # Time horizon constraint
        time_match = re.search(r'(\b\d+\s*(?:days?|weeks?|months?|quarters?|years?)\b|\bq[1-4]\b|\bnext quarter\b|\bimmediately\b|\basap\b)', body_lower)
        if time_match:
            constraints.append(f"Timeframe: {time_match.group(0).strip()}")

        # Equity / Percent constraint
        pct_match = re.search(r'(\b\d+(?:\.\d+)?%|\b\d+\s*percent\b)', body_lower)
        if pct_match:
            constraints.append(f"Allocation/Percentage: {pct_match.group(0).strip()}")

        # Tech stack constraint
        stack_matches = re.findall(r'\b(react|vue|next\.js|fastapi|django|sqlite|postgres|redis|mlx|metal|typescript|python|c\+\+)\b', body_lower)
        if stack_matches:
            constraints.append(f"Tech Stack: {', '.join(sorted(set(stack_matches)))}")

        # 9. Evaluate Ambiguity & Socratic Options
        word_count = len(clean_prompt.split())
        ambiguity_score = 0.0
        clarifications: List[str] = []

        if word_count < 4 and not is_introspection and not is_informational:
            ambiguity_score = 0.85
            clarifications = [
                "Could you specify the target domain (e.g., Strategic Planning, Code Engineering, Financial Cap Table, or Deep Research)?",
                "Do you have existing baseline numbers, repositories, or documents to ground this analysis?",
                "What is your intended deliverable format (e.g., Markdown Dossier, Interactive DAG Plan, Executable Code Diff)?"
            ]
        else:
            ambiguity_score = max(0.0, min(0.4, 0.5 - (len(constraints) * 0.1) - (len(matched_skills) * 0.1)))

        # Clean core objective
        core_objective = clean_prompt
        if is_introspection and not (is_actionable and (matched_skills or matched_tools)):
            core_objective = "Enumerate, explain, and ground all authentic Skills, Tools, and Architectural Capabilities directly from disk manifests."

        is_actionable_dag = (
            (is_actionable or intent_type == IntentType.MULTI_STEP_DAG_EXECUTION)
            and not is_informational
            and not has_negation
            and ambiguity_score < 0.70
        )

        # 10. Extract URLs
        url_pattern = r'https?://[^\s<>"\')]+'
        raw_urls = re.findall(url_pattern, clean_prompt)
        cleaned_urls = [re.sub(r'[\.,;:\)\]]+$', '', u) for u in raw_urls]

        # 11. Classify Cognitive Directive Modality
        is_comprehensive_request = any(w in body_lower for w in [
            "comprehensive", "exhaustive", "publication-grade", "publication grade", "monograph",
            "treatise", "full breakdown", "deep dive", "deep-dive", "in-depth analysis",
            "detailed analysis", "strategic analysis", "academic synthesis", "full analysis",
            "entire paper", "whole paper", "entire document", "all aspects"
        ])

        modality = DirectiveModality.CONCEPTUAL_QA
        if any(w in body_lower for w in ["compare", "comparison", "contrast", "differences between", "similarities between", "versus", " vs ", " vs."]) or len(cleaned_urls) >= 2:
            modality = DirectiveModality.MULTI_DOCUMENT_COMPARISON
        elif any(w in body_lower for w in ["critique", "critical analysis", "audit", "challenge the claims", "flaws in", "limitations of", "stress test", "counter-arguments", "rebuttal", "evaluate the claims", "skeptical"]):
            modality = DirectiveModality.CRITICAL_ANALYSIS
        elif any(w in body_lower for w in ["creative writing", "story", "narrative", "fiction", "allegory", "screenplay", "metaphor", "poem", "poetic", "novel", "worldbuilding", "dialogue between"]):
            modality = DirectiveModality.CREATIVE_WRITING
        elif is_comprehensive_request or any(w in body_lower for w in ["overview", "breakdown", "dossier", "summarize", "summary", "explain this paper", "explain the paper"]):
            modality = DirectiveModality.COMPREHENSIVE_OVERVIEW
        elif any(w in body_lower for w in ["academic article", "research paper", "arxiv", "journal article", "scholarly article", "scholarly paper", "academic publication", "write a paper", "formal treatise"]):
            modality = DirectiveModality.ACADEMIC_ARTICLE
        elif any(w in body_lower for w in ["non-consensus", "contrarian", "counter-intuitive", "unpopular view", "heterodox", "heresy", "blind spots", "antithesis", "challenge the consensus", "dissenting"]):
            modality = DirectiveModality.NON_CONSENSUS_CONTRARIAN
        elif any(w in body_lower for w in ["viral", "x thread", "twitter thread", "linkedin", "substack", "hook", "social post", "thought leadership", "viral post", "viral article", "engaging post"]):
            modality = DirectiveModality.VIRAL_PUBLIC_NARRATIVE
        elif any(w in body_lower for w in ["extract formula", "extract formulas", "extract the formulas", "extract equation", "extract equations", "extract the math", "list all formulas", "only the formulas", "what is the equation", "what is the formula", "formula only"]):
            modality = DirectiveModality.FORMULA_EXTRACTION
        elif any(w in body_lower for w in ["formula", "formulas", "latex", "equation", "equations", "math", "mathematical"]):
            modality = DirectiveModality.FORMULA_EXTRACTION

        genre = detect_document_genre(clean_prompt, raw_prompt=clean_prompt)
        bandwidth = detect_conversational_bandwidth(clean_prompt, modality=modality, genre=genre)

        return ParsedGoalTuple(
            raw_prompt=clean_prompt,
            core_objective=core_objective,
            intent_type=intent_type,
            directive_modality=modality,
            detected_genre=genre,
            detected_bandwidth=bandwidth,
            detected_urls=cleaned_urls,
            domain=domain,
            suggested_agent=suggested_agent,
            constraints=constraints,
            ambiguity_score=round(ambiguity_score, 2),
            is_ambiguous=ambiguity_score > 0.70,
            clarification_options=clarifications,
            required_skills=matched_skills,
            required_tools=matched_tools,
            is_actionable_dag=is_actionable_dag,
            confidence=round(1.0 - (ambiguity_score * 0.5), 2)
        )
