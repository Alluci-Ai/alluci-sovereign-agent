import pytest
pytestmark = pytest.mark.unit

import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from backend.security.tunnel_handler import TunnelHandler

@pytest.fixture
def handler():
    with patch("os.getenv", side_effect=lambda k, d=None: "wss://relay" if k == "TUNNEL_RELAY_URL" else "d123" if k == "DAEMON_ID" else d):
        return TunnelHandler()

@pytest.mark.asyncio
async def test_start_stop(handler):
    assert handler.is_running is False
    await handler.start()
    assert handler.is_running is True
    assert handler._task is not None
    
    await handler.stop()
    assert handler.is_running is False
    assert handler._task.cancelled() or handler._task.done()

@pytest.mark.asyncio
async def test_start_no_relay():
    with patch("os.getenv", return_value=None):
        handler_no_relay = TunnelHandler()
        await handler_no_relay.start()
        assert handler_no_relay.is_running is False

@pytest.mark.asyncio
async def test_run_loop_success(handler):
    mock_ws = AsyncMock()
    mock_ws.__aenter__.return_value = mock_ws
    # Yield one message then raise asyncio.CancelledError to exit loop
    async def mock_aiter():
        yield json.dumps({"id": "req1", "method": "GET", "path": "/api", "headers": {}, "body": ""})
        raise asyncio.CancelledError()
    mock_ws.__aiter__.side_effect = mock_aiter

    with patch("websockets.connect", return_value=mock_ws) as mock_connect:
        with patch.object(handler, "_handle_request", new_callable=AsyncMock) as mock_handle:
            handler.is_running = True
            try:
                await handler._run_loop()
            except asyncio.CancelledError:
                pass
            mock_connect.assert_called_once()
            mock_handle.assert_called_once()

@pytest.mark.asyncio
async def test_run_loop_reconnects_on_exception(handler):
    mock_ws = AsyncMock()
    mock_ws.__aenter__.return_value = mock_ws
    # First connection raises exception, second connection works but cancels loop
    mock_ws.__aiter__.side_effect = [Exception("WS Error"), asyncio.CancelledError()]
    
    with patch("websockets.connect", return_value=mock_ws):
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            handler.is_running = True
            try:
                await handler._run_loop()
            except asyncio.CancelledError:
                pass
            mock_sleep.assert_called_with(1)

@pytest.mark.asyncio
async def test_handle_request_success(handler):
    mock_ws = AsyncMock()
    payload = {
        "id": "req_123",
        "method": "POST",
        "path": "/webhook",
        "headers": {"Host": "relay"},
        "body": "test data"
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "text/plain"}
    mock_resp.text = "ok"

    mock_client_instance = AsyncMock()
    mock_client_instance.request.return_value = mock_resp
    
    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        await handler._handle_request(mock_ws, payload)

    mock_client_instance.request.assert_called_once_with(
        method="POST",
        url="http://localhost:8000/webhook",
        headers={},
        content="test data",
        timeout=30.0
    )
    mock_ws.send.assert_called_once()
    sent_data = json.loads(mock_ws.send.call_args[0][0])
    assert sent_data["id"] == "req_123"
    assert sent_data["status_code"] == 200
    assert sent_data["body"] == "ok"

@pytest.mark.asyncio
async def test_handle_request_exception(handler):
    mock_ws = AsyncMock()
    payload = {"id": "req_123", "path": "/bad"}

    mock_client_instance = AsyncMock()
    mock_client_instance.request.side_effect = Exception("Connection Refused")
    
    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch("httpx.AsyncClient", return_value=mock_client):
        await handler._handle_request(mock_ws, payload)

    mock_ws.send.assert_called_once()
    sent_data = json.loads(mock_ws.send.call_args[0][0])
    assert sent_data["status_code"] == 502
    assert "Connection Refused" in sent_data["body"]

def test_get_status(handler):
    status = handler.get_status()
    assert status["is_active"] is False
    assert status["daemon_id"] == "d123"
    assert status["relay_url"] == "wss://relay"
