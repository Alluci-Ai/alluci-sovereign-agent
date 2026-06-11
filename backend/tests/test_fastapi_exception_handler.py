import pytest
pytestmark = pytest.mark.unit

from fastapi.testclient import TestClient
from backend.app import app, settings

client = TestClient(app)

def _add_error_route(path: str):
    # Add a route that raises an exception if not already added
    if not any(route.path == path for route in app.routes):
        @app.get(path)
        async def error_endpoint():
            raise RuntimeError("Sensitive error")

def test_global_exception_handler_debug_off(monkeypatch):
    # Ensure DEBUG is False
    monkeypatch.setattr(settings, "DEBUG", False)
    test_path = "/error-off"
    _add_error_route(test_path)
    response = client.get(test_path)
    assert response.status_code == 500
    json_resp = response.json()
    # Generic message when DEBUG is False
    expected_msg = "An internal server error occurred. Please contact the administrator or check the logs."
    assert json_resp["detail"] == expected_msg

def test_global_exception_handler_debug_on(monkeypatch):
    # Ensure DEBUG is True
    monkeypatch.setattr(settings, "DEBUG", True)
    test_path = "/error-on"
    _add_error_route(test_path)
    response = client.get(test_path)
    assert response.status_code == 500
    json_resp = response.json()
    # Detailed error message when DEBUG is True
    assert json_resp["detail"] == "Sensitive error"
