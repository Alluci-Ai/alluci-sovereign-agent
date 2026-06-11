import pytest
pytestmark = pytest.mark.unit

"""
[ PPN-032 ] Topological Route Classifier Test Suite.
Validates that prompt analysis correctly routes to optimal cloud providers.
"""

from unittest.mock import MagicMock


@pytest.fixture
def router():
    """Create a ModelRouter with mocked settings for testing."""
    from backend.inference.router import ModelRouter
    
    mock_settings = MagicMock()
    mock_settings.GEMINI_API_KEY = None
    mock_settings.OPENAI_API_KEY = None
    mock_settings.ANTHROPIC_API_KEY = None
    mock_settings.GROQ_API_KEY = None
    mock_settings.DEEPSEEK_API_KEY = None
    mock_settings.OPENROUTER_API_KEY = None
    mock_settings.TOGETHER_API_KEY = None
    mock_settings.COHERE_API_KEY = None
    mock_settings.AWS_ACCESS_KEY_ID = None
    mock_settings.NVIDIA_NIM_API_KEY = None
    mock_settings.ELEVENLABS_API_KEY = None
    mock_settings.MIDJOURNEY_API_KEY = None
    mock_settings.HUGGINGFACE_API_TOKEN = None
    mock_settings.LOCAL_LCE_ENABLED = False
    mock_settings.LM_STUDIO_URL = None
    mock_settings.SOVEREIGN_MODE = False
    mock_settings.MAX_CONCURRENT_TASKS = 5

    return ModelRouter(mock_settings)


class TestTopologicalClassification:

    def test_code_prompt_routes_to_groq(self, router):
        """Code/math prompts should route to Groq (LPU) as primary."""
        result = router.classify_prompt_topology(
            "Write a Python function to sort a binary search tree and optimize the algorithm"
        )
        assert result["domain"] == "MATH_CODE"
        assert result["primary"] == "Groq"
        assert result["fallback"] == "DeepSeek"

    def test_architecture_prompt_routes_to_anthropic(self, router):
        """System design prompts should route to Anthropic (Claude) as primary."""
        result = router.classify_prompt_topology(
            "Design a scalable microservice architecture for a distributed event-driven system with Kubernetes"
        )
        assert result["domain"] == "ARCHITECTURE"
        assert result["primary"] == "Anthropic"
        assert result["fallback"] == "OpenAI"

    def test_research_prompt_routes_to_gemini(self, router):
        """Research/knowledge prompts should route to Gemini as primary."""
        result = router.classify_prompt_topology(
            "Summarize the current state of the art research findings on quantum computing trends"
        )
        assert result["domain"] == "RESEARCH"
        assert result["primary"] == "Gemini"
        assert result["fallback"] == "OpenAI"

    def test_creative_prompt_routes_to_openai(self, router):
        """Creative writing prompts should route to OpenAI (GPT-4) as primary."""
        result = router.classify_prompt_topology(
            "Write a compelling marketing email for a brand pitch presentation"
        )
        assert result["domain"] == "CREATIVE"
        assert result["primary"] == "OpenAI"
        assert result["fallback"] == "Anthropic"

    def test_sensitive_prompt_forces_local(self, router):
        """Sensitive/PII prompts should force LOCAL routing and block cloud."""
        result = router.classify_prompt_topology(
            "Analyze my confidential financial bank statements and credit score"
        )
        assert result["domain"] == "SENSITIVE"
        assert result["primary"] == "LOCAL"
        assert result["fallback"] == "LOCAL"

    def test_generic_prompt_defaults_to_gemini(self, router):
        """Prompts with no strong domain signal should default to Gemini."""
        result = router.classify_prompt_topology(
            "Hello, how are you today?"
        )
        assert result["domain"] == "GENERAL"
        assert result["primary"] == "Gemini"

    def test_reorder_cloud_sequence(self, router):
        """Verify that the cloud sequence is correctly reordered by topological priority."""
        cloud_seq = [
            ("Gemini", lambda p: p),
            ("OpenAI", lambda p: p),
            ("Anthropic", lambda p: p),
            ("Groq", lambda p: p),
            ("DeepSeek", lambda p: p),
        ]

        classification = {
            "domain": "MATH_CODE",
            "primary": "Groq",
            "fallback": "DeepSeek",
            "reason": "test",
            "scores": {},
        }

        reordered = router._reorder_cloud_sequence(cloud_seq, classification)
        names = [e[0] for e in reordered]

        # Groq must be first, DeepSeek second
        assert names[0] == "Groq"
        assert names[1] == "DeepSeek"
        # Remaining providers follow
        assert set(names[2:]) == {"Gemini", "OpenAI", "Anthropic"}

    def test_sensitive_blocks_cloud_sequence(self, router):
        """When SENSITIVE is detected, cloud sequence must be empty."""
        cloud_seq = [
            ("Gemini", lambda p: p),
            ("OpenAI", lambda p: p),
        ]

        classification = {
            "domain": "SENSITIVE",
            "primary": "LOCAL",
            "fallback": "LOCAL",
            "reason": "test",
            "scores": {},
        }

        reordered = router._reorder_cloud_sequence(cloud_seq, classification)
        assert reordered == []
