import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.config import router
from backend.security.auth import verify_authenticated
from backend import services

# Override auth
async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_get_config_not_ready():
    services.config_editor = None
    res = client.get("/config")
    assert res.status_code == 503

def test_get_config_success():
    services.config_editor = MagicMock()
    services.config_editor.get_config.return_value = {"test": "val"}
    res = client.get("/config")
    assert res.status_code == 200
    assert res.json() == {"test": "val"}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_update_config_not_ready(mock_csrf):
    services.config_editor = None
    res = client.put("/config", json={"k": "v"})
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_update_config_success(mock_csrf):
    services.config_editor = MagicMock()
    services.config_editor.update_config.return_value = {"k": "v"}
    res = client.put("/config", json={"k": "v"})
    assert res.status_code == 200
    assert res.json() == {"k": "v"}
    mock_csrf.assert_called_once()
    services.config_editor.update_config.assert_called_once_with({"k": "v"})

def test_get_config_schema_not_ready():
    services.config_editor = None
    res = client.get("/config/schema")
    assert res.status_code == 503

def test_get_config_schema_success():
    services.config_editor = MagicMock()
    services.config_editor.get_schema.return_value = {"type": "object"}
    res = client.get("/config/schema")
    assert res.status_code == 200
    assert res.json() == {"type": "object"}
