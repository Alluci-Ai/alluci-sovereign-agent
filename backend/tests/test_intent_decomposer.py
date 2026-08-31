"""
Unit Tests for IntentDecomposer, Manifest Grounding & J-Space Preflight Verifier
================================================================================
"""

import pytest
import numpy as np

from backend.engine.intent_decomposer import IntentDecomposer, IntentType, CapabilityDomain
from backend.engine.codebase_grounding import LocalCodebaseInspector
from backend.topology.j_space_simulator import JSpaceSimulator


class TestIntentDecomposer:
    """Tests deterministic semantic decomposition across universal prompts."""

    def setup_method(self):
        self.decomposer = IntentDecomposer()

    def test_system_introspection_prompt(self):
        prompt = "list and explain all of your Skills and Tools"
        result = self.decomposer.decompose(prompt)
        assert result.intent_type == IntentType.SYSTEM_INTROSPECTION
        assert "Skills, Tools, and Architectural Capabilities" in result.core_objective
        assert not result.is_ambiguous

    def test_financial_modeling_prompt_with_constraints(self):
        prompt = "Model our Series A cap table with a 15% option pool and $5,000,000 investment over next quarter"
        result = self.decomposer.decompose(prompt)
        assert result.intent_type in (IntentType.FINANCIAL_MODELING, IntentType.MULTI_STEP_DAG_EXECUTION)
        assert result.suggested_agent in ("oc", "suf")
        assert any("15%" in c for c in result.constraints)
        assert any("5,000,000" in c or "5" in c for c in result.constraints)
        assert any("quarter" in c.lower() for c in result.constraints)
        assert "ownership_capital_strategy" in result.required_skills
        assert not result.is_ambiguous

    def test_code_engineering_prompt(self):
        prompt = "Refactor the authentication endpoint in backend/routers/auth.py and run pytest assertions"
        result = self.decomposer.decompose(prompt)
        assert result.intent_type == IntentType.CODE_ENGINEERING
        assert result.suggested_agent == "codi"
        assert "codi_opencode_harness" in result.required_skills

    def test_strategic_planning_prompt(self):
        prompt = "Design a Balanced Scorecard and OKR milestone roadmap for Q3"
        result = self.decomposer.decompose(prompt)
        assert result.intent_type == IntentType.STRATEGIC_ADVISORY
        assert result.suggested_agent == "spe"
        assert "strategic_planning_execution" in result.required_skills

    def test_deep_research_prompt(self):
        prompt = "Deep research latest market trends in sovereign AI and paper synthesis"
        result = self.decomposer.decompose(prompt)
        assert result.intent_type == IntentType.DEEP_RESEARCH
        assert result.suggested_agent == "rocco"

    def test_ambiguous_short_prompt(self):
        prompt = "Fix it"
        result = self.decomposer.decompose(prompt)
        assert result.is_ambiguous is True
        assert result.ambiguity_score >= 0.70
        assert len(result.clarification_options) >= 2


class TestManifestGrounding:
    """Tests dynamic discovery and verification of 26 skills and 15 tools from disk truth."""

    def setup_method(self):
        self.inspector = LocalCodebaseInspector()

    def test_installed_skills_discovery(self):
        skills = self.inspector.get_installed_skills_inventory()
        assert len(skills) == 26
        skill_ids = [s["id"] for s in skills]
        assert "codi_01" in skill_ids
        assert "spe_01" in skill_ids
        assert "ocs_01" in skill_ids
        assert "ir_01" in skill_ids
        assert "bmc_01" in skill_ids
        assert "c2c_01" in skill_ids

        # Ensure descriptions are real, not placeholders
        for s in skills:
            assert len(s["description"]) > 10
            assert s["path"].startswith("core_skills")

    def test_installed_tools_discovery(self):
        tools = self.inspector.get_installed_tools_inventory()
        assert len(tools) == 15
        tool_ids = [t["id"] for t in tools]
        assert "autonomous_software_engineering_tool" in tool_ids
        assert "strategic_planning_execution_tool" in tool_ids
        assert "use_of_funds_capital_allocation_tool" in tool_ids
        assert "ownership_capital_strategy_tool" in tool_ids

    def test_full_manifest_grounding_block(self):
        block = self.inspector.get_full_manifest_grounding_block()
        assert "[AUTHENTIC DISK MANIFEST: 26 SPECIALIZED SKILLS & FRAMEWORKS]" in block
        assert "[AUTHENTIC DISK MANIFEST: 15 CAPABILITY TOOLS]" in block
        assert "codi_01" in block
        assert "spe_01" in block


class TestJSpacePreflightVerifier:
    """Tests J-Space preflight simulation and S-CoT nilpotence."""

    def setup_method(self):
        self.simulator = JSpaceSimulator(strict_cot=True)

    def test_valid_preflight_verification(self):
        prompt = "list and explain all of your Skills and Tools"
        candidate = (
            "Here is the authentic disk manifest of my 26 specialized skills and 15 capability tools. "
            "1. Codi OpenCode Harness: Autonomous AST diffing and LSP diagnostics..."
        )
        facts = ["26 specialized skills in core_skills/", "15 capability tools in backend/tools/"]

        result = self.simulator.preflight_simulate_reasoning(
            prompt=prompt,
            candidate_response=candidate,
            grounded_facts=facts,
            is_code_or_tool_dag=False
        )

        assert result.is_valid is True
        assert result.coherence_score > 0.40
        assert result.risk_score <= 0.30
        assert "S-CoT:" in result.feedback

    def test_circular_logic_detection(self):
        prompt = "Explain your identity"
        candidate = "Explain your identity"  # Circular conclusion == premise

        result = self.simulator.preflight_simulate_reasoning(
            prompt=prompt,
            candidate_response=candidate,
            is_code_or_tool_dag=True
        )

        assert result.is_valid is False
        assert result.risk_score >= 0.50
