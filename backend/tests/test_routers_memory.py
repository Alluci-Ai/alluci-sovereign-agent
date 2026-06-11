import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import json
from backend.routers.memory import router
from backend.security.auth import verify_authenticated
from backend import services

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_list_memory_not_ready():
    services.memory = None
    res = client.get("/memory")
    assert res.status_code == 503

@pytest.mark.asyncio
async def test_list_memory():
    services.memory = AsyncMock()
    services.memory.list_entries.return_value = [{"id": "1"}]
    res = client.get("/memory")
    assert res.status_code == 200
    assert res.json() == [{"id": "1"}]

def test_search_memory_not_ready():
    services.memory = None
    res = client.get("/memory/search?q=test")
    assert res.status_code == 503

@pytest.mark.asyncio
async def test_search_memory():
    services.memory = AsyncMock()
    services.memory.search.return_value = [{"id": "1"}]
    res = client.get("/memory/search?q=test")
    assert res.status_code == 200
    assert res.json() == [{"id": "1"}]

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_store_memory_not_ready(mock_csrf):
    services.memory = None
    res = client.post("/memory/store", json={"content": "test"})
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_store_memory(mock_csrf):
    services.memory = AsyncMock()
    services.memory.store.return_value = {"id": "1"}
    res = client.post("/memory/store", json={"content": "test"})
    assert res.status_code == 200
    assert res.json() == {"id": "1"}

def test_get_memory_stats_not_ready():
    services.memory = None
    res = client.get("/memory/stats")
    assert res.status_code == 503

@pytest.mark.asyncio
async def test_get_memory_stats():
    services.memory = AsyncMock()
    services.memory.get_stats.return_value = {"total": 10}
    res = client.get("/memory/stats")
    assert res.status_code == 200
    assert res.json() == {"total": 10}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_memory_entry_not_ready(mock_csrf):
    services.memory = None
    res = client.delete("/memory/1")
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_memory_entry_not_found(mock_csrf):
    services.memory = AsyncMock()
    services.memory.delete.return_value = False
    res = client.delete("/memory/1")
    assert res.status_code == 404

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_memory_entry(mock_csrf):
    services.memory = AsyncMock()
    services.memory.delete.return_value = True
    res = client.delete("/memory/1")
    assert res.status_code == 200
    assert res.json() == {"status": "SUCCESS"}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_trigger_consolidation_not_ready(mock_csrf):
    services.hlsm_manager = None
    res = client.post("/memory/consolidate")
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_trigger_consolidation(mock_csrf):
    services.hlsm_manager = AsyncMock()
    services.hlsm_manager.consolidation_sweep.return_value = {"decayed": 5}
    res = client.post("/memory/consolidate")
    assert res.status_code == 200
    assert res.json()["cycle_summary"] == {"decayed": 5}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("sqlmodel.Session")
def test_pin_memory_not_found(mock_session_cls, mock_csrf):
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session
    mock_session.get.return_value = None
    res = client.patch("/memory/1/pin", json={"is_pinned": True})
    assert res.status_code == 404

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("sqlmodel.Session")
def test_pin_memory(mock_session_cls, mock_csrf):
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session
    mock_entry = MagicMock()
    mock_entry.extra_metadata = "{}"
    mock_session.get.return_value = mock_entry
    res = client.patch("/memory/1/pin", json={"is_pinned": True})
    assert res.status_code == 200
    assert json.loads(mock_entry.extra_metadata)["pinned"] is True

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("sqlmodel.Session")
def test_tag_memory_not_found(mock_session_cls, mock_csrf):
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session
    mock_session.get.return_value = None
    res = client.patch("/memory/1/tags", json={"tags": ["a"]})
    assert res.status_code == 404

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("sqlmodel.Session")
def test_tag_memory(mock_session_cls, mock_csrf):
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session
    mock_entry = MagicMock()
    mock_entry.extra_metadata = "{}"
    mock_session.get.return_value = mock_entry
    res = client.patch("/memory/1/tags", json={"tags": ["a"]})
    assert res.status_code == 200
    assert json.loads(mock_entry.extra_metadata)["tags"] == ["a"]

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_promote_memory_not_ready(mock_csrf):
    services.hlsm_manager = None
    res = client.post("/memory/1/promote")
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("sqlmodel.Session")
def test_promote_memory_not_found(mock_session_cls, mock_csrf):
    services.hlsm_manager = AsyncMock()
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session
    mock_session.get.return_value = None
    res = client.post("/memory/1/promote")
    assert res.status_code == 404

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("sqlmodel.Session")
def test_promote_memory_already_promoted(mock_session_cls, mock_csrf):
    services.hlsm_manager = AsyncMock()
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session
    mock_entry = MagicMock()
    mock_entry.promoted_to_l2 = True
    mock_session.get.return_value = mock_entry
    res = client.post("/memory/1/promote")
    assert res.status_code == 200
    services.hlsm_manager.l2_store.assert_not_called()

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("sqlmodel.Session")
def test_promote_memory_success(mock_session_cls, mock_csrf):
    services.hlsm_manager = AsyncMock()
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session
    mock_entry = MagicMock()
    mock_entry.promoted_to_l2 = False
    mock_session.get.return_value = mock_entry
    res = client.post("/memory/1/promote")
    assert res.status_code == 200
    services.hlsm_manager.l2_store.assert_called_once_with(mock_entry)
    assert mock_entry.promoted_to_l2 is True

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
@patch("sqlmodel.Session")
def test_promote_memory_exception(mock_session_cls, mock_csrf):
    services.hlsm_manager = AsyncMock()
    services.hlsm_manager.l2_store.side_effect = Exception("error")
    mock_session = MagicMock()
    mock_session_cls.return_value.__enter__.return_value = mock_session
    mock_entry = MagicMock()
    mock_entry.promoted_to_l2 = False
    mock_session.get.return_value = mock_entry
    res = client.post("/memory/1/promote")
    assert res.status_code == 500
