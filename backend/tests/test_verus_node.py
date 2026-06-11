import pytest
pytestmark = pytest.mark.unit

import os
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, call
from backend.security.verus_node import VerusNodeManager

@pytest.fixture
def manager():
    return VerusNodeManager()

@pytest.mark.asyncio
async def test_is_installed_true(manager):
    with patch("pathlib.Path.exists", return_value=True):
        assert await manager.is_installed() is True

@pytest.mark.asyncio
async def test_is_installed_false(manager):
    with patch("pathlib.Path.exists", return_value=False):
        assert await manager.is_installed() is False

@pytest.mark.asyncio
async def test_provision_binary_already_installed(manager):
    with patch.object(manager, "is_installed", return_value=True):
        await manager.provision_binary()
        # Should return early, no downloads

@pytest.mark.asyncio
async def test_provision_binary_unsupported_os(manager):
    manager.os_type = "Windows"
    with patch.object(manager, "is_installed", return_value=False):
        with pytest.raises(Exception, match="Unsupported OS"):
            await manager.provision_binary()

@pytest.mark.asyncio
async def test_provision_binary_success(manager):
    manager.os_type = "Linux"
    manager.arch = "x86_64"
    
    mock_resp = MagicMock()
    mock_resp.content = b"fake data"
    mock_client_instance = AsyncMock()
    mock_client_instance.get.return_value = mock_resp
    
    mock_client = MagicMock()
    mock_client.__aenter__.return_value = mock_client_instance

    with patch.object(manager, "is_installed", return_value=False):
        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch("builtins.open", MagicMock()):
                with patch("tarfile.open") as mock_tar:
                    mock_tar_ctx = MagicMock()
                    mock_tar.return_value.__enter__.return_value = mock_tar_ctx
                    
                    # Mock directory iterdir to simulate no nested tarball
                    with patch("pathlib.Path.iterdir", return_value=[]):
                        with patch("os.remove"):
                            with patch("pathlib.Path.exists", return_value=True):
                                with patch("os.chmod"):
                                    with patch("subprocess.run"):
                                        await manager.provision_binary()
                                        mock_tar_ctx.extractall.assert_called_once()
                                        mock_client_instance.get.assert_called_once()

@pytest.mark.asyncio
async def test_generate_config_not_exists(manager):
    with patch("pathlib.Path.exists", return_value=False):
        with patch("builtins.open", MagicMock()) as mock_open:
            await manager.generate_config()
            mock_open.assert_called_once()

@pytest.mark.asyncio
async def test_generate_config_exists_no_force(manager):
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", MagicMock()) as mock_open:
            await manager.generate_config()
            mock_open.assert_not_called()

@pytest.mark.asyncio
async def test_generate_config_exists_force(manager):
    with patch("pathlib.Path.exists", return_value=True):
        with patch("builtins.open", MagicMock()) as mock_open:
            await manager.generate_config(force=True)
            mock_open.assert_called_once()

@pytest.mark.asyncio
async def test_start_already_running(manager):
    manager.process = MagicMock()
    with patch.object(manager, "provision_binary") as mock_prov:
        await manager.start()
        mock_prov.assert_not_called()

@pytest.mark.asyncio
async def test_start_success(manager):
    with patch.object(manager, "is_installed", return_value=True):
        with patch.object(manager, "generate_config", AsyncMock()) as mock_gen:
            mock_proc = AsyncMock()
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
                with patch("asyncio.create_task") as mock_task:
                    await manager.start()
                    mock_gen.assert_called_once()
                    mock_exec.assert_called_once()
                    mock_task.assert_called_once()
                    assert manager.process == mock_proc

@pytest.mark.asyncio
async def test_start_failure(manager):
    with patch.object(manager, "is_installed", return_value=True):
        with patch.object(manager, "generate_config", AsyncMock()):
            with patch("asyncio.create_subprocess_exec", side_effect=Exception("Exec failed")):
                with pytest.raises(Exception, match="Exec failed"):
                    await manager.start()

@pytest.mark.asyncio
async def test_stop(manager):
    mock_proc = AsyncMock()
    manager.process = mock_proc
    await manager.stop()
    mock_proc.terminate.assert_called_once()
    mock_proc.wait.assert_called_once()
    assert manager.process is None

@pytest.mark.asyncio
async def test_monitor_process(manager):
    manager.process = MagicMock()
    
    mock_rpc = AsyncMock()
    mock_rpc.get_info.return_value = {"blocks": 100, "longestchain": 200}
    
    async def side_effect(*args):
        # Stop process loop on first sleep
        manager.process = None
    
    with patch.dict("sys.modules", {"backend.security.verus_rpc": MagicMock(verus_rpc=mock_rpc)}):
        with patch("asyncio.sleep", AsyncMock(side_effect=side_effect)):
            await manager._monitor_process()
            assert manager._sync_status["height"] == 100
            assert manager._sync_status["percent"] == 50.0

@pytest.mark.asyncio
async def test_monitor_process_longestchain_zero(manager):
    manager.process = MagicMock()
    
    mock_rpc = AsyncMock()
    mock_rpc.get_info.return_value = {"blocks": 100, "longestchain": 0}
    
    async def side_effect(*args):
        manager.process = None
    
    with patch.dict("sys.modules", {"backend.security.verus_rpc": MagicMock(verus_rpc=mock_rpc)}):
        with patch("asyncio.sleep", AsyncMock(side_effect=side_effect)):
            await manager._monitor_process()
            assert manager._sync_status["percent"] == 100.0

def test_get_status(manager):
    status = manager.get_status()
    assert "active" in status
    assert "pid" in status
    assert "sync" in status
    assert "directories" in status
