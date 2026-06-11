import pytest
pytestmark = pytest.mark.unit

import os
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from backend.routers.websockets import router
from backend import services
from backend.config import settings

app = FastAPI()
app.include_router(router)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_origins():
    settings.ALLOWED_ORIGINS = ["http://localhost"]
    yield

def test_sovereign_websocket_no_origin():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/sovereign") as websocket:
            websocket.receive_text()

def test_sovereign_websocket_bad_origin():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/sovereign", headers={"Origin": "http://bad"}) as websocket:
            websocket.receive_text()

def test_sovereign_websocket_good_origin_no_token():
    with pytest.raises(Exception):
        with patch("asyncio.wait_for") as mock_wait:
            mock_wait.side_effect = Exception("timeout")
            with client.websocket_connect("/ws/sovereign", headers={"Origin": "http://localhost"}) as websocket:
                websocket.receive_text()

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_sovereign_websocket_good_origin_cookie_token(mock_auth):
    mock_auth.return_value = "token"
    services.ws_gw = AsyncMock()
    with client.websocket_connect("/ws/sovereign", headers={"Origin": "http://localhost"}) as websocket:
        services.ws_gw.handle_connection.assert_called_once()

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_sovereign_websocket_first_message_auth(mock_auth):
    mock_auth.return_value = None
    with patch("backend.routers.websockets.verify_token"):
        services.ws_gw = AsyncMock()
        with client.websocket_connect("/ws/sovereign", headers={"Origin": "http://localhost"}) as websocket:
            websocket.send_json({"type": "auth", "token": "msg_token"})
        services.ws_gw.handle_connection.assert_called_once()

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_sovereign_websocket_first_message_not_auth(mock_auth):
    mock_auth.return_value = None
    with client.websocket_connect("/ws/sovereign", headers={"Origin": "http://localhost"}) as websocket:
        websocket.send_json({"type": "not_auth"})

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_sovereign_websocket_ws_gw_not_ready(mock_auth):
    mock_auth.return_value = "token"
    services.ws_gw = None
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/sovereign", headers={"Origin": "http://localhost"}) as websocket:
            websocket.receive_text()

def test_admin_websocket_no_origin():
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/admin") as websocket:
            websocket.receive_text()

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_admin_websocket_success(mock_auth):
    mock_auth.return_value = "token"
    services.ws_gw = AsyncMock()
    with client.websocket_connect("/ws/admin", headers={"Origin": "http://localhost"}) as websocket:
        pass

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_admin_websocket_not_ready(mock_auth):
    mock_auth.return_value = "token"
    services.ws_gw = None
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/admin", headers={"Origin": "http://localhost"}) as websocket:
            websocket.receive_text()

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_log_stream_success(mock_auth):
    mock_auth.return_value = "token"
    mock_handler = AsyncMock()
    with patch.dict("sys.modules", {"backend.log_streamer": MagicMock(log_stream_handler=mock_handler)}):
        with client.websocket_connect("/api/logs/stream", headers={"Origin": "http://localhost"}) as websocket:
            pass

def test_log_stream_no_origin():
    with pytest.raises(Exception):
        with client.websocket_connect("/api/logs/stream") as websocket:
            websocket.receive_text()

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_log_stream_first_message_auth(mock_auth):
    mock_auth.return_value = None
    with patch("backend.routers.websockets.verify_token"):
        mock_handler = AsyncMock()
        with patch.dict("sys.modules", {"backend.log_streamer": MagicMock(log_stream_handler=mock_handler)}):
            with client.websocket_connect("/api/logs/stream", headers={"Origin": "http://localhost"}) as websocket:
                websocket.send_json({"type": "auth", "token": "msg_token"})
            mock_handler.handle.assert_called_once()

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_log_stream_first_message_not_auth(mock_auth):
    mock_auth.return_value = None
    with client.websocket_connect("/api/logs/stream", headers={"Origin": "http://localhost"}) as websocket:
        websocket.send_json({"type": "not_auth"})

def test_verify_origin_public_url():
    with patch.dict(os.environ, {"DAEMON_PUBLIC_URL": "http://daemon.test"}):
        with pytest.raises(Exception): # no auth, but origin is allowed, so it expects message or cookie
            with client.websocket_connect("/ws/admin", headers={"Origin": "http://daemon.test"}) as websocket:
                websocket.receive_text()

@patch("backend.routers.websockets.verify_token")
def test_auth_invalid_jwt(mock_verify):
    from jose import JWTError
    mock_verify.side_effect = JWTError("invalid")
    with pytest.raises(Exception): 
        with client.websocket_connect("/ws/sovereign?token=invalid_token", headers={"Origin": "http://localhost"}) as websocket:
            websocket.receive_text()

@patch("backend.routers.websockets.authenticate_ws_handshake")
def test_log_stream_auth_timeout(mock_auth):
    mock_auth.return_value = None
    with pytest.raises(Exception):
        with patch("asyncio.wait_for") as mock_wait:
            mock_wait.side_effect = Exception("timeout")
            with client.websocket_connect("/api/logs/stream", headers={"Origin": "http://localhost"}) as websocket:
                websocket.receive_text()

@patch("backend.routers.websockets.verify_token")
def test_auth_valid_jwt(mock_verify):
    mock_verify.return_value = {"sub": "123"}
    services.ws_gw = AsyncMock()
    with client.websocket_connect("/ws/sovereign?token=valid_token", headers={"Origin": "http://localhost"}) as websocket:
        services.ws_gw.handle_connection.assert_called_once()
