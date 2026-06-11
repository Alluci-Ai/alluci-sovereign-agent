import pytest
pytestmark = pytest.mark.unit

import base64
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from cryptography.hazmat.primitives.asymmetric import ed25519
from backend.routers.objectives import router, verify_manifest, _canonicalize
from backend.security.auth import verify_authenticated
from backend import services

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_canonicalize():
    assert _canonicalize({"b": 1, "a": 2}) == '{"a":2,"b":1}'
    assert _canonicalize([2, 1]) == '[2,1]'
    assert _canonicalize("string") == '"string"'

def test_verify_manifest():
    from cryptography.hazmat.primitives import serialization
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    pub_hex = pub_bytes.hex()
    
    manifest = {"rootPublicKey": pub_hex, "autonomyLevel": "SOVEREIGN"}
    canonical = _canonicalize(manifest)
    signature = private_key.sign(canonical.encode("utf-8"))
    
    signed_payload = {
        "manifest": manifest,
        "signature": signature.hex()
    }
    encoded = base64.b64encode(json.dumps(signed_payload).encode()).decode()
    
    res = verify_manifest(encoded)
    assert res == manifest

def test_verify_manifest_invalid():
    with pytest.raises(Exception):
        verify_manifest("invalid_base64")

def test_execute_objective_not_ready():
    services.orchestrator = None
    res = client.post("/objective/execute", json={"objective": "test"})
    assert res.status_code == 503

@pytest.mark.asyncio
@patch("backend.routers.objectives.settings")
@patch("backend.routers.objectives.policy_engine")
async def test_execute_objective_testing(mock_policy, mock_settings):
    mock_settings.APP_ENV = "testing"
    services.orchestrator = AsyncMock()
    services.orchestrator.execute_objective.return_value = "run1"
    
    mock_policy.evaluate.return_value = True
    
    res = client.post("/objective/execute", json={"objective": "test task", "autonomy_level": "SOVEREIGN"})
    assert res.status_code == 200
    assert res.json() == {"status": "accepted", "run_id": "run1"}

@pytest.mark.asyncio
@patch("backend.routers.objectives.settings")
async def test_execute_objective_prod_missing_header(mock_settings):
    mock_settings.APP_ENV = "production"
    services.orchestrator = AsyncMock()
    res = client.post("/objective/execute", json={"objective": "test"})
    assert res.status_code == 403
    assert "header required" in res.json()["detail"]

@pytest.mark.asyncio
@patch("backend.routers.objectives.settings")
@patch("backend.routers.objectives.policy_engine")
async def test_execute_objective_rejected_by_policy(mock_policy, mock_settings):
    mock_settings.APP_ENV = "testing"
    services.orchestrator = AsyncMock()
    mock_policy.evaluate.return_value = False
    
    res = client.post("/objective/execute", json={"objective": "test task"})
    assert res.status_code == 403
    assert "rejected by autonomy policy" in res.json()["detail"]

@pytest.mark.asyncio
@patch("backend.routers.objectives.settings")
@patch("backend.routers.objectives.policy_engine")
async def test_execute_objective_guardrail_block(mock_policy, mock_settings):
    mock_settings.APP_ENV = "testing"
    services.orchestrator = AsyncMock()
    mock_policy.evaluate.return_value = True
    
    services.scanner = AsyncMock()
    services.scanner.scan_input.return_value = (False, "Bad objective")
    
    res = client.post("/objective/execute", json={"objective": "test task"})
    assert res.status_code == 400
    assert "rejected by safety gate" in res.json()["detail"]
    
@pytest.mark.asyncio
@patch("backend.routers.objectives.settings")
@patch("backend.routers.objectives.policy_engine")
async def test_execute_objective_delegate(mock_policy, mock_settings):
    mock_settings.APP_ENV = "testing"
    services.orchestrator = AsyncMock()
    services.orchestrator.multi_agent_delegate.return_value = "Delegated"
    mock_policy.evaluate.return_value = True
    services.scanner = None
    
    res = client.post("/objective/execute?agent_id=child1", json={"objective": "test task"})
    assert res.status_code == 200
    assert res.json() == {"status": "accepted", "run_id": None, "detail": "Delegated"}
    services.orchestrator.multi_agent_delegate.assert_called_once_with("child1", "test task")
