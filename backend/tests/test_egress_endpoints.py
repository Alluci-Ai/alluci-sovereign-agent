import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.security.auth import verify_admin

client = TestClient(app)

# Override admin verification for successful auth
app.dependency_overrides[verify_admin] = lambda: None


def test_get_allowed_hosts():
    response = client.get("/api/v1/egress/hosts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "hosts" in data
    assert isinstance(data["hosts"], list)

def test_update_allowed_hosts():
    payload = {"hosts": ["host1.example.com", "host2.example.com"]}
    response = client.post("/api/v1/egress/hosts", json=payload)
    assert response.status_code == 200
    assert response.json() == payload

def test_get_rotation_schedule():
    response = client.get("/api/v1/egress/rotation")
    assert response.status_code == 200
    data = response.json()
    assert "interval_days" in data
    assert isinstance(data["interval_days"], int)

def test_update_rotation_schedule():
    payload = {"interval_days": 15, "last_rotated": None}
    response = client.post("/api/v1/egress/rotation", json=payload)
    assert response.status_code == 200
    assert response.json() == payload
