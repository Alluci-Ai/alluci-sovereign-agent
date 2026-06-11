import pytest
pytestmark = pytest.mark.unit

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    json_resp = response.json()
    # Basic sanity checks on health payload
    assert "status" in json_resp
    assert json_resp["status"] in ("ok", "degraded")
    assert "version" in json_resp
    assert "components" in json_resp
