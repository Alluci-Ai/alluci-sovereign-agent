import pytest
from unittest.mock import MagicMock, AsyncMock, ANY
from backend.inference.router import ModelRouter

from backend.config import Settings

@pytest.mark.asyncio
async def test_psi_routing_logic():
    settings = Settings(  # type: ignore
        GEMINI_API_KEY="test",
        LOCAL_LLM_ENABLED=False,
        LOCAL_LCE_ENABLED=False,
        LM_STUDIO_URL="",
        OLLAMA_BASE_URL="",
        AWS_ACCESS_KEY_ID="",
        AWS_SECRET_ACCESS_KEY="",
        AWS_REGION="us-east-1"
    )
    router = ModelRouter(settings)
    router.lce_enabled = False
    router.lm_studio_client = None
    
    # Mock request methods
    router._gemini_request = AsyncMock(return_value="gemini response")  # type: ignore
    from backend.inference.router import GEMINI_AVAILABLE
    print("GEMINI_AVAILABLE:", GEMINI_AVAILABLE)
    print("router.gemini_flash:", router.gemini_flash)
    
    # Test 1: Low psi, MEDIUM complexity -> Gemini Flash (use_pro=False)
    res = await router.get_response("test prompt", complexity="MEDIUM", psi=0.5)
    print("RETURN VALUE:", res)
    router._gemini_request.assert_called_with("test prompt", use_pro=False, json_mode=False, system_instruction=ANY, session_id=ANY)
    
    # Test 2: High psi (> 0.7), MEDIUM complexity -> KCM routes to tactical/light.
    # With no groq_api_key, tactical route falls through to Gemini Flash (use_pro=False)
    router._gemini_request.reset_mock()
    await router.get_response("test prompt", complexity="MEDIUM", psi=0.9)
    # Since use_tactical=True but no Groq, falls through. use_strong stays False because
    # use_tactical=True prevents the override on line `if not use_tactical:`.
    router._gemini_request.assert_called_with("test prompt", use_pro=False, json_mode=False, system_instruction=ANY, session_id=ANY)

    # Test 3: HIGH complexity -> Gemini Pro (use_pro=True) regardless of psi
    router._gemini_request.reset_mock()
    await router.get_response("test prompt", complexity="HIGH", psi=0.1)
    router._gemini_request.assert_called_with("test prompt", use_pro=True, json_mode=False, system_instruction=ANY, session_id=ANY)

    # Test 4: HIGH complexity + high psi -> KCM tactical override takes precedence
    # If psi > 0.7, tactical routing overrides even HIGH complexity
    router._gemini_request.reset_mock()
    await router.get_response("test prompt", complexity="HIGH", psi=0.8)
    # use_tactical=True, use_strong set to False, reaches Gemini Flash
    router._gemini_request.assert_called_with("test prompt", use_pro=False, json_mode=False, system_instruction=ANY, session_id=ANY)
