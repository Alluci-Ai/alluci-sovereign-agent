import pytest
from fastapi.testclient import TestClient

@pytest.mark.sanity
def test_app_sanity_startup():
    """
    Core Sanity Test: Spin up the entire FastAPI application to verify
    there are no syntax errors, missing dependencies, or catastrophic
    middleware failures. This test ensures the app is fundamentally healthy.
    """
    # Import inside the test so an import failure is caught by the test, 
    # not during pytest test collection.
    from backend.app import app
    
    with TestClient(app) as client:
        # Hit the readiness endpoint
        response = client.get("/api/v1/ready")
        assert response.status_code == 200, f"App startup failed. Output: {response.text}"
        data = response.json()
        assert data.get("status") == "ready", f"Unexpected status: {data}"
