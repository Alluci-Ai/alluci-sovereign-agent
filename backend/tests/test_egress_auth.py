import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.security.auth import verify_admin
from fastapi import HTTPException

@pytest.fixture(scope="function")
def client():
    """TestClient with verify_admin overridden to fail, cleaned up after test."""
    def override_fail():
        raise HTTPException(status_code=401, detail="Admin auth failed")
    app.dependency_overrides[verify_admin] = override_fail
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_get_allowed_hosts_unauthenticated(client: TestClient):
    response = client.get("/api/v1/egress/hosts")
    assert response.status_code == 401

def test_update_allowed_hosts_unauthenticated(client: TestClient):
    payload = {"hosts": ["host1.example.com"]}
    response = client.post("/api/v1/egress/hosts", json=payload)
    assert response.status_code == 401
