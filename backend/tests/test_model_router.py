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
