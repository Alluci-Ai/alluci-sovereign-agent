import pytest
pytestmark = pytest.mark.unit

import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

from backend.heartbeat import (
    HeartbeatDaemon,
    _run_probe,
    _run_action,
    _parse_legacy_markdown,
    _load_orders_from_manifest,
    execute_standing_order
)

@pytest.mark.asyncio
async def test_run_probe_dispatcher(tmp_path):
    # Test all branches in _run_probe
    f = tmp_path / "test.txt"
    f.write_text("hello")
    fired, _ = await _run_probe("file_watch", {"path": str(f)}, None)
    assert fired is True
    
    t = tmp_path / "tasks.md"
    t.write_text("- [ ] task (due: 2020-01-01)")
    fired, _ = await _run_probe("task_deadline", {"path": str(t)}, None)
    assert fired is True
    
    with patch("backend.services.goal_engine", AsyncMock()) as mock_ge:
        mock_ge.get_goal.return_value = MagicMock(metric_current=0, metric_target=100, title="g")
        fired, _ = await _run_probe("goal_progress", {"goal_id": 1}, None)
        assert fired is True
        
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.text = "hello"
        mock_resp.status_code = 200
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_resp
        fired, _ = await _run_probe("url_fetch", {"url": "http://x"}, None)
        assert fired is True

    with patch("backend.services.hlsm_manager", AsyncMock()) as mock_hlsm:
        mock_hlsm.search.return_value = ["a", "b"]
        fired, _ = await _run_probe("memory_pattern", {"query": "x"}, None)
        assert fired is True

    from backend.database import engine
    from sqlmodel import Session, SQLModel
    SQLModel.metadata.create_all(engine)
    fired, _ = await _run_probe("system_health", {"failure_threshold": 0}, None)
    assert fired is True
    
    with patch("backend.services.channel_registry", {"br": MagicMock(last_inbound_at=1, last_outbound_at=None, last_inbound_sender="s")}):
        fired, _ = await _run_probe("bridge_silence", {"bridge_id": "br", "silence_hours": -1}, None)
        assert fired is True
        
    fired, _ = await _run_probe("cron_expression", {}, None)
    assert fired is True
    
    fired, _ = await _run_probe("unknown", {}, None)
    assert fired is False
    
    with patch("backend.heartbeat._probe_file_watch", side_effect=Exception("boom")):
        fired, _ = await _run_probe("file_watch", {}, None)
        assert fired is False

@pytest.mark.asyncio
async def test_run_action_dispatcher():
    mock_ws = AsyncMock()
    mock_orch = AsyncMock()
    mock_orch.execute_objective.return_value = {"status": "success"}
    mock_hlsm = AsyncMock()
    mock_hlsm.store.return_value = "id"
    
    order = {"id": "1", "label": "L"}
    
    out, _ = await _run_action("notify_ws", {}, "p", order, None, ws_gateway=mock_ws)
    assert out == "success"
    
    with patch("backend.services.channel_registry", {"br": AsyncMock(send_message=AsyncMock(return_value={"status": "success"}))}):
        out, _ = await _run_action("notify_bridge", {"bridge_id": "br"}, "p", order, None)
        assert out == "success"
        
    out, _ = await _run_action("execute_objective", {}, "p", order, None, orchestrator=mock_orch)
    assert out == "success"
    
    with patch("backend.services.goal_engine", AsyncMock()) as mock_ge:
        mock_ge.evaluate_progress.return_value = "ok"
        out, _ = await _run_action("evaluate_goal", {"goal_id": 1}, "p", order, None)
        assert out == "success"
        
    out, _ = await _run_action("log_only", {}, "p", order, None, hlsm_manager=mock_hlsm)
    assert out == "success"
    
    out, _ = await _run_action("pcl_signal", {}, "p", order, None, hlsm_manager=mock_hlsm)
    assert out == "success"
    
    out, _ = await _run_action("unknown", {}, "p", order, None)
    assert out == "skipped"

    with patch("backend.heartbeat._action_notify_ws", side_effect=Exception("boom")):
        out, _ = await _run_action("notify_ws", {}, "p", order, None)
        assert out == "failed"

def test_legacy_markdown_empty_label():
    res = _parse_legacy_markdown("- [x]  \n- [ ]")
    assert len(res) == 0

def test_load_orders_json_array_non_dict():
    res = _load_orders_from_manifest({"heartbeat": "[1, 2, {\"active\": true}]"})
    assert len(res) == 1

def test_load_orders_json_array_invalid():
    res = _load_orders_from_manifest({"heartbeat": "[invalid"})
    assert len(res) == 0

def test_load_orders_list():
    res = _load_orders_from_manifest({"heartbeat": [{"active": True}, 1]})
    assert len(res) == 1

@pytest.mark.asyncio
async def test_execute_standing_order_network():
    res = await execute_standing_order("http://google.com [NETWORK_OK]")
    assert res is None
    
    res2 = await execute_standing_order("http://google.com without ok")
    assert "Blocked" in str(res2)

