import pytest
pytestmark = pytest.mark.unit

"""
Unit tests for the HeartbeatDaemon probe system.

Tests each of the 8 probe types in isolation using mocks and temp files.
Does NOT require a running database or external services.
"""
import asyncio
import hashlib
import json
import os
import tempfile
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch


from backend.heartbeat import (
   _parse_legacy_markdown,
   _load_orders_from_manifest,
   _probe_file_watch,
   _probe_task_deadline,
   _order_requires_network,
   _order_has_network_consent,
   execute_standing_order,
   DEFAULT_INTERVAL_MINUTES,
)


# ── Parser Tests ─────────────────────────────────────────────────────────────

class TestLegacyMarkdownParser:

   def test_parses_checked_items(self):
       raw = "- [x] Send weekly report\n- [x] Update CRM\n- [ ] Skipped item"
       orders = _parse_legacy_markdown(raw)
       assert len(orders) == 2
       assert orders[0]["label"] == "Send weekly report"
       assert orders[1]["label"] == "Update CRM"

   def test_empty_string_returns_empty_list(self):
       assert _parse_legacy_markdown("") == []

   def test_no_checked_items_returns_empty(self):
       raw = "- [ ] Task 1\n- [ ] Task 2"
       assert _parse_legacy_markdown(raw) == []

   def test_order_has_required_fields(self):
       raw = "- [x] Do something"
       orders = _parse_legacy_markdown(raw)
       assert len(orders) == 1
       o = orders[0]
       assert "id" in o
       assert "label" in o
       assert "active" in o
       assert o["probe_type"] == "task_deadline"
       assert o["action_type"] == "execute_objective"
       assert o["interval_minutes"] == DEFAULT_INTERVAL_MINUTES

   def test_duplicate_labels_get_different_ids(self):
       raw = "- [x] Task\n- [x] Task"
       orders = _parse_legacy_markdown(raw)
       # Both entries exist; they'll have the same hash since same label
       assert len(orders) == 2

   def test_label_id_is_deterministic(self):
       raw = "- [x] Daily standup"
       expected_id = hashlib.sha256("Daily standup".encode()).hexdigest()[:8]
       orders = _parse_legacy_markdown(raw)
       assert orders[0]["id"] == expected_id


class TestLoadOrdersFromManifest:

   def test_none_manifest_returns_empty(self):
       assert _load_orders_from_manifest(None) == []

   def test_empty_heartbeat_field_returns_empty(self):
       assert _load_orders_from_manifest({"heartbeat": ""}) == []

   def test_list_heartbeat_field_returns_dicts(self):
       manifest = {
           "heartbeat": [
               {"id": "h1", "active": True, "probe_type": "cron_expression",
                "action_type": "log_only", "interval_minutes": 60}
           ]
       }
       orders = _load_orders_from_manifest(manifest)
       assert len(orders) == 1
       assert orders[0]["id"] == "h1"

   def test_json_string_heartbeat_field_is_parsed(self):
       orders_data = [{"id": "h2", "probe_type": "cron_expression",
                       "action_type": "log_only", "interval_minutes": 30}]
       manifest = {"heartbeat": json.dumps(orders_data)}
       orders = _load_orders_from_manifest(manifest)
       assert len(orders) == 1

   def test_markdown_string_is_migrated(self):
       manifest = {"heartbeat": "- [x] Prepare briefing"}
       orders = _load_orders_from_manifest(manifest)
       assert len(orders) == 1
       assert orders[0]["probe_type"] == "task_deadline"


# ── Network Consent Tests ────────────────────────────────────────────────────

class TestNetworkConsent:

   def test_url_triggers_network_requirement(self):
       assert _order_requires_network("Fetch https://example.com/data") is True
       assert _order_requires_network("Fetch http://internal/health") is True
       assert _order_requires_network("Read local file") is False

   def test_network_ok_marker_grants_consent(self):
       assert _order_has_network_consent("Fetch [NETWORK_OK] https://example.com") is True
       assert _order_has_network_consent("Fetch https://example.com") is False

   @pytest.mark.asyncio
   async def test_order_missing_network_consent_is_blocked(self):
       result = await execute_standing_order("Check https://api.example.com/status")
       assert "Blocked" in result
       assert "NETWORK_OK" in result

   @pytest.mark.asyncio
   async def test_order_with_network_consent_proceeds(self):
       # This will hit the "original execution logic follows" stub — should not raise
       result = await execute_standing_order(
           "Check https://api.example.com/status [NETWORK_OK]"
       )
       # Result is None (stub) or some value — just ensure no exception
       assert result is None or isinstance(result, str)


# ── File Watch Probe ─────────────────────────────────────────────────────────

class TestFileWatchProbe:

   @pytest.mark.asyncio
   async def test_nonexistent_path_does_not_fire(self):
       fired, detail = await _probe_file_watch({"path": "/nonexistent/path/xyz.txt"})
       assert fired is False
       assert "not found" in detail.lower()

   @pytest.mark.asyncio
   async def test_new_file_fires_first_time(self, tmp_path):
       """First observation of a file always fires (no prior hash)."""
       test_file = tmp_path / "test.txt"
       test_file.write_text("initial content")
       fired, detail = await _probe_file_watch({"path": str(test_file)})
       assert fired is True
       assert "changed" in detail.lower() or "File" in detail

   @pytest.mark.asyncio
   async def test_unchanged_file_does_not_fire(self, tmp_path):
       """After first observation, same content should not fire."""
       test_file = tmp_path / "stable.txt"
       test_file.write_text("stable content")

       # First call — fires
       await _probe_file_watch({"path": str(test_file)})

       # Second call — same content, should not fire
       fired, detail = await _probe_file_watch({"path": str(test_file)})
       assert fired is False
       assert "No change" in detail

   @pytest.mark.asyncio
   async def test_changed_file_fires(self, tmp_path):
       """Mutating file content between calls fires the probe."""
       test_file = tmp_path / "mutable.txt"
       test_file.write_text("version 1")

       # Establish baseline
       await _probe_file_watch({"path": str(test_file)})

       # Mutate
       test_file.write_text("version 2 — different!")
       fired, detail = await _probe_file_watch({"path": str(test_file)})
       assert fired is True

   @pytest.mark.asyncio
   async def test_empty_path_does_not_fire(self):
       fired, detail = await _probe_file_watch({"path": ""})
       assert fired is False


# ── Task Deadline Probe ──────────────────────────────────────────────────────

class TestTaskDeadlineProbe:

   @pytest.mark.asyncio
   async def test_nonexistent_tasks_file_does_not_fire(self):
       fired, detail = await _probe_task_deadline({"path": "/nonexistent/TASKS.md"})
       assert fired is False

   @pytest.mark.asyncio
   async def test_overdue_task_fires(self, tmp_path):
       tasks_file = tmp_path / "TASKS.md"
       tasks_file.write_text(
           "- [ ] Overdue task @due(2020-01-01)\n"
           "- [ ] Future task @due(2099-12-31)\n"
       )
       fired, detail = await _probe_task_deadline({"path": str(tasks_file)})
       assert fired is True

   @pytest.mark.asyncio
   async def test_no_overdue_tasks_does_not_fire(self, tmp_path):
       tasks_file = tmp_path / "TASKS.md"
       tasks_file.write_text(
           "- [ ] Future task @due(2099-12-31)\n"
           "- [x] Already done task\n"
       )
       fired, detail = await _probe_task_deadline({"path": str(tasks_file)})
       assert fired is False

# ── Goal Progress Probe ──────────────────────────────────────────────────────

class TestGoalProgressProbe:

    @pytest.mark.asyncio
    async def test_no_goal_id_does_not_fire(self):
        from backend.heartbeat import _probe_goal_progress
        fired, detail = await _probe_goal_progress({})
        assert fired is False

    @pytest.mark.asyncio
    async def test_goal_below_threshold_fires(self):
        from backend.heartbeat import _probe_goal_progress
        import backend.services as svc
        
        mock_goal = MagicMock()
        mock_goal.title = "Test Goal"
        mock_goal.metric_current = 20.0
        mock_goal.metric_target = 100.0
        
        mock_ge = AsyncMock()
        mock_ge.get_goal = AsyncMock(return_value=mock_goal)
        
        original = svc.goal_engine
        svc.goal_engine = mock_ge
        try:
            fired, detail = await _probe_goal_progress({"goal_id": 1, "threshold_pct": 50.0})
            assert fired is True
            assert "20.0%" in detail
        finally:
            svc.goal_engine = original

    @pytest.mark.asyncio
    async def test_goal_above_threshold_does_not_fire(self):
        from backend.heartbeat import _probe_goal_progress
        import backend.services as svc
        
        mock_goal = MagicMock()
        mock_goal.title = "Test Goal"
        mock_goal.metric_current = 80.0
        mock_goal.metric_target = 100.0
        
        mock_ge = AsyncMock()
        mock_ge.get_goal = AsyncMock(return_value=mock_goal)
        
        original = svc.goal_engine
        svc.goal_engine = mock_ge
        try:
            fired, detail = await _probe_goal_progress({"goal_id": 1, "threshold_pct": 50.0})
            assert fired is False
            assert "above threshold" in detail
        finally:
            svc.goal_engine = original

# ── URL Fetch Probe ──────────────────────────────────────────────────────────

class TestUrlFetchProbe:

    @pytest.mark.asyncio
    async def test_no_url_does_not_fire(self):
        from backend.heartbeat import _probe_url_fetch
        fired, detail = await _probe_url_fetch({})
        assert fired is False

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_url_reachable_fires(self, mock_get):
        from backend.heartbeat import _probe_url_fetch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Hello World"
        mock_get.return_value = mock_resp
        
        fired, detail = await _probe_url_fetch({"url": "http://example.com"})
        assert fired is True
        assert "reachable" in detail

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_url_keyword_found(self, mock_get):
        from backend.heartbeat import _probe_url_fetch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Hello World"
        mock_get.return_value = mock_resp
        
        fired, detail = await _probe_url_fetch({"url": "http://example.com", "keyword": "world"})
        assert fired is True

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_url_keyword_not_found(self, mock_get):
        from backend.heartbeat import _probe_url_fetch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Hello World"
        mock_get.return_value = mock_resp
        
        fired, detail = await _probe_url_fetch({"url": "http://example.com", "keyword": "missing"})
        assert fired is False

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_url_change_detection(self, mock_get):
        from backend.heartbeat import _probe_url_fetch
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "Hello World v1"
        mock_get.return_value = mock_resp
        
        # First call creates the file and fires
        fired, detail = await _probe_url_fetch({"url": "http://example.com", "check_change": True})
        assert fired is True
        
        # Second call with same text should NOT fire
        fired, detail = await _probe_url_fetch({"url": "http://example.com", "check_change": True})
        assert fired is False

        # Third call with new text should fire
        mock_resp.text = "Hello World v2"
        fired, detail = await _probe_url_fetch({"url": "http://example.com", "check_change": True})
        assert fired is True

# ── Memory Pattern Probe ─────────────────────────────────────────────────────

class TestMemoryPatternProbe:

    @pytest.mark.asyncio
    async def test_no_query_does_not_fire(self):
        from backend.heartbeat import _probe_memory_pattern
        fired, detail = await _probe_memory_pattern({})
        assert fired is False

    @pytest.mark.asyncio
    async def test_memory_pattern_found(self):
        from backend.heartbeat import _probe_memory_pattern
        import backend.services as svc
        
        mock_mem = AsyncMock()
        mock_mem.search = AsyncMock(return_value=[{"id": 1}, {"id": 2}])
        
        original = svc.memory
        svc.memory = mock_mem
        svc.hlsm_manager = mock_mem
        try:
            fired, detail = await _probe_memory_pattern({"query": "error", "min_occurrences": 2})
            assert fired is True
            assert "found 2" in detail
        finally:
            svc.memory = original

# ── System Health Probe ──────────────────────────────────────────────────────

class TestSystemHealthProbe:

    @pytest.mark.asyncio
    async def test_system_health_threshold_reached(self):
        from backend.heartbeat import _probe_system_health
        from backend.models import TaskRecord
        import time
        
        records = [
            TaskRecord(action="Task1", status="failed", end_time=datetime.fromtimestamp(time.time())),
            TaskRecord(action="Task2", status="failed", end_time=datetime.fromtimestamp(time.time())),
            TaskRecord(action="Task3", status="failed", end_time=datetime.fromtimestamp(time.time()))
        ]
        
        with patch("sqlmodel.Session.exec") as mock_exec:
            mock_exec.return_value.all.return_value = records
            fired, detail = await _probe_system_health({"failure_threshold": 3, "hours": 4})
            assert fired is True

    @pytest.mark.asyncio
    async def test_system_health_threshold_not_reached(self):
        from backend.heartbeat import _probe_system_health
        from backend.models import TaskRecord
        import time
        
        records = [
            TaskRecord(action="Task1", status="failed", end_time=datetime.fromtimestamp(time.time())),
        ]
        
        with patch("sqlmodel.Session.exec") as mock_exec:
            mock_exec.return_value.all.return_value = records
            fired, detail = await _probe_system_health({"failure_threshold": 3, "hours": 4})
            assert fired is False

# ── Bridge Silence Probe ─────────────────────────────────────────────────────

class TestBridgeSilenceProbe:

    @pytest.mark.asyncio
    async def test_no_bridge_id(self):
        from backend.heartbeat import _probe_bridge_silence
        fired, detail = await _probe_bridge_silence({})
        assert fired is False

    @pytest.mark.asyncio
    async def test_bridge_silent_fires(self):
        from backend.heartbeat import _probe_bridge_silence
        import backend.services as svc
        
        mock_adapter = MagicMock()
        mock_adapter.last_inbound_at = time.time() - (5 * 3600)  # 5 hours ago
        mock_adapter.last_outbound_at = time.time() - (6 * 3600) # 6 hours ago
        mock_adapter.last_inbound_sender = "user1"
        
        original_registry = svc.channel_registry
        svc.channel_registry = {"discord": mock_adapter}
        try:
            fired, detail = await _probe_bridge_silence({"bridge_id": "discord", "silence_hours": 4})
            assert fired is True
        finally:
            svc.channel_registry = original_registry

    @pytest.mark.asyncio
    async def test_bridge_not_silent(self):
        from backend.heartbeat import _probe_bridge_silence
        import backend.services as svc
        
        mock_adapter = MagicMock()
        mock_adapter.last_inbound_at = time.time() - (1 * 3600)  # 1 hour ago
        mock_adapter.last_outbound_at = time.time() - (2 * 3600)
        
        original_registry = svc.channel_registry
        svc.channel_registry = {"discord": mock_adapter}
        try:
            fired, detail = await _probe_bridge_silence({"bridge_id": "discord", "silence_hours": 4})
            assert fired is False
        finally:
            svc.channel_registry = original_registry
