import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.exec_approval import router
from backend.security.auth import verify_authenticated
from backend import services

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_get_pending_approvals_not_ready():
    services.exec_approval = None
    res = client.get("/exec/pending")
    assert res.status_code == 503

@pytest.mark.asyncio
async def test_get_pending_approvals():
    services.exec_approval = AsyncMock()
    services.exec_approval.get_pending.return_value = [{"id": "1"}]
    # We must use TestClient or httpx directly, TestClient handles async if Starlette does
    # Actually wait, TestClient runs async endpoints.
    # We need to mock the service correctly.
    # It's an async mock, so TestClient will await it
    res = client.get("/exec/pending")
    assert res.status_code == 200
    assert res.json() == [{"id": "1"}]

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_approve_request_not_ready(mock_csrf):
    services.exec_approval = None
    res = client.post("/exec/approve/req1")
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_approve_request(mock_csrf):
    services.exec_approval = AsyncMock()
    services.exec_approval.approve.return_value = {"status": "APPROVED"}
    res = client.post("/exec/approve/req1")
    assert res.status_code == 200
    assert res.json() == {"status": "APPROVED"}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_deny_request_not_ready(mock_csrf):
    services.exec_approval = None
    res = client.post("/exec/deny/req1")
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_deny_request(mock_csrf):
    services.exec_approval = AsyncMock()
    services.exec_approval.deny.return_value = {"status": "DENIED"}
    res = client.post("/exec/deny/req1")
    assert res.status_code == 200
    assert res.json() == {"status": "DENIED"}

def test_list_policies_not_ready():
    services.exec_approval = None
    res = client.get("/exec/policies")
    assert res.status_code == 503

def test_list_policies():
    services.exec_approval = AsyncMock()
    services.exec_approval.list_policies.return_value = [{"id": 1}]
    res = client.get("/exec/policies")
    assert res.status_code == 200
    assert res.json() == [{"id": 1}]

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_add_policy_not_ready(mock_csrf):
    services.exec_approval = None
    res = client.post("/exec/policies", json={"rule": "*"})
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_add_policy(mock_csrf):
    services.exec_approval = AsyncMock()
    services.exec_approval.add_policy.return_value = {"id": 1}
    res = client.post("/exec/policies", json={"rule": "*"})
    assert res.status_code == 200
    assert res.json() == {"id": 1}

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_policy_not_ready(mock_csrf):
    services.exec_approval = None
    res = client.delete("/exec/policies/1")
    assert res.status_code == 503

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_delete_policy(mock_csrf):
    services.exec_approval = AsyncMock()
    services.exec_approval.delete_policy.return_value = True
    res = client.delete("/exec/policies/1")
    assert res.status_code == 200
    assert res.json() == True
