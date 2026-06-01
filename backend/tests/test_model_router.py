import json
"""
Unit tests for ModelRouter.
All external API calls are mocked — no real network traffic.
"""
import pytest
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
                    result = await router.get_response("Test prompt")

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
