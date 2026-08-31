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


def test_attention_sink_preserves_large_document_payload():
    from backend.inference.mlx_engine import MLXEngine

    # Simulate a 130KB document payload (like Hoffman paper)
    doc_header = "ORIGINAL RESEARCH ARTICLE: Objects of Consciousness by Donald Hoffman\n"
    theoretical_core = "Section 2: Theory of Conscious Agents. Let C = (W, X, G, P, D, A, N)... " * 2000
    doc_footer = "\nReferences: Turing (1937), Nagel, Tononi. Frontiers in Psychology 2014."
    
    full_doc = doc_header + theoretical_core + doc_footer
    assert len(full_doc) > 130000

    prompt = f"<bos><|turn>system\nYou are Alluci.<|turn|>\n<|turn>user\nProvide an overview of this paper:\n{full_doc}<|turn|>\n<|turn>model\n"
    
    # Process through streaming attention sink
    processed = MLXEngine._apply_streaming_attention_sink(prompt, max_chars=250000)
    
    # Ensure the entire document remains intact without slicing
    assert len(processed) == len(prompt)
    assert "Section 2: Theory of Conscious Agents" in processed
    assert "References: Turing" in processed


def test_attention_sink_rolls_multiturn_conversational_history():
    from backend.inference.mlx_engine import MLXEngine

    system_hdr = "<bos><|turn>system\nYou are Alluci.<|turn|>\n"
    turn_1 = "<|turn>user\nHello turn 1<|turn|>\n<|turn>model\nResponse turn 1<|turn|>\n" * 100
    turn_2 = "<|turn>user\nHello turn 2<|turn|>\n<|turn>model\nResponse turn 2<|turn|>\n" * 100
    latest_turn = "<|turn>user\nActive turn with crucial query<|turn|>\n<|turn>model\n"
    
    full_prompt = system_hdr + turn_1 + turn_2 + latest_turn
    
    # Process through streaming attention sink with a tighter budget
    processed = MLXEngine._apply_streaming_attention_sink(full_prompt, max_chars=3000)
    
    assert len(processed) <= 3500
    # Latest turn and system header must be preserved
    assert "Active turn with crucial query" in processed
    assert "<bos><|turn>system" in processed
    assert "consolidated to H-LSM" in processed or "archived to H-LSM" in processed
