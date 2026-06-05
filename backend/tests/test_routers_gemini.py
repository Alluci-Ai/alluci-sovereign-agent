import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.gemini import router
from backend.security.auth import verify_authenticated
from backend import services

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_gemini_proxy_not_ready():
    services.router = None
    res = client.post("/gemini/proxy", json={"prompt": "hi"})
    assert res.status_code == 503

@pytest.mark.asyncio
async def test_gemini_proxy_success():
    services.router = AsyncMock()
    services.orchestrator = AsyncMock()
    
    services.orchestrator._build_system_context.return_value = "System ctx"
    services.router.get_response.return_value = "Hello"
    
    # We must mock the actual route or use testclient.
    res = client.post("/gemini/proxy", json={"prompt": "hi", "complexity": "LOW", "privacy_level": "PUBLIC", "inference_mode": "LOCAL"})
    assert res.status_code == 200
    assert res.json() == {"result": "Hello"}
    
    services.orchestrator._build_system_context.assert_called_once()
    services.router.get_response.assert_called_once_with(
        prompt="hi",
        system_instruction="System ctx",
        complexity="LOW",
        privacy_level="PUBLIC",
        inference_mode="LOCAL",
        session_id=None
    )

def test_gemini_proxy_exception():
    services.router = AsyncMock()
    services.orchestrator = None
    
    services.router.get_response.side_effect = Exception("Model failed")
    
    res = client.post("/gemini/proxy", json={"prompt": "hi"})
    assert res.status_code == 500
    assert "Model failed" in res.json()["detail"]
