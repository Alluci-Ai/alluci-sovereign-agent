import pytest
pytestmark = pytest.mark.unit

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

def test_gemini_proxy_stream_not_ready():
    services.router = None
    res = client.post("/gemini/proxy/stream", json={"prompt": "hi"})
    assert res.status_code == 503

@pytest.mark.asyncio
async def test_gemini_proxy_stream_success():
    services.router = MagicMock()
    services.orchestrator = AsyncMock()
    
    services.orchestrator._build_system_context.return_value = "System ctx"
    
    async def mock_generator(*args, **kwargs):
        yield "Chunk 1"
        yield "Chunk 2"
        
    services.router.get_response_stream = mock_generator
    
    res = client.post("/gemini/proxy/stream", json={"prompt": "hi", "complexity": "LOW", "privacy_level": "PUBLIC", "inference_mode": "LOCAL"})
    assert res.status_code == 200
    assert res.headers["content-type"] == "text/event-stream; charset=utf-8"
    
    # Read the streamed chunks
    content = res.content.decode("utf-8")
    assert 'data: {"text": "Chunk 1"}\n\ndata: {"text": "Chunk 2"}\n\n' in content
    
    services.orchestrator._build_system_context.assert_called_once()

def test_gemini_proxy_stream_exception():
    services.router = MagicMock()
    services.orchestrator = None
    
    def fail_stream(*args, **kwargs):
        raise Exception("Stream failed")
        
    services.router.get_response_stream = fail_stream
    
    res = client.post("/gemini/proxy/stream", json={"prompt": "hi"})
    assert res.status_code == 200
    assert 'data: {"text": "[ ERROR ]: Stream failed"}' in res.content.decode("utf-8")

@pytest.mark.asyncio
async def test_gemini_proxy_local_file_retrieval_readme():
    services.router = AsyncMock()
    services.orchestrator = AsyncMock()
    services.orchestrator.ws_gateway = AsyncMock()
    
    res = client.post("/gemini/proxy", json={"prompt": "can you show me the Alluci Sovereign Agent README.md file"})
    assert res.status_code == 200
    data = res.json()
    assert "README.md" in data["result"]
    assert "Alluci-Sovereign-Agent" in data["result"]
    # Verify LLM was NOT called because disk truth was returned directly
    services.router.get_response.assert_not_called()

@pytest.mark.asyncio
async def test_gemini_proxy_local_file_not_found():
    services.router = AsyncMock()
    services.orchestrator = AsyncMock()
    
    res = client.post("/gemini/proxy", json={"prompt": "show me non_existent_script_98234.py"})
    assert res.status_code == 200
    data = res.json()
    assert "File `non_existent_script_98234.py` was not found on the local filesystem" in data["result"]
    services.router.get_response.assert_not_called()

@pytest.mark.asyncio
async def test_gemini_proxy_web_search_grounding():
    services.router = AsyncMock()
    services.orchestrator = AsyncMock()
    services.orchestrator._build_system_context.return_value = "System ctx"
    services.router.get_response.return_value = "Web Search Answer"

    with patch("backend.adapters.web_search.WebSearchAdapter.execute", new_callable=AsyncMock) as mock_search:
        mock_search.return_value = {
            "status": "success",
            "results": [{"title": "Verus Protocol", "link": "https://verus.io", "snippet": "Verus multi-chain protocol"}]
        }
        res = client.post("/gemini/proxy", json={"prompt": "search the web for Verus Protocol"})
        assert res.status_code == 200
        assert res.json() == {"result": "Web Search Answer"}
        mock_search.assert_called_once_with("Verus Protocol")



