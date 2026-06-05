import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from backend.updater import UpdateManager

@pytest.fixture
def updater():
    return UpdateManager(current_version="1.0.0")

@pytest.mark.asyncio
async def test_start_stop(updater):
    # Short circuit the loop so it doesn't run forever during test
    updater._monitor_loop = AsyncMock()
    
    await updater.start()
    assert updater.checking_task is not None
    assert not updater.checking_task.done()
    
    await updater.stop()
    assert updater.checking_task.done()

@pytest.mark.asyncio
async def test_check_for_updates_available(updater):
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"tag_name": "v1.1.0"}
        
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock(return_value=mock_resp)
        
        res = await updater.check_for_updates()
        
        assert res is True
        assert updater.update_available is True
        assert updater.latest_version == "1.1.0"
        assert updater._last_check is not None

@pytest.mark.asyncio
async def test_check_for_updates_not_available(updater):
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"tag_name": "v1.0.0"}
        
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get = AsyncMock(return_value=mock_resp)
        
        res = await updater.check_for_updates()
        
        assert res is False
        assert updater.update_available is False

@pytest.mark.asyncio
async def test_check_for_updates_network_error(updater):
    with patch("httpx.AsyncClient") as mock_client:
        mock_instance = mock_client.return_value.__aenter__.return_value
        mock_instance.get.side_effect = Exception("Network timeout")
        
        res = await updater.check_for_updates()
        
        assert res is False

def test_is_newer(updater):
    assert updater._is_newer("1.1.0", "1.0.0") is True
    assert updater._is_newer("1.0.0", "1.1.0") is False
    assert updater._is_newer("1.0.0", "1.0.0") is False
    assert updater._is_newer("2.0.0", "1.9.9") is True
    
    # Fallback path
    assert updater._is_newer("v1-alpha", "v1-beta") is True

@pytest.mark.asyncio
async def test_updater_monitor_loop(updater):
    with patch.object(updater, "check_for_updates", new_callable=AsyncMock), \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        
        # Make sleep raise an exception to break the infinite loop
        mock_sleep.side_effect = Exception("break loop")
        
        try:
            await updater._monitor_loop()
        except Exception as e:
            assert str(e) == "break loop"
        
        mock_sleep.assert_called_once_with(4 * 3600)

@pytest.mark.asyncio
async def test_perform_update(updater):
    res = await updater.perform_update()
    assert res["ok"] is False
    assert "In-place updates are disabled" in res["error"]

def test_get_status(updater):
    status = updater.get_status()
    assert status["current_version"] == "1.0.0"
    assert status["latest_version"] is None
    assert status["update_available"] is False
    assert status["last_check"] is None
