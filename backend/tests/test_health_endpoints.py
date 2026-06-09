from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_healthz():
    resp = client.get("/healthz")
    assert resp.status_code == 200
    json_data = resp.json()
    assert isinstance(json_data, dict)
    assert "status" in json_data

def test_readyz():
    resp = client.get("/readyz")
    # readyz may be 200 (ready) or 503 (not ready) depending on env
    assert resp.status_code in (200, 503)
    # If 200, ensure basic status field
    if resp.status_code == 200:
        json_data = resp.json()
        assert isinstance(json_data, dict)
        assert json_data.get("status") == "ready"
