import pytest
from fastapi.testclient import TestClient
from backend.app import app
from backend.security.auth import verify_admin

client = TestClient(app)

# Override admin verification to simulate missing/invalid admin

def override_fail():
    from fastapi import HTTPException
    raise HTTPException(status_code=401, detail="Admin auth failed")

app.dependency_overrides[verify_admin] = override_fail

def test_get_allowed_hosts_unauthenticated():
    response = client.get("/api/v1/egress/hosts")
    assert response.status_code == 500 or response.status_code == 401

def test_update_allowed_hosts_unauthenticated():
    payload = {"hosts": ["host1.example.com"]}
    response = client.post("/api/v1/egress/hosts", json=payload)
    assert response.status_code == 500 or response.status_code == 401
