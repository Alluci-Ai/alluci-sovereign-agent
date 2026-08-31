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
        elif word_count < 7 and not constraints and not matched_skills and not is_introspection and not is_research and not is_informational:
            ambiguity_score = 0.60
            clarifications = [
                "Would you like an executive strategic overview or a granular multi-step execution plan?",
                "Are there specific constraints (timeline, budget, tech stack) we should incorporate?"
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

        return ParsedGoalTuple(
            raw_prompt=clean_prompt,
            core_objective=core_objective,
            intent_type=intent_type,
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
