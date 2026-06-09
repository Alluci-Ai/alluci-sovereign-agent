import pytest
from fastapi.testclient import TestClient
from backend.app import app, SovereignAPIException, _check_health
from backend.engine.errors import AdapterError
from fastapi import Request, Response
from unittest.mock import AsyncMock, patch

@pytest.fixture
def test_client(app_client):
    # This comes from conftest.py, with everything mocked out
    return app_client

def test_health_check(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "components" in data

def test_ready_check(test_client):
    response = test_client.get("/ready")
    assert response.status_code == 200

def test_exception_handler_adapter_error(test_client):
    @app.get("/test-adapter-error")
    def trigger_adapter_error():
        raise AdapterError("Mock adapter failed")
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-adapter-error")
    assert response.status_code == 500
    assert response.json()["status"] == "error"
    assert "Mock adapter failed" in response.json()["message"]

def test_exception_handler_sovereign_api(test_client):
    @app.get("/test-sovereign-error")
    def trigger_sovereign_error():
        raise SovereignAPIException(403, "ERR_403", "Test detail")
    
    response = test_client.get("/test-sovereign-error")
    assert response.status_code == 403
    assert response.json() == {"error_code": "ERR_403", "detail": "Test detail"}

@patch("backend.app.settings")
def test_exception_handler_global_error_production(mock_settings):
    mock_settings.APP_ENV = "production"
    
    @app.get("/test-global-error-prod")
    def trigger_global_error_prod():
        raise RuntimeError("Secret internal failure")
        
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-global-error-prod")
    assert response.status_code == 500
    assert "Secret internal failure" not in response.json()["detail"]
    assert "Internal Server Error" in response.json()["message"]

@patch("backend.app.settings")
def test_exception_handler_global_error_dev(mock_settings):
    # Enable debug mode for this test
    mock_settings.DEBUG = True
    # Reload the backend.app module so the patched settings are observed
    import importlib
    import backend.app as app_module
    importlib.reload(app_module)

    @app_module.app.get("/test-global-error-dev")
    def trigger_global_error_dev():
        raise RuntimeError("Secret internal failure")

    client = TestClient(app_module.app, raise_server_exceptions=False)
    response = client.get("/test-global-error-dev")
    assert response.status_code == 500
    # In testing, APP_ENV is "testing", so details should be exposed
    assert "Secret internal failure" in response.json()["detail"]

@pytest.mark.asyncio
async def test_check_health_logic():
    # Test degraded health check logic directly
    mock_app = type("App", (), {})()
    
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = Exception("Redis down")
    
    mock_app.state = type("State", (), {"redis_client": mock_redis})()
    
    # Mock db to fail
    with patch("sqlmodel.Session") as mock_session:
        mock_session.side_effect = Exception("DB down")
        res = await _check_health(mock_app)
        
    assert res["status"] == "degraded"
    assert res["components"]["redis"] == "error"
    assert res["components"]["database"] == "error"

def test_static_files(test_client):
    # Simply pinging the frontend entrypoint index.html
    # If it's returning a 200 or 404 cleanly, the static mounting didn't crash
    response = test_client.get("/")
    assert response.status_code in [200, 404]
