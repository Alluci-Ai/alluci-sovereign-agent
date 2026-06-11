import pytest
pytestmark = pytest.mark.unit

from fastapi.testclient import TestClient
from backend.app import app
from backend.security.auth import verify_admin
from fastapi import HTTPException

@pytest.fixture(scope="function")
def client():
    """TestClient with verify_admin overridden to succeed, cleaned up after test."""
    # No exception means admin passes
    app.dependency_overrides[verify_admin] = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_get_allowed_hosts(client: TestClient):
    response = client.get("/api/v1/egress/hosts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "hosts" in data
    assert isinstance(data["hosts"], list)

def test_update_allowed_hosts(client: TestClient):
    payload = {"hosts": ["host1.example.com", "host2.example.com"]}
    response = client.post("/api/v1/egress/hosts", json=payload)
    assert response.status_code == 200
    assert response.json() == payload

def test_get_rotation_schedule(client: TestClient):
    response = client.get("/api/v1/egress/rotation")
    assert response.status_code == 200
    data = response.json()
    assert "interval_days" in data
    assert isinstance(data["interval_days"], int)

def test_update_rotation_schedule(client: TestClient):
    payload = {"interval_days": 15, "last_rotated": None}
    response = client.post("/api/v1/egress/rotation", json=payload)
    assert response.status_code == 200
    assert response.json() == payload
