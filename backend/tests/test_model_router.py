import pytest
pytestmark = pytest.mark.unit

import json
"""
Unit tests for ModelRouter.
All external API calls are mocked — no real network traffic.
"""
from unittest.mock import AsyncMock, MagicMock, patch
import sys

def make_mock_settings(**overrides):
   settings = MagicMock()
   settings.SOVEREIGN_MODE = False
   settings.GEMINI_API_KEY = None
   settings.OPENAI_API_KEY = None
   settings.ANTHROPIC_API_KEY = None
   settings.GROQ_API_KEY = None
   settings.DEEPSEEK_API_KEY = None
   settings.OPENROUTER_API_KEY = None
   settings.TOGETHER_API_KEY = None
   settings.COHERE_API_KEY = None
   settings.AWS_ACCESS_KEY_ID = None
   settings.HUGGINGFACE_API_TOKEN = None
   settings.LM_STUDIO_URL = None
   settings.ELEVENLABS_API_KEY = None
   settings.MIDJOURNEY_API_KEY = None
   settings.RUNWAY_API_KEY = None
   settings.LOCAL_LCE_ENABLED = False
   for k, v in overrides.items():
       setattr(settings, k, v)
   return settings

class TestModelRouterInit:
    def test_sovereign_mode_disables_cloud(self):
        settings = make_mock_settings(SOVEREIGN_MODE=True)
        with patch("backend.inference.router.GEMINI_AVAILABLE", True), \
             patch("backend.inference.router.OPENAI_AVAILABLE", True), \
             patch("backend.inference.router.ANTHROPIC_AVAILABLE", True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)
        assert router.gemini_flash is None
        assert router.openai_client is None
        assert router.anthropic_client is None
        assert router.groq_api_key is None

    def test_no_keys_leaves_all_cloud_disabled(self):
        settings = make_mock_settings()
        with patch("backend.inference.router.GEMINI_AVAILABLE", True), \
             patch("backend.inference.router.OPENAI_AVAILABLE", True), \
             patch("backend.inference.router.ANTHROPIC_AVAILABLE", True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)
        assert router.openai_client is None
        assert router.anthropic_client is None

class TestModelRouterLocalRoute:
    @pytest.mark.asyncio
    async def test_routes_to_lm_studio_when_configured(self):
        settings = make_mock_settings(LM_STUDIO_URL="http://localhost:1234")
        with patch("backend.inference.router.OPENAI_AVAILABLE", True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)

        with patch.object(router, "_lm_studio_request", new_callable=AsyncMock) as mock_call:
            mock_call.return_value = "LM Studio response"
            result = await router.get_response("Test prompt", complexity="MEDIUM")

        assert result == "LM Studio response"

    @pytest.mark.asyncio
    async def test_failover_to_gemini_when_lm_studio_fails(self):
        settings = make_mock_settings(GEMINI_API_KEY="test-key", LM_STUDIO_URL="http://localhost:1234")
        with patch("backend.inference.router.OPENAI_AVAILABLE", True), \
             patch("backend.inference.router.GEMINI_AVAILABLE", True), \
             patch("backend.inference.router.genai", MagicMock(), create=True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)

            with patch.object(router, "_lm_studio_request", new_callable=AsyncMock) as mock_lm:
                mock_lm.side_effect = Exception("LM Studio down")
                with patch.object(router, "_gemini_request", new_callable=AsyncMock) as mock_gemini:
                    mock_gemini.return_value = "Gemini response"
                    result = await router.get_response("Test prompt", complexity="HIGH")

        assert result == "Gemini response"

class TestStructuredPlanGeneration:
    @pytest.mark.asyncio
    async def test_get_structured_plan_returns_steps(self):
        settings = make_mock_settings()
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)

        valid_plan = json.dumps({
            "steps": [
                {"id": "s1", "tool": "web_search", "description": "Search", "dependencies": []},
                {"id": "s2", "tool": "summarize", "description": "Summarize", "dependencies": ["s1"]}
            ]
        })

        with patch.object(router, "get_response", new_callable=AsyncMock) as mock_resp:
            mock_resp.return_value = valid_plan
            plan = await router.get_structured_plan("Find info about Python")

        assert "steps" in plan
        assert len(plan["steps"]) == 2

    @pytest.mark.asyncio
    async def test_malformed_plan_response_returns_empty_steps(self):
        settings = make_mock_settings()
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)

        with patch.object(router, "get_response", new_callable=AsyncMock) as mock_resp:
            mock_resp.return_value = "I cannot create a plan right now."
            plan = await router.get_structured_plan("Objective")

        assert plan.get("steps", []) == []


class TestFailoversAndSpecificRequests:
    @pytest.mark.asyncio
    async def test_openai_request_strong(self):
        settings = make_mock_settings(OPENAI_API_KEY="test")
        with patch("backend.inference.router.OPENAI_AVAILABLE", True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)
            router.openai_client = AsyncMock()
            mock_choice = MagicMock()
            mock_choice.message.content = "openai strong"
            router.openai_client.chat.completions.create.return_value = MagicMock(choices=[mock_choice], usage=MagicMock())
            
            res = await router._openai_request("hello", use_strong=True)
            assert res == "openai strong"

    @pytest.mark.asyncio
    async def test_gemini_request(self):
        settings = make_mock_settings(GEMINI_API_KEY="test")
        with patch("backend.inference.router.GEMINI_AVAILABLE", True), \
             patch("backend.inference.router.genai", MagicMock(), create=True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)
            
            mock_flash = AsyncMock()
            mock_flash.generate_content_async.return_value = MagicMock(text="gemini response")
            router.gemini_flash = mock_flash
            
            res = await router._gemini_request("hello")
            assert res == "gemini response"

    @pytest.mark.asyncio
    async def test_anthropic_request(self):
        settings = make_mock_settings(ANTHROPIC_API_KEY="test")
        with patch("backend.inference.router.ANTHROPIC_AVAILABLE", True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)
            router.anthropic_client = AsyncMock()
            
            mock_content = MagicMock()
            mock_content.text = "anthropic response"
            router.anthropic_client.messages.create.return_value = MagicMock(content=[mock_content])
            
            res = await router._anthropic_request("hello")
            assert res == "anthropic response"

    @pytest.mark.asyncio
    async def test_kimi_request(self):
        settings = make_mock_settings(NVIDIA_NIM_API_KEY="test")
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        
        with patch("backend.inference.router.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.json = MagicMock(return_value={"choices": [{"message": {"content": "kimi"}}]})
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            res = await router._kimi_request("hello")
            assert res == "kimi"
            
    @pytest.mark.asyncio
    async def test_cohere_request(self):
        settings = make_mock_settings(COHERE_API_KEY="test")
        with patch("backend.inference.router.COHERE_AVAILABLE", True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)
            router.cohere_client = AsyncMock()
            router.cohere_client.chat.return_value = MagicMock(text="cohere response")
            
            res = await router._cohere_request("hello")
            assert res == "cohere response"

    @pytest.mark.asyncio
    async def test_bedrock_request(self):
        settings = make_mock_settings(AWS_ACCESS_KEY_ID="test")
        with patch("backend.inference.router.BOTO3_AVAILABLE", True), \
             patch("backend.inference.router.aioboto3", MagicMock(), create=True):
            from backend.inference.router import ModelRouter
            router = ModelRouter(settings)
            
            router.bedrock_session = MagicMock()
            mock_client = AsyncMock()
            
            router.bedrock_session.client.return_value = mock_client
            
            mock_invoke = AsyncMock()
            import asyncio
            async def mock_read():
                return b'{"content": [{"text": "bedrock"}]}'
            mock_body = MagicMock()
            mock_body.read = mock_read
            mock_invoke.return_value = {"body": mock_body}
            mock_client.__aenter__.return_value.invoke_model = mock_invoke
            
            res = await router._bedrock_request("hello")
            assert res == "bedrock"

    @pytest.mark.asyncio
    async def test_generic_openai_request(self):
        settings = make_mock_settings()
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        
        client = AsyncMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "generic openai"
        client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])
        
        res = await router._generic_openai_request("hello", client, "DeepSeek")
        assert res == "generic openai"

    @pytest.mark.asyncio
    async def test_refine_plan(self):
        settings = make_mock_settings()
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        
        with patch.object(router, "get_structured_plan", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"steps": []}
            res = await router.refine_plan("obj", [{"id": "s1"}], "res", "bad", ["s1"])
            assert "steps" in res

    @pytest.mark.asyncio
    async def test_fast_tactical_response(self):
        settings = make_mock_settings(GROQ_API_KEY="test")
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        
        with patch("backend.inference.router.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.json = MagicMock(return_value={"choices": [{"message": {"content": "groq tactical"}}]})
            mock_post.return_value.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            res = await router.get_fast_tactical_response("hello")
            assert res == "groq tactical"

    @pytest.mark.asyncio
    async def test_fast_tactical_response_fallback(self):
        settings = make_mock_settings(GROQ_API_KEY="test")
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        
        with patch("backend.inference.router.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=Exception("API limit"))
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            with patch.object(router, "_gemini_request", new_callable=AsyncMock) as mock_gem:
                mock_gem.return_value = "gemini tactical"
                res = await router.get_fast_tactical_response("hello fallback")
                assert res == "gemini tactical"

class TestModelRouterGenerators:
    @pytest.mark.asyncio
    async def test_generate_speech(self):
        settings = make_mock_settings(ELEVENLABS_API_KEY="test")
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        
        with patch("backend.inference.router.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.content = b"audio"
            mock_post.return_value.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            res = await router.generate_speech("hello")
            assert res == b"audio"

    @pytest.mark.asyncio
    async def test_generate_image(self):
        settings = make_mock_settings(MIDJOURNEY_API_KEY="test")
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        
        with patch("backend.inference.router.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.json = MagicMock(return_value={"url": "http://img"})
            mock_post.return_value.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            res = await router.generate_image("cat")
            assert res == "http://img"

    @pytest.mark.asyncio
    async def test_generate_video(self):
        settings = make_mock_settings(RUNWAY_API_KEY="test")
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        
        with patch("backend.inference.router.httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock()
            mock_post.return_value.json = MagicMock(return_value={"id": "vid123"})
            mock_post.return_value.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            res = await router.generate_video("cat")
            assert res == "vid123"

    @pytest.mark.asyncio
    async def test_check_health(self):
        settings = make_mock_settings()
        from backend.inference.router import ModelRouter
        router = ModelRouter(settings)
        router.lm_studio_client = MagicMock()
        
        with patch.object(router, "_lm_studio_request", new_callable=AsyncMock) as mock_lm:
            mock_lm.return_value = "OK"
            res = await router.check_health()
            assert "lm_studio" in res
            assert res["lm_studio"]["status"] == "HEALTHY"
