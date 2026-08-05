import pytest
import json
from unittest.mock import MagicMock

@pytest.mark.asyncio
async def test_lce_payload_routing():
    from backend.inference.router import ModelRouter
    
    mock_settings = MagicMock()
    router = ModelRouter(settings=mock_settings)
    
    original_lce = router._lce_request
    
    async def mock_lce(*args, **kwargs):
        return json.dumps(kwargs.get("tools", []))
        
    router._lce_request = mock_lce
    try:
        tools = [{"type": "function", "function": {"name": "test"}}]
        res_str = await router.get_response("test", tools=tools)
        res = json.loads(res_str)
        assert len(res) == 1
        assert res[0]["function"]["name"] == "test"
    finally:
        router._lce_request = original_lce

@pytest.mark.asyncio
async def test_gemini_agent_dispatch_routing(mocker):
    from backend.inference.router import ModelRouter

    mock_settings = MagicMock()
    mock_settings.SOVEREIGN_MODE = True
    mock_settings.LOCAL_LCE_ENABLED = False
    mock_settings.LM_STUDIO_URL = None
    router = ModelRouter(settings=mock_settings)

    # Set gemini_flash model mock
    mock_gemini = MagicMock()
    router.gemini_flash = mock_gemini

    mock_gemini_request = mocker.patch.object(router, "_gemini_request", return_value="Gemini response")

    # Mock database session query for agent model override
    mock_session = MagicMock()
    mock_agent_rec = MagicMock()
    mock_agent_rec.model = "gemini-2.0-flash"
    mock_session.__enter__.return_value.exec.return_value.first.return_value = mock_agent_rec

    mocker.patch("sqlmodel.Session", return_value=mock_session)

    res = await router.get_response("Hello", agent_id="researcher")
    assert res == "Gemini response"
    mock_gemini_request.assert_called_once()

