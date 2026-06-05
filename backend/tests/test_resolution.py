import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from backend.security.resolution import SecurityResolutionManager
from backend.security.exceptions import SecurityException

@pytest.fixture
def manager():
    return SecurityResolutionManager()

@pytest.fixture
def exc():
    return SecurityException("test", "TEST", {"meta": "data"})

@pytest.mark.asyncio
@patch("backend.services.ws_gw", new_callable=AsyncMock)
async def test_request_and_provide_resolution(mock_ws, manager, exc):
    task = asyncio.create_task(manager.request_resolution("task1", exc))
    
    # Let it run to block
    await asyncio.sleep(0.01)
    
    # Broadcast called
    mock_ws.broadcast_event.assert_called_once_with(
        event_name="security.resolution_required",
        data={
            "task_id": "task1",
            "message": "test",
            "exception_type": "TEST",
            "metadata": {"meta": "data"}
        }
    )
    
    # Now provide resolution
    res = manager.provide_resolution("task1", "APPROVED")
    assert res is True
    
    # Task should finish and return resolution
    final_res = await task
    assert final_res == "APPROVED"
    assert "task1" not in manager._pending_resolutions

def test_provide_resolution_not_found(manager):
    res = manager.provide_resolution("unknown", "APPROVED")
    assert res is False

@pytest.mark.asyncio
@patch("backend.services.ws_gw", None)
async def test_request_resolution_no_ws(manager, exc):
    # Should work without failing if ws_gw is None
    task = asyncio.create_task(manager.request_resolution("task2", exc))
    await asyncio.sleep(0.01)
    res = manager.provide_resolution("task2", "REJECTED")
    assert res is True
    assert await task == "REJECTED"
