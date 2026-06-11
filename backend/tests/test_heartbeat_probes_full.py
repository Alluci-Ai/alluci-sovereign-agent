import pytest
pytestmark = pytest.mark.unit

import os
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

from backend.heartbeat import (
    _probe_file_watch, _probe_task_deadline, _probe_goal_progress,
    _probe_url_fetch, _probe_memory_pattern, _probe_system_health,
    _probe_bridge_silence
)

@pytest.mark.asyncio
async def test_probe_file_watch_dir(tmp_path):
    d = tmp_path / "dir"
    d.mkdir()
    (d / "f1.txt").write_text("1")
    fired, _ = await _probe_file_watch({"path": str(d)})
    assert fired is True

@pytest.mark.asyncio
async def test_probe_url_fetch_full():
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = MagicMock()
        mock_resp.text = "hello world"
        mock_resp.status_code = 200
        mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_resp)
        
        # Keyword fail
        fired, _ = await _probe_url_fetch({"url": "http://x", "keyword": "notfound"})
        assert fired is False
        
        # Check change first time
        fired, _ = await _probe_url_fetch({"url": "http://x", "check_change": True})
        assert fired is True
        
        # Check change second time
        fired, _ = await _probe_url_fetch({"url": "http://x", "check_change": True})
        assert fired is False

@pytest.mark.asyncio
async def test_probe_goal_progress_fail():
    with patch("backend.services.goal_engine", AsyncMock()) as mock_ge:
        mock_ge.get_goal.return_value = None
        fired, _ = await _probe_goal_progress({"goal_id": 1})
        assert fired is False
        
        mock_ge.get_goal.return_value = MagicMock(metric_current=100, metric_target=100, title="g")
        fired, _ = await _probe_goal_progress({"goal_id": 1, "threshold_pct": 50})
        assert fired is False

@pytest.mark.asyncio
async def test_probe_memory_pattern_fail():
    with patch("backend.services.hlsm_manager", AsyncMock()) as mock_hlsm:
        mock_hlsm.search.return_value = ["a"]
        fired, _ = await _probe_memory_pattern({"query": "x", "min_occurrences": 5})
        assert fired is False

@pytest.mark.asyncio
async def test_probe_system_health_fail():
    from backend.database import engine
    from sqlmodel import Session, SQLModel
    SQLModel.metadata.create_all(engine)
    fired, _ = await _probe_system_health({"failure_threshold": 100})
    assert fired is False

@pytest.mark.asyncio
async def test_probe_bridge_silence_fail():
    with patch("backend.services.channel_registry", {"br": MagicMock(last_inbound_at=1, last_outbound_at=2)}):
        fired, _ = await _probe_bridge_silence({"bridge_id": "br", "silence_hours": 1})
        assert fired is False
        
    with patch("backend.services.channel_registry", {"br": MagicMock(last_inbound_at=None)}):
        fired, _ = await _probe_bridge_silence({"bridge_id": "br", "silence_hours": 1})
        assert fired is False

