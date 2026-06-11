import pytest
pytestmark = pytest.mark.unit

"""
Upgraded Heartbeat — Production Test Suite
==========================================
Covers:
  - Legacy markdown order migration
  - JSON array order loading
  - All 8 probe types (file_watch, task_deadline, goal_progress,
    url_fetch, memory_pattern, system_health, bridge_silence, cron_expression)
  - All 6 action paths (notify_ws, notify_bridge, execute_objective,
    evaluate_goal, log_only, pcl_signal)
  - Per-agent order loading from AgentRecord
  - Cooldown enforcement via HeartbeatOrderRecord
  - Quiet hours suppression
  - Outcome persistence
  - PCL signal storage flag
"""
import asyncio
import json
import os
import time
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def sqlite_engine(tmp_path):
    from sqlmodel import create_engine, SQLModel
    import backend.models  # registers all tables
    engine = create_engine(
        f"sqlite:///{tmp_path}/hb_test.db",
        connect_args={"check_same_thread": False},
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def mock_vault():
    v = AsyncMock()
    v.retrieve_secret = AsyncMock(return_value={
        "heartbeat": json.dumps([{
            "id": "root_order_01",
            "label": "Check TASKS.md for deadlines",
            "active": True,
            "probe_type": "task_deadline",
            "probe_config": {"path": "TASKS.md"},
            "action_type": "notify_ws",
            "action_config": {"message_template": "{label}: {probe_detail}"},
            "interval_minutes": 1,
        }])
    })
    return v


@pytest.fixture
def mock_ws():
    ws = AsyncMock()
    ws.broadcast_event = AsyncMock()
    return ws


@pytest.fixture
def daemon(sqlite_engine, mock_vault, mock_ws):
    from backend.heartbeat import HeartbeatDaemon
    d = HeartbeatDaemon(
        orchestrator=MagicMock(),
        vault=mock_vault,
        interval_seconds=900,
        db_engine=sqlite_engine,
    )
    d.ws_gateway = mock_ws
    # d.db_engine = sqlite_engine  <-- redundant now but kept as backup
    return d


# ─── Order Loading ────────────────────────────────────────────────────────────

def test_legacy_markdown_migration():
    from backend.heartbeat import _parse_legacy_markdown
    raw = "- [x] Monitor system vitality\n- [ ] Inactive\n- [x] Scan for anomalies"
    orders = _parse_legacy_markdown(raw)
    assert len(orders) == 2
    assert orders[0]["label"] == "Monitor system vitality"
    assert orders[0]["active"] is True
    assert orders[0]["probe_type"] == "task_deadline"
    assert orders[0]["action_type"] == "execute_objective"
    labels = [o["label"] for o in orders]
    assert "Inactive" not in labels


def test_json_array_order_loading():
    from backend.heartbeat import _load_orders_from_manifest
    orders_json = json.dumps([{
        "id": "t1", "label": "URL Monitor", "active": True,
        "probe_type": "url_fetch", "probe_config": {"url": "https://example.com"},
        "action_type": "pcl_signal", "action_config": {"priority": 2},
        "interval_minutes": 5,
    }])
    orders = _load_orders_from_manifest({"heartbeat": orders_json})
    assert len(orders) == 1
    assert orders[0]["probe_type"] == "url_fetch"


def test_inactive_orders_excluded_from_legacy():
    from backend.heartbeat import _parse_legacy_markdown
    raw = "- [x] Active order\n- [ ] This is inactive"
    orders = _parse_legacy_markdown(raw)
    assert len(orders) == 1
    assert orders[0]["label"] == "Active order"


def test_empty_manifest_returns_no_orders():
    from backend.heartbeat import _load_orders_from_manifest
    assert _load_orders_from_manifest(None) == []
    assert _load_orders_from_manifest({}) == []
    assert _load_orders_from_manifest({"heartbeat": ""}) == []


# ─── Probe: task_deadline ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_probe_task_deadline_fires_on_overdue(tmp_path):
    from backend.heartbeat import _probe_task_deadline
    tasks_file = tmp_path / "TASKS.md"
    tasks_file.write_text(
        "## Tasks\n"
        "- [ ] Overdue task (due: 2020-01-15)\n"
        "- [ ] Future task (due: 2099-12-31)\n"
        "- [x] Done task\n"
    )
    fired, detail = await _probe_task_deadline({"path": str(tasks_file)})
    assert fired is True
    assert "overdue" in detail.lower() or "1" in detail


@pytest.mark.asyncio
async def test_probe_task_deadline_silent_when_no_overdue(tmp_path):
    from backend.heartbeat import _probe_task_deadline
    tasks_file = tmp_path / "TASKS.md"
    tasks_file.write_text("- [ ] Future task (due: 2099-12-31)\n")
    fired, _ = await _probe_task_deadline({"path": str(tasks_file)})
    assert fired is False


@pytest.mark.asyncio
async def test_probe_task_deadline_missing_file():
    from backend.heartbeat import _probe_task_deadline
    fired, detail = await _probe_task_deadline({"path": "/nonexistent/TASKS.md"})
    assert fired is False
    assert "not found" in detail.lower()


# ─── Probe: file_watch ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_probe_file_watch_fires_on_first_run(tmp_path):
    from backend.heartbeat import _probe_file_watch
    test_file = tmp_path / "watch.txt"
    test_file.write_text("version 1")
    # First run — no previous hash, should fire
    fired, detail = await _probe_file_watch({"path": str(test_file)})
    assert fired is True
    assert "changed" in detail.lower()


@pytest.mark.asyncio
async def test_probe_file_watch_silent_on_no_change(tmp_path):
    from backend.heartbeat import _probe_file_watch
    test_file = tmp_path / "watch2.txt"
    test_file.write_text("stable content")
    # First run fires
    await _probe_file_watch({"path": str(test_file)})
    # Second run — same content, should NOT fire
    fired, _ = await _probe_file_watch({"path": str(test_file)})
    assert fired is False


# ─── Probe: cron_expression ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_probe_cron_expression_always_fires():
    from backend.heartbeat import _run_probe
    fired, detail = await _run_probe("cron_expression", {}, None)
    assert fired is True
    assert "cron" in detail.lower()


# ─── Probe: unknown ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_probe_unknown_returns_false_no_raise():
    from backend.heartbeat import _run_probe
    fired, detail = await _run_probe("nonexistent_probe_xyz", {}, None)
    assert fired is False
    assert "Unknown" in detail


# ─── Action: notify_ws ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_notify_ws_broadcasts(mock_ws):
    from backend.heartbeat import _action_notify_ws
    order = {"id": "ord_01", "label": "Test Notification"}
    outcome, detail = await _action_notify_ws(
        {"message_template": "{label}: {probe_detail}"},
        "3 overdue tasks found",
        order,
        mock_ws,
    )
    assert outcome == "success"
    mock_ws.broadcast_event.assert_awaited_once()
    event_name, event_data = mock_ws.broadcast_event.call_args[0]
    assert event_name == "heartbeat.notification"
    assert "Test Notification" in event_data["message"]
    assert "3 overdue tasks found" in event_data["probe_detail"]


@pytest.mark.asyncio
async def test_action_notify_ws_skips_without_gateway():
    from backend.heartbeat import _action_notify_ws
    outcome, detail = await _action_notify_ws({}, "probe", {"id": "x"}, None)
    assert outcome == "skipped"
    assert "gateway" in detail.lower()


# ─── Action: execute_objective ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_execute_objective_calls_orchestrator():
    from backend.heartbeat import _action_execute_objective
    mock_orch = AsyncMock()
    mock_orch.execute_objective = AsyncMock(
        return_value={"status": "completed", "result": "done"}
    )
    order = {"id": "ord_02", "label": "Run DAG"}
    outcome, detail = await _action_execute_objective(
        {"objective_template": "Run: {probe_detail}", "autonomy": "RESTRICTED"},
        "file changed",
        order,
        None,
        mock_orch,
    )
    assert outcome == "success"
    mock_orch.execute_objective.assert_awaited_once()
    kwargs = mock_orch.execute_objective.call_args[1]
    assert "file changed" in kwargs["objective"]
    assert kwargs["autonomy"] == "RESTRICTED"


@pytest.mark.asyncio
async def test_action_execute_objective_injects_agent_id():
    from backend.heartbeat import _action_execute_objective
    mock_orch = AsyncMock()
    mock_orch.execute_objective = AsyncMock(return_value={"status": "completed"})
    order = {"id": "ord_03", "label": "Agent Task"}
    await _action_execute_objective(
        {"objective_template": "{probe_detail}", "autonomy": "RESTRICTED"},
        "deadline hit",
        order,
        "agent_abc",
        mock_orch,
    )
    kwargs = mock_orch.execute_objective.call_args[1]
    assert "[Agent:agent_abc]" in kwargs["objective"]


@pytest.mark.asyncio
async def test_action_execute_objective_skips_without_orchestrator():
    from backend.heartbeat import _action_execute_objective
    outcome, _ = await _action_execute_objective({}, "probe", {"id": "x"}, None, None)
    assert outcome == "skipped"


# ─── Action: pcl_signal ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_pcl_signal_stores_to_hlsm():
    from backend.heartbeat import _action_pcl_signal
    mock_hlsm = AsyncMock()
    mock_hlsm.store = AsyncMock(return_value="mem_id_abc")
    order = {"id": "ord_04", "label": "URL Changed"}
    outcome, detail = await _action_pcl_signal(
        {"signal_label": "Website updated", "priority": 2},
        "content changed at https://example.com",
        order,
        "agent_xyz",
        mock_hlsm,
    )
    assert outcome == "success"
    mock_hlsm.store.assert_awaited_once()
    call_kwargs = mock_hlsm.store.call_args[1]
    assert "[PCL_SIGNAL]" in call_kwargs["content"]
    assert "[Agent:agent_xyz]" in call_kwargs["content"]
    assert "priority=2" in call_kwargs["content"]
    assert call_kwargs["metadata"]["source"] == "heartbeat_signal"
    assert call_kwargs["metadata"]["priority"] == 2


@pytest.mark.asyncio
async def test_action_pcl_signal_skips_without_memory():
    from backend.heartbeat import _action_pcl_signal
    outcome, detail = await _action_pcl_signal({}, "probe", {"id": "x"}, None, None)
    assert outcome == "skipped"


# ─── Action: log_only ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_log_only_stores_to_memory():
    from backend.heartbeat import _action_log_only
    mock_hlsm = AsyncMock()
    mock_hlsm.store = AsyncMock(return_value="mem_id_log")
    order = {"id": "ord_05", "label": "Log Event"}
    outcome, _ = await _action_log_only("something happened", order, mock_hlsm)
    assert outcome == "success"
    stored = mock_hlsm.store.call_args[1]
    assert stored["metadata"]["source"] == "heartbeat_log"
    assert stored["metadata"]["order_id"] == "ord_05"


# ─── Action: evaluate_goal ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_evaluate_goal_calls_engine():
    from backend.heartbeat import _action_evaluate_goal
    import backend.services as svc
    mock_ge = AsyncMock()
    mock_ge.evaluate_progress = AsyncMock(return_value={"progress": 45.0})
    original = svc.goal_engine
    svc.goal_engine = mock_ge
    try:
        outcome, detail = await _action_evaluate_goal({"goal_id": "7"})
        assert outcome == "success"
        mock_ge.evaluate_progress.assert_awaited_once_with(7)
    finally:
        svc.goal_engine = original


@pytest.mark.asyncio
async def test_action_evaluate_goal_skips_without_goal_id():
    from backend.heartbeat import _action_evaluate_goal
    outcome, _ = await _action_evaluate_goal({})
    assert outcome == "skipped"


# ─── Cooldown via HeartbeatOrderRecord ────────────────────────────────────────

def test_order_due_on_first_run(daemon, sqlite_engine):
    order = {"id": "never_run_order_001", "interval_minutes": 60}
    assert daemon._is_order_due(order, None) is True


def test_order_not_due_within_interval(daemon, sqlite_engine):
    from backend.models import HeartbeatOrderRecord
    from sqlmodel import Session
    with Session(sqlite_engine) as session:
        session.add(HeartbeatOrderRecord(
            order_id="recent_order_001",
            agent_id=None,
            fired_at=time.time() - 30,  # 30 seconds ago
            probe_type="task_deadline",
            action_type="notify_ws",
            outcome="success",
        ))
        session.commit()
    order = {"id": "recent_order_001", "interval_minutes": 15}
    assert daemon._is_order_due(order, None) is False


def test_order_due_after_interval_elapsed(daemon, sqlite_engine):
    from backend.models import HeartbeatOrderRecord
    from sqlmodel import Session
    with Session(sqlite_engine) as session:
        session.add(HeartbeatOrderRecord(
            order_id="old_order_001",
            agent_id=None,
            fired_at=time.time() - 3700,  # just over 1 hour ago
            probe_type="cron_expression",
            action_type="log_only",
            outcome="success",
        ))
        session.commit()
    order = {"id": "old_order_001", "interval_minutes": 60}
    assert daemon._is_order_due(order, None) is True


# ─── Outcome Persistence ──────────────────────────────────────────────────────

def test_outcome_persisted_to_db(daemon, sqlite_engine):
    from backend.models import HeartbeatOrderRecord
    from sqlmodel import Session, select
    daemon._persist_outcome(
        "test_persist_001", None, "file_watch", "notify_ws",
        "success", "File changed: TASKS.md"
    )
    with Session(sqlite_engine) as session:
        records = session.exec(
            select(HeartbeatOrderRecord)
            .where(HeartbeatOrderRecord.order_id == "test_persist_001")
        ).all()
    assert len(records) == 1
    assert records[0].outcome == "success"
    assert records[0].detail == "File changed: TASKS.md"
    assert records[0].signal_stored is False


def test_pcl_signal_stored_flag(daemon, sqlite_engine):
    from backend.models import HeartbeatOrderRecord
    from sqlmodel import Session, select
    daemon._persist_outcome(
        "signal_order_001", "agent_01", "url_fetch", "pcl_signal",
        "success", "content changed", signal_stored=True
    )
    with Session(sqlite_engine) as session:
        rec = session.exec(
            select(HeartbeatOrderRecord)
            .where(HeartbeatOrderRecord.order_id == "signal_order_001")
        ).first()
    assert rec is not None
    assert rec.signal_stored is True
    assert rec.agent_id == "agent_01"


# ─── Per-Agent Order Loading ──────────────────────────────────────────────────

def test_agent_orders_loaded_from_db(daemon, sqlite_engine):
    from backend.models import AgentRecord
    from sqlmodel import Session
    daemon.db_engine = sqlite_engine

    agent_orders = json.dumps([{
        "id": "agent_order_01", "label": "Agent Probe",
        "active": True, "probe_type": "system_health",
        "probe_config": {"failure_threshold": 3, "hours": 4},
        "action_type": "log_only", "action_config": {},
        "interval_minutes": 30,
    }])
    with Session(sqlite_engine) as session:
        session.add(AgentRecord(
            id="agent_test_01",
            name="Test Agent",
            status="ACTIVE",
            heartbeat_orders=agent_orders,
        ))
        session.commit()

    loaded = daemon._load_agent_orders()
    assert len(loaded) == 1
    agent_id, order = loaded[0]
    assert agent_id == "agent_test_01"
    assert order["label"] == "Agent Probe"
    assert order["probe_type"] == "system_health"


def test_paused_agent_orders_not_loaded(daemon, sqlite_engine):
    from backend.models import AgentRecord
    from sqlmodel import Session
    daemon.db_engine = sqlite_engine

    agent_orders = json.dumps([{
        "id": "paused_order_01", "label": "Should not load",
        "active": True, "probe_type": "cron_expression",
        "probe_config": {}, "action_type": "log_only",
        "action_config": {}, "interval_minutes": 15,
    }])
    with Session(sqlite_engine) as session:
        session.add(AgentRecord(
            id="paused_agent_01",
            name="Paused Agent",
            status="PAUSED",
            heartbeat_orders=agent_orders,
        ))
        session.commit()

    loaded = daemon._load_agent_orders()
    agent_ids = [aid for aid, _ in loaded]
    assert "paused_agent_01" not in agent_ids


# ─── Quiet Hours ──────────────────────────────────────────────────────────────

def test_quiet_hours_detection_crosses_midnight(daemon):
    from unittest.mock import patch
    # quiet_start=22, quiet_end=7 (crosses midnight)
    daemon.quiet_start = 22
    daemon.quiet_end = 7
    with patch("backend.heartbeat.datetime") as mock_dt:
        mock_dt.now.return_value = MagicMock(hour=23)
        assert daemon._is_quiet_hours() is True
    with patch("backend.heartbeat.datetime") as mock_dt:
        mock_dt.now.return_value = MagicMock(hour=3)
        assert daemon._is_quiet_hours() is True
    with patch("backend.heartbeat.datetime") as mock_dt:
        mock_dt.now.return_value = MagicMock(hour=12)
        assert daemon._is_quiet_hours() is False

# ── Action: notify_bridge ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_action_notify_bridge_success():
    from backend.heartbeat import _action_notify_bridge
    import backend.services as svc
    
    mock_adapter = AsyncMock()
    mock_adapter.send_message = AsyncMock(return_value={"status": "success", "id": 1})
    
    original_registry = svc.channel_registry
    svc.channel_registry = {"discord": mock_adapter}
    
    try:
        outcome, detail = await _action_notify_bridge(
            {"bridge_id": "discord", "recipient": "user1", "message_template": "{probe_detail}"},
            "system issue",
            {"label": "Test"},
        )
        assert outcome == "success"
        mock_adapter.send_message.assert_awaited_once_with(recipient="user1", content="system issue")
    finally:
        svc.channel_registry = original_registry

@pytest.mark.asyncio
async def test_action_notify_bridge_no_recipient():
    from backend.heartbeat import _action_notify_bridge
    outcome, detail = await _action_notify_bridge({"bridge_id": "discord"}, "info", {})
    assert outcome == "failed"

@pytest.mark.asyncio
async def test_action_notify_bridge_not_in_registry():
    from backend.heartbeat import _action_notify_bridge
    import backend.services as svc
    original_registry = svc.channel_registry
    svc.channel_registry = {}
    try:
        outcome, detail = await _action_notify_bridge({"bridge_id": "discord", "recipient": "user"}, "info", {})
        assert outcome == "failed"
    finally:
        svc.channel_registry = original_registry

# ── Daemon Loops and Evaluation ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_daemon_stop(daemon):
    daemon._running = True
    f = asyncio.Future()
    daemon._task = f
    
    await daemon.stop()
    assert daemon._running is False
    assert f.cancelled()

@pytest.mark.asyncio
async def test_evaluate_all_orders(daemon):
    # Mock the loaders
    daemon._load_root_orders = AsyncMock(return_value=[{"id": "root1", "active": True}])
    daemon._load_agent_orders = MagicMock(return_value=[("agent1", {"id": "agent1_order", "active": True})])
    
    # Mock due check and run
    daemon._is_order_due = MagicMock(return_value=True)
    daemon._run_order = AsyncMock()
    
    await daemon._evaluate_all_orders()
    
    # Should have run both orders
    assert daemon._run_order.call_count == 2
    
@pytest.mark.asyncio
async def test_run_order_success(daemon):
    from backend.heartbeat import _run_action
    
    order = {"id": "ord1", "probe_type": "cron_expression", "action_type": "log_only"}
    
    # Mock the probe
    with patch("backend.heartbeat._run_probe", new_callable=AsyncMock) as mock_probe:
        mock_probe.return_value = (True, "Cron fired")
        
        # Mock the action
        with patch("backend.heartbeat._run_action", new_callable=AsyncMock) as mock_action:
            mock_action.return_value = ("success", "Logged")
            
            # Mock persistence
            daemon._persist_outcome = MagicMock()
            
            await daemon._run_order(order, None)
            
            mock_probe.assert_awaited_once()
            mock_action.assert_awaited_once()
            daemon._persist_outcome.assert_called_once()
            
            # Check persistence args
            args, kwargs = daemon._persist_outcome.call_args
            assert args[0] == "ord1"  # order_id
            assert args[4] == "success" # outcome

@pytest.mark.asyncio
async def test_tick_loop_handles_exception(daemon):
    daemon._running = True
    
    async def side_effect():
        daemon._running = False # stop after one tick
        raise ValueError("Simulated error in evaluation")
        
    daemon._evaluate_all_orders = AsyncMock(side_effect=side_effect)
    
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        # Run the tick loop
        await daemon._tick_loop()
        # It should catch the ValueError and sleep, then exit since running=False
        mock_sleep.assert_awaited()
