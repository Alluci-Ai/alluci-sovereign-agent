import pytest
pytestmark = pytest.mark.unit

import os
import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.security import router
from backend.security.network_policy import EgressFilterTransport
from backend.security.circuit_breaker import circuit_breaker

app = FastAPI()
app.include_router(router)
client = TestClient(app)

@patch("backend.routers.security.resolution_manager")
def test_resolve_cancel_task_success(mock_manager):
    mock_manager.provide_resolution.return_value = True
    res = client.post("/security/resolve", json={
        "task_id": "task1",
        "resolution_type": "CANCEL_TASK"
    })
    assert res.status_code == 200
    assert res.json()["action"] == "task_cancelled"
    mock_manager.provide_resolution.assert_called_once_with("task1", "CANCEL_TASK")

@patch("backend.routers.security.resolution_manager")
def test_resolve_cancel_task_not_found(mock_manager):
    mock_manager.provide_resolution.return_value = False
    res = client.post("/security/resolve", json={
        "task_id": "task1",
        "resolution_type": "CANCEL_TASK"
    })
    assert res.status_code == 404

def test_resolve_allow_domain_no_domain():
    res = client.post("/security/resolve", json={
        "task_id": "task1",
        "resolution_type": "ALLOW_DOMAIN_SESSION"
    })
    assert res.status_code == 400

@patch("backend.routers.security.resolution_manager")
def test_resolve_allow_domain_session(mock_manager):
    res = client.post("/security/resolve", json={
        "task_id": "task1",
        "resolution_type": "ALLOW_DOMAIN_SESSION",
        "metadata": {"domain": "example.com"}
    })
    assert res.status_code == 200
    assert "example.com" in EgressFilterTransport.TRUSTED_DOMAINS
    mock_manager.provide_resolution.assert_called_once_with("task1", "ALLOW_DOMAIN_SESSION")

@patch("backend.routers.security.resolution_manager")
def test_resolve_allow_domain_permanent(mock_manager, tmp_path):
    config_path = tmp_path / "trusted_domains.json"
    with patch("os.path.expanduser", return_value=str(config_path)):
        res = client.post("/security/resolve", json={
            "task_id": "task1",
            "resolution_type": "ALLOW_DOMAIN_PERMANENT",
            "metadata": {"domain": "permanent.com"}
        })
        assert res.status_code == 200
        assert "permanent.com" in EgressFilterTransport.TRUSTED_DOMAINS
        
        assert os.path.exists(config_path)
        with open(config_path, "r") as f:
            domains = json.load(f)
            assert "permanent.com" in domains

@patch("backend.routers.security.resolution_manager")
def test_resolve_ignore_budget_verus(mock_manager):
    initial = circuit_breaker.MAX_VERUS_SPEND_PER_DAY
    res = client.post("/security/resolve", json={
        "task_id": "task1",
        "resolution_type": "IGNORE_BUDGET",
        "metadata": {"budget_type": "VERUS", "amount": 5.0}
    })
    assert res.status_code == 200
    assert circuit_breaker.MAX_VERUS_SPEND_PER_DAY == initial + 15.0

@patch("backend.routers.security.resolution_manager")
def test_resolve_ignore_budget_llm(mock_manager):
    initial = circuit_breaker.MAX_LLM_API_COST_PER_DAY
    res = client.post("/security/resolve", json={
        "task_id": "task1",
        "resolution_type": "IGNORE_BUDGET",
        "metadata": {"budget_type": "LLM", "amount": 2.0}
    })
    assert res.status_code == 200
    assert circuit_breaker.MAX_LLM_API_COST_PER_DAY == initial + 7.0

@patch("backend.routers.security.resolution_manager")
@patch("backend.routers.security.CalibrationManager")
def test_resolve_override_tearing(mock_cm_class, mock_manager):
    mock_cm_instance = mock_cm_class.return_value
    res = client.post("/security/resolve", json={
        "task_id": "task1",
        "resolution_type": "OVERRIDE_TEARING",
        "metadata": {"topology_shift": 2.5, "origin": "test_agent", "is_tool": True}
    })
    
    assert res.status_code == 200
    assert res.json()["action"] == "tearing_overridden"
    
    # Assert log_approved_trajectory is called with shift / 10.0
    mock_cm_instance.log_approved_trajectory.assert_called_once_with(0.25, origin="test_agent", is_tool=True)
    mock_manager.provide_resolution.assert_called_once_with("task1", "OVERRIDE_TEARING")

def test_resolve_unknown():
    res = client.post("/security/resolve", json={
        "task_id": "task1",
        "resolution_type": "UNKNOWN"
    })
    assert res.status_code == 400
