import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.heartbeat import (
    _load_orders_from_manifest,
    _probe_url_fetch,
    _probe_memory_pattern,
    _probe_system_health,
    _probe_bridge_silence,
    _run_action,
    _action_notify_ws,
    _action_notify_bridge,
    _action_execute_objective,
    _action_evaluate_goal,
    _action_log_only,
    _action_pcl_signal
)

def test_load_orders_exception():
    res = _load_orders_from_manifest({"heartbeat": "[{\"test\"}]"}) # invalid json
    assert res == []
    
@pytest.mark.asyncio
async def test_probe_url_fetch_exception():
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = Exception("HTTP err")
        res, _ = await _probe_url_fetch({"url": "http://google.com"})
        assert res is False
        
@pytest.mark.asyncio
async def test_probe_memory_pattern_exception():
    with patch("backend.services.hlsm_manager", AsyncMock()) as mock_hlsm:
        mock_hlsm.search.side_effect = Exception("Mem err")
        res, _ = await _probe_memory_pattern({"query": "q"})
        assert res is False

@pytest.mark.asyncio
async def test_probe_system_health_exception():
    with patch("backend.heartbeat.Session", side_effect=Exception("DB err")):
        res, _ = await _probe_system_health({})
        assert res is False
        
@pytest.mark.asyncio
async def test_probe_bridge_silence_exceptions():
    with patch("backend.services.channel_registry", None):
        res, _ = await _probe_bridge_silence({"bridge_id": "discord", "silence_hours": 1})
        assert res is False
        
    with patch("backend.services.channel_registry", {"discord": "not an adapter"}):
        res, _ = await _probe_bridge_silence({"bridge_id": "discord", "silence_hours": 1})
        assert res is False

@pytest.mark.asyncio
async def test_action_notify_ws_exceptions():
    mock_ws = AsyncMock()
    mock_ws.broadcast_event.side_effect = Exception("WS err")
    res, _ = await _action_notify_ws({}, "d", {}, mock_ws)
    assert res == "failed"
    
@pytest.mark.asyncio
async def test_action_notify_bridge_exceptions():
    with patch("backend.services.channel_registry", {"discord": AsyncMock(send_message=AsyncMock(side_effect=Exception("br err")))}):
        res, _ = await _action_notify_bridge({"bridge_id": "discord", "recipient": "r"}, "d", {})
        assert res == "failed"

@pytest.mark.asyncio
async def test_action_execute_objective_exceptions():
    mock_orch = AsyncMock()
    mock_orch.execute_objective.side_effect = Exception("Orch err")
    res, _ = await _action_execute_objective({}, "d", {}, None, mock_orch)
    assert res == "failed"
    
@pytest.mark.asyncio
async def test_action_evaluate_goal_exceptions():
    with patch("backend.services.goal_engine", AsyncMock()) as mock_ge:
        mock_ge.evaluate_progress.side_effect = Exception("GE err")
        res, _ = await _action_evaluate_goal({"goal_id": 1})
        assert res == "failed"
        
@pytest.mark.asyncio
async def test_action_log_only_exceptions():
    mock_hlsm = AsyncMock()
    mock_hlsm.store.side_effect = Exception("HLSM err")
    res, _ = await _action_log_only("d", {}, mock_hlsm)
    assert res == "failed"
    
@pytest.mark.asyncio
async def test_action_pcl_signal_exceptions():
    mock_hlsm = AsyncMock()
    mock_hlsm.store.side_effect = Exception("HLSM err")
    res, _ = await _action_pcl_signal({}, "d", {}, None, mock_hlsm)
    assert res == "failed"
