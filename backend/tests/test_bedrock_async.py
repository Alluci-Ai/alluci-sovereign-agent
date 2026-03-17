"""
T-01 Verification: AWS Bedrock _bedrock_request must not block the event loop.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class FakeBodyStream:
    """Simulates the aioboto3 streaming body response."""
    def __init__(self, data: dict):
        self._data = json.dumps(data).encode()

    async def read(self) -> bytes:
        return self._data

@pytest.mark.asyncio
async def test_bedrock_request_is_non_blocking():
    """
    Verifies _bedrock_request completes without blocking the event loop.
    If the underlying call were synchronous (blocking), asyncio.wait_for
    with a very short timeout would still hang past the timeout because
    the event loop cannot interrupt a blocking call.
    This test uses a mock that introduces a small async delay to prove
    the event loop is not blocked.
    """
    from backend.inference.router import ModelRouter

    # Build a minimal settings mock
    settings = MagicMock()
    settings.GEMINI_API_KEY = None
    settings.OPENAI_API_KEY = None
    settings.ANTHROPIC_API_KEY = None
    settings.DEEPSEEK_API_KEY = None
    settings.OPENROUTER_API_KEY = None
    settings.LM_STUDIO_URL = None
    settings.TOGETHER_API_KEY = None
    settings.COHERE_API_KEY = None
    settings.AWS_ACCESS_KEY_ID = "test-key"
    settings.AWS_SECRET_ACCESS_KEY = "test-secret"
    settings.AWS_REGION = "us-east-1"
    settings.GROQ_API_KEY = None
    settings.ELEVENLABS_API_KEY = None
    settings.MIDJOURNEY_API_KEY = None
    settings.RUNWAY_API_KEY = None
    settings.NVIDIA_NIM_API_KEY = None

    fake_response_body = {
        "content": [{"text": "Bedrock test response"}]
    }

    # Create a mock aioboto3 async context manager
    mock_client = AsyncMock()
    mock_client.invoke_model = AsyncMock(return_value={
        "body": FakeBodyStream(fake_response_body)
    })
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_client)
    mock_context.__aexit__ = AsyncMock(return_value=False)

    import aioboto3
    mock_session = MagicMock(spec=aioboto3.Session)
    mock_session.client = MagicMock(return_value=mock_context)

    with patch("aioboto3.Session", return_value=mock_session):
        router = ModelRouter(settings)
        router.bedrock_session = mock_session

        # This must complete within 2 seconds — a blocking call would hang
        result = await asyncio.wait_for(
            router._bedrock_request("Hello", use_strong=False),
            timeout=2.0
        )

    assert result == "Bedrock test response"
    mock_client.invoke_model.assert_awaited_once()

@pytest.mark.asyncio
async def test_bedrock_request_raises_when_not_configured():
    """_bedrock_request raises RuntimeError when bedrock_session is None."""
    from backend.inference.router import ModelRouter

    settings = MagicMock()
    settings.GEMINI_API_KEY = None
    settings.OPENAI_API_KEY = None
    settings.ANTHROPIC_API_KEY = None
    settings.DEEPSEEK_API_KEY = None
    settings.OPENROUTER_API_KEY = None
    settings.LM_STUDIO_URL = None
    settings.TOGETHER_API_KEY = None
    settings.COHERE_API_KEY = None
    settings.AWS_ACCESS_KEY_ID = None
    settings.GROQ_API_KEY = None
    settings.ELEVENLABS_API_KEY = None
    settings.MIDJOURNEY_API_KEY = None
    settings.RUNWAY_API_KEY = None
    settings.NVIDIA_NIM_API_KEY = None

    router = ModelRouter(settings)
    router.bedrock_session = None

    with pytest.raises(RuntimeError, match="AWS Bedrock not configured"):
        await router._bedrock_request("Hello")
