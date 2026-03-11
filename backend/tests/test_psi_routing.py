import pytest
from unittest.mock import MagicMock, AsyncMock
from backend.inference.router import ModelRouter

from backend.config import Settings

@pytest.mark.asyncio
async def test_psi_routing_logic():
    settings = Settings(
        GEMINI_API_KEY="test",
        LOCAL_LLM_ENABLED=False,
        LM_STUDIO_URL="",
        OLLAMA_BASE_URL="",
        AWS_ACCESS_KEY_ID="",
        AWS_SECRET_ACCESS_KEY="",
        AWS_REGION="us-east-1"
    )
    router = ModelRouter(settings)
    
    # Mock request methods
    router._gemini_request = AsyncMock(return_value="gemini response")
    
    # Test 1: Low psi, MEDIUM complexity -> Gemini Flash (use_pro=False)
    await router.get_response("test prompt", complexity="MEDIUM", psi=0.5)
    router._gemini_request.assert_called_with("test prompt", use_pro=False, json_mode=False)
    
    # Test 2: High psi (> 0.8), MEDIUM complexity -> Gemini Pro (use_pro=True)
    router._gemini_request.reset_mock()
    await router.get_response("test prompt", complexity="MEDIUM", psi=0.9)
    router._gemini_request.assert_called_with("test prompt", use_pro=True, json_mode=False)

    # Test 3: HIGH complexity -> Gemini Pro (use_pro=True) regardless of psi
    router._gemini_request.reset_mock()
    await router.get_response("test prompt", complexity="HIGH", psi=0.1)
    router._gemini_request.assert_called_with("test prompt", use_pro=True, json_mode=False)
