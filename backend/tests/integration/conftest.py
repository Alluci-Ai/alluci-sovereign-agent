import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from backend.app import app
from backend.security.auth import create_access_token
from backend.config import settings
import httpx

from unittest.mock import patch

@pytest.fixture(scope="module")
def client():
    """
    Spins up the full ASGI application via FastAPI's TestClient to ensure all 
    startup checks, vault initialization, and services are fully loaded.
    TestClient natively handles ASGI lifespan events perfectly.
    """
    original_env = settings.APP_ENV
    settings.APP_ENV = "testing"
    
    # Patch the availability flags during lifespan to prevent ModelRouter from 
    # attempting to configure real cloud SDKs, which is crashing the sandbox setup.
    with patch("backend.inference.router.GEMINI_AVAILABLE", False), \
         patch("backend.inference.router.OPENAI_AVAILABLE", False):
        try:
            # TestClient automatically runs app lifespan (startup/shutdown)
            with TestClient(app) as test_client:
                yield test_client
        finally:
            settings.APP_ENV = original_env

@pytest.fixture(scope="module")
def auth_headers(client):
    """
    Generates a valid JWT token. Because this depends on 'client', 
    the app's lifespan (and thus JWT key initialization) has already completed.
    """
    token = create_access_token(data={"sub": "admin", "role": "admin"})
    return {"Authorization": f"Bearer {token}"}
