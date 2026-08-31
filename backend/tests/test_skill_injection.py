import pytest
from backend.skill_manager import SkillManager
from unittest.mock import MagicMock

def test_resolve_skill_context_hcd():
    vault = MagicMock()
    sm = SkillManager(vault=vault)
    
    # Query with skill ID
    ctx1 = sm.resolve_skill_context_for_prompt("tell me about hcd_01")
    assert ctx1 is not None
    assert "Human Centered Design" in ctx1
    assert "Empathy" in ctx1
    assert "EthnographicResearch" in ctx1
    assert "Empathize -> Understand User Needs" in ctx1
    
    # Query with full skill name
    ctx2 = sm.resolve_skill_context_for_prompt("What are the mindsets for Human Centered Design?")
    assert ctx2 is not None
    assert "hcd_01" in ctx2

def test_resolve_multi_skills():
    vault = MagicMock()
    sm = SkillManager(vault=vault)
    
    ctx = sm.resolve_skill_context_for_prompt("Can we combine Human Centered Design with other tools?")
    assert ctx is not None
    assert "Human Centered Design" in ctx

def test_detect_context_switch():
    vault = MagicMock()
    sm = SkillManager(vault=vault)
    
    assert sm.detect_context_switch("let's switch to python debugging", ["hcd_01"]) is True
    assert sm.detect_context_switch("how do we implement the empathy phase?", ["hcd_01"]) is False

def test_natural_conversational_deduction():
    vault = MagicMock()
    sm = SkillManager(vault=vault)
    
    # Trigger hcd_01 via conversational keywords (empathy mapping / user research) without hcd_01 ID or exact title
    ctx1 = sm.resolve_skill_context_for_prompt("How can we perform empathy mapping and user research for our product?")
    assert ctx1 is not None
    assert "hcd_01" in ctx1

    # Trigger hcd_01 via methodology term (JourneyMapping)
    ctx2 = sm.resolve_skill_context_for_prompt("Let's do journey mapping for the customer flow")
    assert ctx2 is not None
    assert "hcd_01" in ctx2

def test_negative_directive_suppresses_skill_injection():
    vault = MagicMock()
    sm = SkillManager(vault=vault)
    ctx = sm.resolve_skill_context_for_prompt("just explain in detail the whitepaper. do not apply any frameworks to it.")
    assert ctx is None

def test_document_envelope_isolation_prevents_spurious_skill_matching():
    vault = MagicMock()
    sm = SkillManager(vault=vault)
    # The attached file contains words like "strategic planning" and "empathy mapping", but the user directive is a pure summary request
    prompt = (
        "Please summarize this document.\n\n"
        "--- [ATTACHED FILE: doc.pdf] ---\n"
        "This document discusses strategic planning, okrs, empathy mapping, and organizational design frameworks.\n"
        "--- [END ATTACHED FILE] ---"
    )
    ctx = sm.resolve_skill_context_for_prompt(prompt)
    assert ctx is None


def test_router_prepare_system_instruction():
    from backend.inference.router import ModelRouter
    from unittest.mock import patch
    
    router = ModelRouter(settings=MagicMock(), vault=MagicMock())
    
    mock_sm = MagicMock()
    mock_sm.resolve_skill_context_for_prompt.return_value = "<COGNITIVE_SKILL_CONTEXT id=\"hcd_01\">\nTest Skill Context\n</COGNITIVE_SKILL_CONTEXT>"
    
    with patch("backend.services.skill_manager", mock_sm):
        sys_inst = router._prepare_system_instruction("give me a comprehensive overview of your Human Centered Design skill.")
        assert "<COGNITIVE_SKILL_CONTEXT id=\"hcd_01\">" in sys_inst
        assert "You are Alluci" in sys_inst
