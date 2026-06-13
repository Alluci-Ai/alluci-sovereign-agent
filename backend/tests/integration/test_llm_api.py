import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
import backend.services

def test_full_stack_gemini_proxy_local(client: TestClient, auth_headers: dict):
    """
    Tests the full API stack for a local inference request.
    Routes through FastAPI middlewares, hits the gemini_proxy endpoint, invokes ModelRouter,
    and patches the final request to LM Studio.
    """
    payload = {
        "prompt": "Hello from full stack local",
        "complexity": "MEDIUM",
        "privacy_level": "PUBLIC",
        "inference_mode": "LOCAL"
    }

    mock_lce = AsyncMock(return_value="I am the local model response.")
    with patch("backend.inference.router.ModelRouter._lce_request", mock_lce):
        response = client.post("/api/v1/gemini/proxy", json=payload, headers=auth_headers)
        
        assert response.status_code == 200, f"Error: {response.text}"
        data = response.json()
        assert "result" in data
        assert data["result"] == "I am the local model response."
        mock_lce.assert_called_once()

def test_full_stack_gemini_proxy_cloud(client: TestClient, auth_headers: dict):
    """
    Tests the full API stack failing over to a Cloud LLM (Gemini).
    """
    payload = {
        "prompt": "Hello from full stack cloud",
        "complexity": "HIGH",
        "privacy_level": "PUBLIC",
        "inference_mode": "CLOUD"
    }

    # Access the dynamically initialized router from the lifespan
    assert backend.services.router is not None
    original_gemini = backend.services.router.gemini_flash
    original_sovereign = getattr(backend.services.router.settings, "SOVEREIGN_MODE", True)
    
    mock_flash = AsyncMock()
    mock_flash.generate_content_async.return_value = MagicMock(text="I am the cloud model response.")
    backend.services.router.gemini_flash = mock_flash
    backend.services.router.gemini_pro = mock_flash
    backend.services.router.settings.SOVEREIGN_MODE = False
    
    try:
        with patch("backend.inference.router.GEMINI_AVAILABLE", True):
            response = client.post("/api/v1/gemini/proxy", json=payload, headers=auth_headers)
        assert response.status_code == 200, f"Error: {response.text}"
        data = response.json()
        assert data["result"] == "I am the cloud model response."
        mock_flash.generate_content_async.assert_called_once()
    finally:
        backend.services.router.gemini_flash = original_gemini
        backend.services.router.settings.SOVEREIGN_MODE = original_sovereign

def test_full_stack_tactical_router(client: TestClient, auth_headers: dict):
    """
    Tests the tactical routing (Groq) for low-latency requests.
    """
    payload = {
        "prompt": "Quick tactical question",
        "complexity": "LOW",
        "privacy_level": "PUBLIC",
        "inference_mode": "TACTICAL"
    }

    # tactical uses httpx.AsyncClient.post internally, we'll patch that network boundary
    with patch("backend.inference.router.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Tactical response deployed."}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Temporarily enable groq routing in the services router
        assert backend.services.router is not None
        original_groq_key = backend.services.router.groq_api_key
        backend.services.router.groq_api_key = "test_tactical_key"

        try:
            response = client.post("/api/v1/gemini/proxy", json=payload, headers=auth_headers)
            assert response.status_code == 200, f"Error: {response.text}"
            data = response.json()
            assert data["result"] == "Tactical response deployed."
            mock_post.assert_called_once()
        finally:
            backend.services.router.groq_api_key = original_groq_key
