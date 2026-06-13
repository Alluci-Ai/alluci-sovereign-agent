import pytest
pytestmark = pytest.mark.unit

import asyncio
import json
from unittest.mock import patch
from backend.ws_gateway import JsonRpcGateway, ConnectedClient
from backend.ws_gateway import _rpc_error, _rpc_success
from backend.schemas.ws_gateway import ExecAllowParams

class MockWebSocket:
    """Simple mock WebSocket that records sent messages."""
    def __init__(self):
        self.sent_messages = []
        self.closed = False
        self.close_code = None
        self.close_reason = None

    async def send_text(self, text: str):
        self.sent_messages.append(text)

    async def close(self, code: int = 1000, reason: str = ""):
        self.closed = True
        self.close_code = code
        self.close_reason = reason

    # The real gateway only calls `receive_text` during authentication, which we bypass.
    async def receive_text(self):
        return ""

    @property
    def cookies(self):
        return {}

@pytest.mark.asyncio
@patch("backend.ws_gateway.settings.DEBUG", True)
async def test_invalid_params_return_error_with_validation_details():
    # Prepare gateway and a mock client
    gateway = JsonRpcGateway(jwt_secret="test-secret")
    mock_ws = MockWebSocket()
    client = ConnectedClient(mock_ws, client_id="c1", subject="test")  # type: ignore

    # Craft a request missing the required 'request_id' for exec.allow
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "exec.allow",
        "params": {"persist": True}
    })

    await gateway._dispatch(request, client)

    # Exactly one message should have been sent (the error response)
    assert len(mock_ws.sent_messages) == 1
    response = json.loads(mock_ws.sent_messages[0])
    assert response["error"]["code"] == -32602  # INVALID_PARAMS
    # Validation errors should be present in the data field
    assert "validation_errors" in response["error"].get("data", {})

@pytest.mark.asyncio
async def test_valid_params_return_success():
    gateway = JsonRpcGateway(jwt_secret="test-secret")
    mock_ws = MockWebSocket()
    client = ConnectedClient(mock_ws, client_id="c2", subject="test")  # type: ignore

    # Provide all required fields for ExecAllowParams
    request = json.dumps({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "exec.allow",
        "params": {
            "request_id": "req-123",
            "persist": False,
            "command": "echo hello",
            "tool_name": "shell"
        }
    })

    # Since there is no approval_manager injected, the handler will return an error dict.
    await gateway._dispatch(request, client)

    # Should receive a success response (even if the handler returns an error dict, it is still a result).
    assert len(mock_ws.sent_messages) == 1
    response = json.loads(mock_ws.sent_messages[0])
    assert "result" in response
    # The result should contain the error dict from the missing approval_manager.
    assert isinstance(response["result"], dict)
    assert response["result"].get("error") == "No approval manager"
