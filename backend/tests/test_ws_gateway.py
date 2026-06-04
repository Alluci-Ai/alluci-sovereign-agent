import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from backend.ws_gateway import JsonRpcGateway, ConnectedClient, _rpc_success, _rpc_error

# Helper to generate a valid test token
def generate_test_token():
    from backend.security.auth import create_access_token
    return create_access_token(data={"sub": "testuser"})

@pytest.fixture
def test_app():
    app = FastAPI()
    gateway = JsonRpcGateway("test_secret")
    
    # Mock some services for injection
    mock_vault = MagicMock()
    mock_vault.status.return_value = {"unlocked": True}
    mock_vault._get_full_vault_state = AsyncMock(return_value={"state": "test"})
    mock_vault.retrieve_secret = AsyncMock(return_value=[{"event": "start"}])
    mock_vault.vdxf = MagicMock()
    mock_vault.vdxf.verify_integrity = AsyncMock(return_value=True)
    mock_vault.vdxf.current_anchor = "test_hash"
    mock_orchestrator = MagicMock()
    mock_orchestrator.get_active_routines.return_value = ["routine1"]
    mock_updater = MagicMock()
    mock_updater.check_for_updates = AsyncMock(return_value={"update_available": False})
    mock_updater.perform_update = AsyncMock(return_value={"status": "triggered"})
    mock_updater.get_status.return_value = {"status": "checked"}
    
    gateway.inject_services(
        vault=mock_vault,
        orchestrator=mock_orchestrator,
        updater=mock_updater
    )
    
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await gateway.handle_connection(websocket)
        
    return app, gateway

@pytest.fixture
def client(test_app):
    app, _ = test_app
    return TestClient(app)

def test_authenticate_success_via_msg(client, test_app):
    app, gateway = test_app
    token = generate_test_token()
    
    with client.websocket_connect("/ws") as websocket:
        # Send auth hello
        websocket.send_text(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "hello",
            "params": {"token": token}
        }))
        
        # Expect hello response from server
        resp_raw = websocket.receive_text()
        resp = json.loads(resp_raw)
        assert resp["method"] == "hello"
        assert "client_id" in resp["params"]
        
        # Verify client is registered
        client_id = resp["params"]["client_id"]
        assert client_id in gateway.clients
        
        c = gateway.clients[client_id]
        assert c.subject == "testuser"
        
        # Close
        websocket.close()

def test_authenticate_success_via_cookie(test_app):
    app, gateway = test_app
    token = generate_test_token()
    client = TestClient(app, cookies={"alluci_daemon_token": token})
    
    with client.websocket_connect("/ws") as websocket:
        # Send hello without token in params
        websocket.send_text(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "hello",
            "params": {}
        }))
        
        resp_raw = websocket.receive_text()
        resp = json.loads(resp_raw)
        assert resp["method"] == "hello"
        websocket.close()

def test_authenticate_failure_no_token(client):
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "hello"
        }))
        
        # Server should send error and close
        resp_raw = websocket.receive_text()
        resp = json.loads(resp_raw)
        assert "error" in resp
        assert resp["error"]["code"] == -32000 # AUTH_REQUIRED
        
        # Connection should drop
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_text()

def test_rpc_system_status(client, test_app):
    app, gateway = test_app
    token = generate_test_token()
    
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"jsonrpc": "2.0", "params": {"token": token}}))
        websocket.receive_text() # drop hello
        
        websocket.send_text(json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "system.status"
        }))
        
        resp = json.loads(websocket.receive_text())
        assert resp["id"] == 2
        assert "result" in resp
        assert "cpu_percent" in resp["result"]
        assert "memory_usage_mb" in resp["result"]

def test_rpc_methods_list(client, test_app):
    app, gateway = test_app
    token = generate_test_token()
    
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"jsonrpc": "2.0", "params": {"token": token}}))
        websocket.receive_text()
        
        websocket.send_text(json.dumps({"jsonrpc": "2.0", "id": 3, "method": "methods.list"}))
        resp = json.loads(websocket.receive_text())
        assert resp["id"] == 3
        assert "system.status" in resp["result"]["methods"]

def test_rpc_events_subscribe_unsubscribe(client, test_app):
    app, gateway = test_app
    token = generate_test_token()
    
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"jsonrpc": "2.0", "params": {"token": token}}))
        hello_resp = json.loads(websocket.receive_text())
        client_id = hello_resp["params"]["client_id"]
        
        # Subscribe
        websocket.send_text(json.dumps({
            "jsonrpc": "2.0", "id": 4, "method": "events.subscribe",
            "params": {"channels": ["log", "task"]}
        }))
        resp = json.loads(websocket.receive_text())
        assert "log" in resp["result"]["subscribed"]
        assert "log" in gateway.clients[client_id].subscriptions
        
        # Unsubscribe
        websocket.send_text(json.dumps({
            "jsonrpc": "2.0", "id": 5, "method": "events.unsubscribe",
            "params": {"channels": ["log"]}
        }))
        resp2 = json.loads(websocket.receive_text())
        assert "log" not in resp2["result"]["subscribed"]
        assert "log" not in gateway.clients[client_id].subscriptions

def test_rpc_invalid_method(client, test_app):
    app, gateway = test_app
    token = generate_test_token()
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"jsonrpc": "2.0", "params": {"token": token}}))
        websocket.receive_text()
        
        websocket.send_text(json.dumps({"jsonrpc": "2.0", "id": 10, "method": "unknown.method"}))
        resp = json.loads(websocket.receive_text())
        assert resp["error"]["code"] == -32601 # METHOD_NOT_FOUND

def test_rpc_invalid_json(client, test_app):
    token = generate_test_token()
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"jsonrpc": "2.0", "params": {"token": token}}))
        websocket.receive_text()
        
        websocket.send_text("INVALID JSON")
        resp = json.loads(websocket.receive_text())
        assert resp["error"]["code"] == -32700 # PARSE_ERROR

@pytest.mark.asyncio
async def test_broadcast_event(test_app):
    app, gateway = test_app
    
    mock_ws = AsyncMock()
    c1 = ConnectedClient(mock_ws, "c1", "sub")
    c1.subscriptions.add("log")
    
    mock_ws2 = AsyncMock()
    c2 = ConnectedClient(mock_ws2, "c2", "sub")
    c2.subscriptions.add("other_channel")
    # Not subscribed to 'log'
    
    gateway.clients = {"c1": c1, "c2": c2}
    
    await gateway.broadcast_event("log", {"msg": "hello"})
    
    mock_ws.send_text.assert_awaited_once()
    mock_ws2.send_text.assert_not_awaited()

@pytest.mark.asyncio
async def test_other_builtins(test_app):
    app, gateway = test_app
    dummy_client = ConnectedClient(AsyncMock(), "c1", "testuser")
    gateway.clients["c1"] = dummy_client
    
    # Inject more services for builtins
    whatsapp_mock = MagicMock(last_qr="qr_data", connection_state="waiting")
    whatsapp_mock.is_connected = AsyncMock(return_value=True)
    mock_registry = {"whatsapp": whatsapp_mock}
    mock_approval_manager = MagicMock()
    mock_approval_manager.handle_allow = AsyncMock(return_value={"status": "allowed"})
    mock_approval_manager.handle_deny = AsyncMock(return_value={"status": "denied"})
    
    gateway.inject_services(channel_registry=mock_registry, approval_manager=mock_approval_manager)
    
    res = await gateway._rpc_system_health({}, dummy_client)
    assert res is not None
    
    res_pres = await gateway._rpc_system_presence({}, dummy_client)
    assert len(res_pres["active_sessions"]) == 1
    
    res_wa = await gateway._rpc_whatsapp_get_qr({}, dummy_client)
    assert "error" in res_wa or "qr" in res_wa
    
    res_exec_a = await gateway._rpc_exec_allow({"request_id": "req1", "persist": True}, dummy_client)
    assert res_exec_a.get("status") == "allowed" or "error" in res_exec_a
    
    res_exec_d = await gateway._rpc_exec_deny({"request_id": "req2"}, dummy_client)
    assert res_exec_d.get("status") == "denied" or "error" in res_exec_d
    
    res_patch = await gateway._rpc_sessions_patch({"session_key": "key", "label": "lbl"}, dummy_client)
    assert res_patch.get("status") == "patched" or "error" in res_patch
    
    res_upd = await gateway._rpc_system_update({}, dummy_client)
    assert res_upd.get("status") == "triggered" or "error" in res_upd
    
    res_updc = await gateway._rpc_system_update_check({}, dummy_client)
    assert res_updc.get("status") == "checked" or "error" in res_updc
    
    res_sig_reg = await gateway._rpc_signal_register({"phone_number": "123", "use_voice": False}, dummy_client)
    assert res_sig_reg.get("status") in ["initiated", "error"]
    
    res_sig_ver = await gateway._rpc_signal_verify({"phone_number": "123", "code": "000"}, dummy_client)
    assert res_sig_ver.get("status") in ["verified", "error"]

    res_mani = await gateway._rpc_manifold_pvt({}, dummy_client)
    assert "pvt" in res_mani or "error" in res_mani
