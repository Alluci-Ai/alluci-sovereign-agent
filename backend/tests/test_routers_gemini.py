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

@pytest.mark.asyncio
async def test_gemini_proxy_explain_file_content_injection():
    services.router = AsyncMock()
    services.orchestrator = AsyncMock()
    services.orchestrator._build_system_context.return_value = "System ctx"
    services.router.get_response.return_value = "Explanation of README.md and sovereign pillars"

    res = client.post("/gemini/proxy", json={"prompt": "now explain what this README.md file says and what makes you different from other agents"})
    assert res.status_code == 200
    assert res.json() == {"result": "Explanation of README.md and sovereign pillars"}

    # Verify that get_response was called with the actual README.md disk content injected into the prompt
    services.router.get_response.assert_called_once()
    called_prompt = services.router.get_response.call_args[1]["prompt"]
    assert "[VERIFIED DISK CONTENT: `README.md`" in called_prompt
    assert "Alluci-Sovereign-Agent" in called_prompt


@pytest.mark.asyncio
async def test_gemini_proxy_introspective_subsystem_grounding_dpk():
    services.router = AsyncMock()
    services.orchestrator = AsyncMock()
    services.orchestrator._build_system_context.return_value = "System ctx"
    services.router.get_response.return_value = "DPK explanation"

    res = client.post("/gemini/proxy", json={"prompt": "Can you explain what your DPK does based on your codebase?"})
    assert res.status_code == 200
    assert res.json() == {"result": "DPK explanation"}

    services.router.get_response.assert_called_once()
    called_prompt = services.router.get_response.call_args[1]["prompt"]
    assert "[INTROSPECTIVE SUBSYSTEM GROUNDING: `backend/security/dpk.py`]:" in called_prompt
    assert "DiscreteProjectionKernel" in called_prompt or "PolytopeState" in called_prompt


@pytest.mark.asyncio
async def test_gemini_proxy_no_accidental_substring_subsystem_grounding():
    services.router = AsyncMock()
    services.orchestrator = AsyncMock()
    services.orchestrator._build_system_context.return_value = "System ctx"
    services.router.get_response.return_value = "Special explanation without spe grounding"

    # "special" contains "spe", "surface" contains "ace"
    res = client.post("/gemini/proxy", json={"prompt": "Can you look at your README.md file and explain what makes you special on the surface?"})
    assert res.status_code == 200

    services.router.get_response.assert_called_once()
    called_prompt = services.router.get_response.call_args[1]["prompt"]
    # Verify that "spe" and "ace" subsystem code was NOT accidentally injected as substring matches
    assert "strategic_planning_execution_tool.py" not in called_prompt
    assert "[VERIFIED DISK CONTENT: `README.md`" in called_prompt
    assert "DOCUMENT OUTLINE & TABLE OF SECTIONS:" in called_prompt


@pytest.mark.asyncio
async def test_gemini_proxy_deep_research_web_search():
    services.router = AsyncMock()
    services.orchestrator = AsyncMock()
    services.orchestrator._build_system_context.return_value = "System ctx"
    services.router.get_response.return_value = "Deep research synthesized response"

    with patch("backend.adapters.web_search.WebSearchAdapter.expand_and_harvest", new_callable=AsyncMock) as mock_harvest:
        mock_harvest.return_value = {
            "status": "success",
            "provider": "multi_query_ddg",
            "results": [{"title": "Apple MLX Breakthroughs", "link": "https://github.com/ml-explore/mlx", "snippet": "Apple silicon machine learning framework"}]
        }
        res = client.post("/gemini/proxy", json={"prompt": "Do deep research on Apple MLX in 2026"})
        assert res.status_code == 200
        assert res.json() == {"result": "Deep research synthesized response"}
        mock_harvest.assert_called_once_with("Apple MLX in 2026")


def test_mlx_streaming_attention_sink_truncation():
    from backend.inference.mlx_engine import MLXEngine
    engine = MLXEngine()
    
    system_rules = "SYSTEM RULES: SOVEREIGN IDENTITY DIRECTIVE 1 TO 10. " * 50
    user_dialogue = "USER MESSAGE: WHAT IS DPK ARCHITECTURE? " * 1000
    
    full_prompt = f"<bos><|turn>system\n{system_rules}<|turn|>\n<|turn>user\n{user_dialogue}<|turn|>\n<|turn>model\n"
    assert len(full_prompt) > 25000
    
    sinked = engine._apply_streaming_attention_sink(full_prompt, max_chars=16000)
    assert len(sinked) <= 16500
    assert "SYSTEM RULES: SOVEREIGN IDENTITY" in sinked
    assert "intermediate conversational turns archived to H-LSM episodic memory" in sinked
    assert "WHAT IS DPK ARCHITECTURE?" in sinked


def test_mlx_speculative_decoding_configuration():
    from backend.inference.mlx_engine import MLXEngine
    engine = MLXEngine()
    assert hasattr(engine, "load_draft_model_sync")
    assert hasattr(engine, "draft_engine")
    assert hasattr(engine, "draft_model_id")





