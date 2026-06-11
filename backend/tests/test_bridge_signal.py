import pytest
pytestmark = pytest.mark.unit

import asyncio
import json
import os
from unittest.mock import AsyncMock, patch, MagicMock, ANY

from backend.bridges.signal import SignalBridge

@pytest.fixture
def mock_vault():
    vault = MagicMock()
    return vault

@pytest.fixture
def signal_bridge(mock_vault):
    bridge = SignalBridge("test_bridge", "/tmp", mock_vault)
    # mock settings
    with patch("backend.config.settings") as mock_settings:
        mock_settings.SIGNAL_CLI_PATH = "signal-cli"
        mock_settings.SIGNAL_SOCKET_PATH = "/tmp/signal-cli.sock"
        yield bridge

@pytest.mark.asyncio
async def test_signal_connect_missing_phone(signal_bridge):
    res = await signal_bridge.connect({})
    assert res is False
    assert signal_bridge.last_error == "phone_number required for Signal bridge."

@pytest.mark.asyncio
async def test_signal_connect_daemon_success(signal_bridge):
    credentials = {"phone_number": "+1234567890"}
    
    with patch.object(signal_bridge, "_start_daemon", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = True
        with patch("backend.bridges.signal.asyncio.create_task") as mock_create_task:
            res = await signal_bridge.connect(credentials)
            
            assert res is True
            assert signal_bridge._use_daemon is True
            mock_create_task.assert_called()

@pytest.mark.asyncio
async def test_signal_connect_daemon_fallback(signal_bridge):
    credentials = {"phone_number": "+1234567890"}
    
    with patch.object(signal_bridge, "_start_daemon", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = False
        with patch("backend.bridges.signal.asyncio.create_task") as mock_create_task:
            res = await signal_bridge.connect(credentials)
            
            assert res is True
            assert signal_bridge._use_daemon is False
            mock_create_task.assert_called()

@pytest.mark.asyncio
async def test_signal_start_daemon_success(signal_bridge):
    signal_bridge.phone_number = "+123"
    
    with patch("backend.bridges.signal.os.path.exists", side_effect=[False, True]):
        with patch("backend.bridges.signal.asyncio.create_subprocess_exec") as mock_exec:
            proc = AsyncMock()
            proc.stderr = AsyncMock()
            proc.stderr.__aiter__.return_value = []
            mock_exec.return_value = proc
            
            with patch("backend.bridges.signal.asyncio.sleep", new_callable=AsyncMock):
                res = await signal_bridge._start_daemon()
                assert res is True

@pytest.mark.asyncio
async def test_signal_start_daemon_timeout(signal_bridge):
    signal_bridge.phone_number = "+123"
    
    with patch("backend.bridges.signal.os.path.exists", return_value=False):
        with patch("backend.bridges.signal.asyncio.create_subprocess_exec") as mock_exec:
            proc = MagicMock()
            proc.terminate = MagicMock()
            mock_exec.return_value = proc
            
            with patch("backend.bridges.signal.asyncio.sleep", new_callable=AsyncMock):
                res = await signal_bridge._start_daemon()
                assert res is False
                proc.terminate.assert_called_once()

@pytest.mark.asyncio
async def test_signal_rpc_call_success(signal_bridge):
    with patch("backend.bridges.signal.asyncio.open_unix_connection") as mock_conn:
        reader = AsyncMock()
        writer = AsyncMock()
        mock_conn.return_value = (reader, writer)
        
        reader.readline = AsyncMock(return_value=b'{"result": {"ok": true}}\n')
        
        res = await signal_bridge._rpc_call("test", {"a": 1})
        assert res == {"ok": True}
        writer.write.assert_called_once()

@pytest.mark.asyncio
async def test_signal_rpc_call_error(signal_bridge):
    with patch("backend.bridges.signal.asyncio.open_unix_connection") as mock_conn:
        reader = AsyncMock()
        writer = AsyncMock()
        mock_conn.return_value = (reader, writer)
        
        reader.readline = AsyncMock(return_value=b'{"error": {"message": "failed"}}\n')
        
        with pytest.raises(RuntimeError):
            await signal_bridge._rpc_call("test", {"a": 1})

@pytest.mark.asyncio
async def test_signal_handle_daemon_event(signal_bridge):
    event = {
        "method": "receive",
        "params": {
            "envelope": {
                "sourceNumber": "+123",
                "timestamp": 12345,
                "dataMessage": {
                    "message": "hello",
                    "groupInfo": {"groupId": "grp1"}
                }
            }
        }
    }
    
    with patch.object(signal_bridge, "_dispatch_inbound", new_callable=AsyncMock) as mock_dispatch:
        await signal_bridge._handle_daemon_event(event)
        
        assert len(signal_bridge._message_buffer) == 1
        msg = signal_bridge._message_buffer[0]
        assert msg["body"] == "hello"
        assert msg["from"] == "+123"
        assert msg["group_id"] == "grp1"
        mock_dispatch.assert_called_once_with(msg)

@pytest.mark.asyncio
async def test_signal_send_daemon(signal_bridge):
    signal_bridge.is_connected = True
    signal_bridge._use_daemon = True
    signal_bridge.phone_number = "+999"
    
    with patch.object(signal_bridge, "_rpc_call", new_callable=AsyncMock) as mock_rpc:
        mock_rpc.return_value = {"timestamp": 111}
        
        res = await signal_bridge.send("+123", "hello test")
        assert res["status"] == "success"
        mock_rpc.assert_called_once()

@pytest.mark.asyncio
async def test_signal_send_subprocess(signal_bridge):
    signal_bridge.is_connected = True
    signal_bridge._use_daemon = False
    signal_bridge.phone_number = "+999"
    
    with patch("backend.bridges.signal.asyncio.create_subprocess_exec") as mock_exec:
        proc = AsyncMock()
        proc.communicate.return_value = (b"sent", b"")
        proc.returncode = 0
        mock_exec.return_value = proc
        
        res = await signal_bridge.send("+123", "hello process")
        assert res["status"] == "success"

@pytest.mark.asyncio
async def test_signal_get_link_qr(signal_bridge):
    with patch("backend.bridges.signal.asyncio.create_subprocess_exec") as mock_exec:
        proc = AsyncMock()
        proc.communicate.return_value = (b"tsdevice://1234\n", b"")
        mock_exec.return_value = proc
        
        res = await signal_bridge.get_link_qr()
        assert res == "tsdevice://1234"

@pytest.mark.asyncio
async def test_signal_disconnect(signal_bridge):
    signal_bridge.is_connected = True
    
    mock_task = asyncio.Future()
    signal_bridge._listener_task = mock_task
    
    proc = MagicMock()
    signal_bridge._daemon_process = proc
    
    with patch("backend.bridges.signal.asyncio.wait_for", new_callable=AsyncMock):
        await signal_bridge.disconnect()
    
    assert signal_bridge.is_connected is False
    assert mock_task.cancelled()
    proc.terminate.assert_called_once()

@pytest.mark.asyncio
async def test_signal_health(signal_bridge):
    signal_bridge.is_connected = True
    signal_bridge._use_daemon = True
    proc = MagicMock()
    proc.pid = 999
    proc.returncode = None
    signal_bridge._daemon_process = proc
    
    with patch("backend.bridges.signal.os.path.exists", return_value=True):
        assert await signal_bridge.validate_integrity() is True
        
    health = signal_bridge.get_health()
    assert health["mode"] == "daemon"
    assert health["daemon_pid"] == 999
