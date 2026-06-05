import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.goals import router
from backend.security.auth import verify_authenticated
from backend import services

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_list_goals_not_ready():
    services.goal_engine = None
    res = client.get("/goals/")
    assert res.status_code == 503

@pytest.mark.asyncio
async def test_list_goals():
    services.goal_engine = AsyncMock()
    # It returns a list of GoalRecords or dicts
    services.goal_engine.list_goals.return_value = [{"id": 1, "title": "test", "description": "desc", "status": "ACTIVE", "created_at": "2024-01-01T00:00:00Z"}]
    res = client.get("/goals/")
    assert res.status_code == 200
    assert len(res.json()) == 1

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_create_goal_not_ready(mock_csrf):
    services.goal_engine = None
    res = client.post("/goals/", json={"title": "t", "description": "d"})
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_create_goal(mock_csrf):
    services.goal_engine = AsyncMock()
    services.goal_engine.create_goal.return_value = 1
    res = client.post("/goals/", json={"title": "t", "description": "d"})
    assert res.status_code == 200
    assert res.json() == {"id": 1, "status": "CREATED"}

def test_get_goal_not_ready():
    services.goal_engine = None
    res = client.get("/goals/1")
    assert res.status_code == 503

@pytest.mark.asyncio
async def test_get_goal_not_found():
    services.goal_engine = AsyncMock()
    services.goal_engine.get_goal.return_value = None
    res = client.get("/goals/1")
    assert res.status_code == 404

@pytest.mark.asyncio
async def test_get_goal():
    services.goal_engine = AsyncMock()
    services.goal_engine.get_goal.return_value = {"id": 1, "title": "test", "description": "desc", "status": "ACTIVE", "created_at": "2024-01-01T00:00:00Z"}
    res = client.get("/goals/1")
    assert res.status_code == 200
    assert res.json()["id"] == 1

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_update_goal_not_ready(mock_csrf):
    services.goal_engine = None
    res = client.patch("/goals/1", json={"status": "DONE"})
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_update_goal_not_found(mock_csrf):
    services.goal_engine = AsyncMock()
    services.goal_engine.update_goal.return_value = False
    res = client.patch("/goals/1", json={"status": "DONE"})
    assert res.status_code == 404

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_update_goal(mock_csrf):
    services.goal_engine = AsyncMock()
    services.goal_engine.update_goal.return_value = True
    res = client.patch("/goals/1", json={"status": "DONE"})
    assert res.status_code == 200
    assert res.json() == {"status": "UPDATED"}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_goal_not_ready(mock_csrf):
    services.goal_engine = None
    res = client.delete("/goals/1")
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_goal_not_found(mock_csrf):
    services.goal_engine = AsyncMock()
    services.goal_engine.delete_goal.return_value = False
    res = client.delete("/goals/1")
    assert res.status_code == 404

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_goal(mock_csrf):
    services.goal_engine = AsyncMock()
    services.goal_engine.delete_goal.return_value = True
    res = client.delete("/goals/1")
    assert res.status_code == 200
    assert res.json() == {"status": "DELETED"}
