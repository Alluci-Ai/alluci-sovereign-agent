import pytest
pytestmark = pytest.mark.unit

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.app import app
from backend import services

@pytest.fixture
def mock_usage_tracker():
    tracker = MagicMock()
    tracker.get_summary.return_value = {
        "total_input": 5000,
        "total_output": 2500,
        "cache_read": 500,
        "cache_write": 100,
        "total_cost": 0.012345,
        "session_count": 3
    }
    tracker.get_daily.return_value = [
        {
            "date": "2026-08-12",
            "input_tokens": 5000,
            "output_tokens": 2500,
            "cache_read": 500,
            "cache_write": 100,
            "cost": 0.012345,
            "turns": 5
        }
    ]
    tracker.get_sessions.return_value = {
        "sessions": [
            {
                "session_key": "test_session_1",
                "agent": "MAIN",
                "provider": "MLX",
                "models": ["alluci-polytope-gemma-4-31b"],
                "total_input": 5000,
                "total_output": 2500,
                "total_cache_read": 500,
                "total_cache_write": 100,
                "total_cost": 0.012345,
                "turn_count": 5,
                "messages": 10,
                "first_turn": "2026-08-12T10:00:00Z",
                "last_turn": "2026-08-12T10:05:00Z"
            }
        ],
        "totals": {
            "total_input": 5000,
            "total_output": 2500,
            "cache_read": 500,
            "cache_write": 100,
            "total_cost": 0.012345,
            "session_count": 1
        },
        "limit_reached": False,
        "missing_cost_entries": 0
    }
    tracker.get_session_timeseries.return_value = [
        {
            "timestamp": "2026-08-12T10:00:00Z",
            "model": "alluci-polytope-gemma-4-31b",
            "input_tokens": 1000,
            "output_tokens": 500,
            "turn_cost": 0.002,
            "cumulative_cost": 0.002,
            "cumulative_tokens": 1500
        }
    ]
    return tracker

from backend.security.auth import verify_authenticated

@pytest.fixture
def client(mock_usage_tracker):
    old_tracker = services.usage_tracker
    services.usage_tracker = mock_usage_tracker
    app.dependency_overrides[verify_authenticated] = lambda: True
    yield TestClient(app)
    app.dependency_overrides.pop(verify_authenticated, None)
    services.usage_tracker = old_tracker

def test_usage_summary_endpoint(client):
    with patch("backend.routers.usage.verify_token", return_value={"sub": "user@sovereign.local"}):
        headers = {"Authorization": "Bearer fake_test_token"}
        res = client.get("/api/v1/usage/summary?start=2026-08-01&end=2026-08-12", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total_input"] == 5000
        assert data["session_count"] == 3

def test_usage_daily_endpoint(client):
    with patch("backend.routers.usage.verify_token", return_value={"sub": "user@sovereign.local"}):
        headers = {"Authorization": "Bearer fake_test_token"}
        res = client.get("/api/v1/usage/daily", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["date"] == "2026-08-12"

def test_usage_sessions_endpoint(client):
    with patch("backend.routers.usage.verify_token", return_value={"sub": "user@sovereign.local"}):
        headers = {"Authorization": "Bearer fake_test_token"}
        res = client.get("/api/v1/usage/sessions?limit=10", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "sessions" in data
        assert len(data["sessions"]) == 1
        assert data["sessions"][0]["session_key"] == "test_session_1"

def test_session_timeseries_endpoint(client):
    with patch("backend.routers.usage.verify_token", return_value={"sub": "user@sovereign.local"}):
        headers = {"Authorization": "Bearer fake_test_token"}
        res = client.get("/api/v1/usage/sessions/test_session_1/timeseries", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["model"] == "alluci-polytope-gemma-4-31b"

def test_usage_csv_export_endpoint(client):
    with patch("backend.routers.usage.verify_token", return_value={"sub": "user@sovereign.local"}):
        res = client.get("/api/v1/usage/sessions/export/csv?token=fake_test_token")
        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert "test_session_1" in res.text
        assert "Session Key" in res.text
