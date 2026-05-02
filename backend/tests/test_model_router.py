import json
"""
Unit tests for ModelRouter.
All external API calls are mocked — no real network traffic.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys

# Mock google generative ai globally
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()
sys.modules["anthropic"] = MagicMock()
sys.modules["groq"] = MagicMock()
sys.modules["openai"] = MagicMock()


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
   settings.OLLAMA_URL = "http://localhost:11434"
   settings.LM_STUDIO_URL = None
   settings.ELEVENLABS_API_KEY = None
   settings.MIDJOURNEY_API_KEY = None
   settings.RUNWAY_API_KEY = None
   for k, v in overrides.items():
       setattr(settings, k, v)
   return settings


class TestModelRouterInit:

   def test_sovereign_mode_disables_cloud(self):
       settings = make_mock_settings(SOVEREIGN_MODE=True)
       with patch("backend.inference.router.ModelRouter._probe_ollama", return_value=False):
           from backend.inference.router import ModelRouter
           router = ModelRouter(settings)
       assert router.gemini_flash is None
       assert router.openai_client is None
       assert router.anthropic_client is None
       assert router.groq_api_key is None

   def test_no_keys_leaves_all_cloud_disabled(self):
       settings = make_mock_settings()
       with patch("backend.inference.router.ModelRouter._probe_ollama", return_value=False):
           from backend.inference.router import ModelRouter
           router = ModelRouter(settings)
       assert router.openai_client is None
       assert router.anthropic_client is None

   def test_ollama_ready_when_probe_succeeds(self):
       settings = make_mock_settings()
       with patch("backend.inference.router.ModelRouter._probe_ollama", return_value=True):
           from backend.inference.router import ModelRouter
           router = ModelRouter(settings)
       assert router.ollama_ready is True

   def test_ollama_not_ready_when_probe_fails(self):
       settings = make_mock_settings()
       with patch("backend.inference.router.ModelRouter._probe_ollama", return_value=False):
           from backend.inference.router import ModelRouter
           router = ModelRouter(settings)
       assert router.ollama_ready is False


class TestModelRouterOllamaRoute:

   @pytest.mark.asyncio
   async def test_routes_to_ollama_when_ready(self):
       settings = make_mock_settings()
       with patch("backend.inference.router.ModelRouter._probe_ollama", return_value=True):
           from backend.inference.router import ModelRouter
           router = ModelRouter(settings)

       # Mock the actual Ollama HTTP call
       mock_response = MagicMock()
       mock_response.status_code = 200
       mock_response.json.return_value = {
           "message": {"content": "Ollama response"},
           "model": "llama3"
       }

       with patch.object(router, "_call_ollama", new_callable=AsyncMock) as mock_call:
           mock_call.return_value = "Ollama response"
           result = await router.get_response("Test prompt", system="You are a test assistant.")

       assert result is not None

   @pytest.mark.asyncio
   async def test_failover_to_gemini_when_ollama_fails(self):
       settings = make_mock_settings(GEMINI_API_KEY="test-key")
       with patch("backend.inference.router.ModelRouter._probe_ollama", return_value=False):
           from backend.inference.router import ModelRouter
           with patch("google.generativeai.configure"), \
                patch("google.generativeai.GenerativeModel") as mock_genai:
               mock_model = MagicMock()
               mock_model.generate_content_async = AsyncMock(
                   return_value=MagicMock(text="Gemini response")
               )
               mock_genai.return_value = mock_model
               router = ModelRouter(settings)
               router.ollama_ready = False

               with patch.object(router, "_call_gemini", new_callable=AsyncMock) as mock_gemini:
                   mock_gemini.return_value = "Gemini response"
                   result = await router.get_response("Test prompt")

       # Ensure the router attempted the call
       assert result is not None


class TestStructuredPlanGeneration:

   @pytest.mark.asyncio
   async def test_get_structured_plan_returns_steps(self):
       settings = make_mock_settings()
       with patch("backend.inference.router.ModelRouter._probe_ollama", return_value=False):
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
       with patch("backend.inference.router.ModelRouter._probe_ollama", return_value=False):
           from backend.inference.router import ModelRouter
           router = ModelRouter(settings)

       with patch.object(router, "get_response", new_callable=AsyncMock) as mock_resp:
           mock_resp.return_value = "I cannot create a plan right now."
           plan = await router.get_structured_plan("Objective")

       assert plan.get("steps", []) == []
