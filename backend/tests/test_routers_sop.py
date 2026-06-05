import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.sop import router
from backend.security.auth import verify_authenticated
from backend import services
from backend.models import SOPRecord

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_list_sops_not_ready():
    services.sop_engine = None
    res = client.get("/sops/")
    assert res.status_code == 503

def test_list_sops_success():
    services.sop_engine = MagicMock()
    mock_sop = SOPRecord(id=1, name="s1", description="d1", steps=[], created_at="2026-01-01T00:00:00Z", is_active=True)
    services.sop_engine.list_sops.return_value = [mock_sop]
    res = client.get("/sops/")
    assert res.status_code == 200
    assert len(res.json()) == 1

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_register_sop_not_ready(mock_csrf):
    services.sop_engine = None
    res = client.post("/sops/", json={"name": "s", "description": "d", "steps": []})
    assert res.status_code == 503

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_register_sop_success(mock_csrf):
    services.sop_engine = AsyncMock()
    services.sop_engine.register_sop.return_value = 1
    res = client.post("/sops/", json={"name": "s", "description": "d", "steps": []})
    assert res.status_code == 200
    assert res.json()["id"] == 1

def test_get_sop_not_ready():
    services.sop_engine = None
    res = client.get("/sops/1")
    assert res.status_code == 503

def test_get_sop_not_found():
    services.sop_engine = MagicMock()
    services.sop_engine.get_sop.return_value = None
    res = client.get("/sops/1")
    assert res.status_code == 404

def test_get_sop_success():
    services.sop_engine = MagicMock()
    mock_sop = SOPRecord(id=1, name="s1", description="d1", steps=[], created_at="2026-01-01T00:00:00Z", is_active=True)
    services.sop_engine.get_sop.return_value = mock_sop
    res = client.get("/sops/1")
    assert res.status_code == 200
    assert res.json()["id"] == 1

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_execute_sop_not_ready(mock_csrf):
    services.sop_engine = None
    res = client.post("/sops/1/execute", json={})
    assert res.status_code == 503

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_execute_sop_value_error(mock_csrf):
    services.sop_engine = AsyncMock()
    services.sop_engine.execute_sop.side_effect = ValueError("bad")
    res = client.post("/sops/1/execute", json={})
    assert res.status_code == 404

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_execute_sop_exception(mock_csrf):
    services.sop_engine = AsyncMock()
    services.sop_engine.execute_sop.side_effect = Exception("error")
    res = client.post("/sops/1/execute", json={})
    assert res.status_code == 500

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_execute_sop_success(mock_csrf):
    services.sop_engine = AsyncMock()
    services.sop_engine.execute_sop.return_value = {"status": "ok"}
    res = client.post("/sops/1/execute", json={})
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}
