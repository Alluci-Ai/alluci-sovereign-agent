import pytest
pytestmark = pytest.mark.unit

import pytest
from backend.engine.intent_decomposer import IntentDecomposer, IntentType
from backend.engine.grounding_providers import ArchitectureGroundingProvider, ModularGroundingOrchestrator


def test_intent_decomposer_distinguishes_external_paper_from_alluci_introspection():
    decomposer = IntentDecomposer()

    # 1. External paper query
    prompt_hoffman = "Provide a detailed and comprehensive overview and explanation of this Hoffman_Objects of Consciousness paper."
    parsed_hoffman = decomposer.decompose(prompt_hoffman)
    assert parsed_hoffman.intent_type != IntentType.SYSTEM_INTROSPECTION
    assert parsed_hoffman.intent_type in [IntentType.INFORMATIONAL_QA, IntentType.DEEP_RESEARCH, IntentType.GENERAL_CONVERSATIONAL]

    # 2. CIMC paper query
    prompt_cimc = "Provide a detailed and comprehensive overview and explanation of this CIMC White-paper."
    parsed_cimc = decomposer.decompose(prompt_cimc)
    assert parsed_cimc.intent_type != IntentType.SYSTEM_INTROSPECTION

    # 3. Explicit Alluci system introspection query
    prompt_alluci = "Explain your architecture, the 6 functional domains, and how Alluci is built."
    parsed_alluci = decomposer.decompose(prompt_alluci)
    assert parsed_alluci.intent_type == IntentType.SYSTEM_INTROSPECTION


@pytest.mark.asyncio
async def test_architecture_grounding_provider_precedence():
    decomposer = IntentDecomposer()
    arch_provider = ArchitectureGroundingProvider()

    # External paper prompt
    doc_prompt = "Provide a detailed and comprehensive overview and explanation of this Hoffman_Objects of Consciousness paper."
    parsed_doc = decomposer.decompose(doc_prompt)
    
    can_handle_doc = await arch_provider.can_handle(doc_prompt, parsed_doc)
    assert can_handle_doc is False

    # Alluci architecture prompt
    sys_prompt = "Explain the Alluci Sovereign Agent architecture and 6 functional domains."
    parsed_sys = decomposer.decompose(sys_prompt)
    
    can_handle_sys = await arch_provider.can_handle(sys_prompt, parsed_sys)
    assert can_handle_sys is True


@pytest.mark.asyncio
async def test_modular_orchestrator_avoids_blueprint_hijack_on_document():
    decomposer = IntentDecomposer()
    orch = ModularGroundingOrchestrator()

    doc_prompt = "Provide a detailed and comprehensive overview and explanation of this Hoffman_Objects of Consciousness paper."
    parsed_doc = decomposer.decompose(doc_prompt)

    grounding, directive = await orch.resolve_grounding(doc_prompt, parsed_doc)
    
    # Grounding must NOT contain the Alluci Sovereign Agent architecture blueprint
    if grounding:
        assert "Alluci Sovereign Agent Architecture Blueprint" not in grounding
        assert "AUTHENTIC SYSTEM ARCHITECTURE" not in grounding
