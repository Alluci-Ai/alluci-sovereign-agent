import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.telemetry import router
from backend.security.auth import verify_authenticated
from backend import services

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_post_telemetry_not_ready(mock_csrf):
    services.ace = None
    res = client.post("/telemetry", json={"hr": 60})
    assert res.status_code == 503

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_post_telemetry_success(mock_csrf):
    services.ace = MagicMock()
    services.ace.process_telemetry.return_value = {"mode": "FLOW", "reason": "optimal"}
    services.ace.current_state = {
        "physical_vitality": 0.8,
        "stress_score": 0.1,
        "flow_mode": "FLOW"
    }
    services.memory = AsyncMock()
    services.orchestrator = AsyncMock()
    services.orchestrator.harmonic = AsyncMock()
    services.ws_gw = AsyncMock()

    res = client.post("/telemetry", json={
        "hr": 60,
        "hrv": 50,
        "respiratory_rate": 15,
        "device_id": "watch1",
        "valence": 0.6,
        "arousal": 0.4,
        "focus": 0.8
    })

    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"
    services.memory.store.assert_called_once()
    services.orchestrator.harmonic.tick.assert_called_once()
    services.ws_gw.broadcast_event.assert_called_once()

@pytest.mark.asyncio
@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_post_telemetry_exceptions(mock_csrf):
    services.ace = MagicMock()
    services.ace.process_telemetry.return_value = {"mode": "FLOW", "reason": "optimal"}
    services.ace.current_state = {
        "physical_vitality": 0.8,
        "stress_score": 0.1,
        "flow_mode": "FLOW"
    }
    services.memory = AsyncMock()
    services.memory.store.side_effect = Exception("db error")
    
    services.orchestrator = AsyncMock()
    services.orchestrator.harmonic = AsyncMock()
    services.orchestrator.harmonic.tick.side_effect = Exception("tick error")
    
    services.ws_gw = AsyncMock()
    services.ws_gw.broadcast_event.side_effect = Exception("ws error")

    res = client.post("/telemetry", json={
        "hr": 60,
    })

    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"
