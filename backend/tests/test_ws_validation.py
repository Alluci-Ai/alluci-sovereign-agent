import pytest
pytestmark = pytest.mark.unit

import json
from fastapi.testclient import TestClient
from backend.ws_gateway import JsonRpcGateway, ConnectedClient
from backend.security.auth import create_access_token
from unittest.mock import AsyncMock

def generate_test_token():
    return create_access_token(data={"sub": "testuser"})

@pytest.fixture
def gateway():
    gw = JsonRpcGateway("test_secret")
    # Inject minimal services needed for exec.allow
    gw.inject_services(approval_manager=type("MockMgr", (), {"handle_allow": lambda self, request_id, persist=False, command="", tool_name="": {"status": "allowed"}})())
    return gw

def test_exec_allow_validation_error(gateway):
    # Missing required request_id will trigger validation error
    token = generate_test_token()
    client = ConnectedClient(AsyncMock(), "c1", "testuser")
    gateway.clients["c1"] = client
    # Simulate a request with empty params
    raw = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "exec.allow", "params": {}})
    # Call dispatch directly
    import asyncio
    asyncio.run(gateway._dispatch(raw, client))
    # Since client websocket is a mock, capture send_text calls
    client.websocket.send_text.assert_called()
    sent = client.websocket.send_text.call_args[0][0]
    resp = json.loads(sent)
    assert resp["error"]["code"] == -32602
    assert "validation_errors" in resp["error"]["data"]
