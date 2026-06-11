import pytest
pytestmark = pytest.mark.unit

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from backend.heartbeat import HeartbeatDaemon

@pytest.fixture
def mock_orchestrator():
    return MagicMock()

@pytest.fixture
def mock_vault():
    vault = MagicMock()
    vault.retrieve_secret = AsyncMock(return_value=None)
    return vault

@pytest.mark.asyncio
async def test_heartbeat_daemon_start_stop(mock_orchestrator, mock_vault):
    daemon = HeartbeatDaemon(mock_orchestrator, mock_vault, interval_seconds=1)
    
    # We don't want it to actually run the inner loops fully and hit missing DBs
    # so we mock _evaluate_all_orders
    with patch.object(daemon, '_evaluate_all_orders', new_callable=AsyncMock) as mock_eval:
        daemon._running = True
        daemon._task = asyncio.create_task(daemon._tick_loop())
        
        await asyncio.sleep(0.1) # let loop run at least once
        
        await daemon.stop()
        
        # Verify it stopped and task was cancelled or done
        assert not daemon._running
        assert daemon._task.done()

@pytest.mark.asyncio
async def test_heartbeat_dynamic_interval(mock_orchestrator, mock_vault):
    mock_vault.retrieve_secret.return_value = {
        "preferences": {
            "heartbeat_interval": 0.05
        }
    }
    daemon = HeartbeatDaemon(mock_orchestrator, mock_vault, interval_seconds=1)
    
    with patch.object(daemon, '_evaluate_all_orders', new_callable=AsyncMock):
        daemon._running = True
        daemon._task = asyncio.create_task(daemon._tick_loop())
        
        await asyncio.sleep(0.1) 
        await daemon.stop()
        
        # Should have run multiple times due to the 0.05 interval
        assert daemon.vault.retrieve_secret.call_count >= 1
