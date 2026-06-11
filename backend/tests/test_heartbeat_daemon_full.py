import pytest
pytestmark = pytest.mark.unit

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session, select
from backend.models import AgentRecord, HeartbeatOrderRecord
from backend.heartbeat import HeartbeatDaemon

@pytest.fixture
def daemon_with_mock_db():
    daemon = HeartbeatDaemon(MagicMock(), MagicMock(), 1)
    daemon.db_engine = MagicMock()
    return daemon

@pytest.mark.asyncio
async def test_daemon_inject_hlsm(daemon_with_mock_db):
    daemon_with_mock_db.inject_hlsm("mock_hlsm")
    assert daemon_with_mock_db._hlsm == "mock_hlsm"
    assert daemon_with_mock_db._dream_orchestrator is not None

def test_get_db_fallback():
    daemon = HeartbeatDaemon(MagicMock(), MagicMock(), 1)
    db = daemon._get_db()
    assert db is not None

@pytest.mark.asyncio
async def test_daemon_start_stop():
    daemon = HeartbeatDaemon(MagicMock(), MagicMock(), 1)
    with patch.object(daemon, '_tick_loop', new_callable=AsyncMock):
        # Fire and forget start to allow tick_loop to mock complete
        asyncio.create_task(daemon.start())
        await asyncio.sleep(0.01)
        assert daemon._running is True
        
        await daemon.stop()
        assert daemon._running is False

@pytest.mark.asyncio
async def test_tick_loop_dream_orchestrator(daemon_with_mock_db):
    daemon_with_mock_db._running = True
    daemon_with_mock_db._dream_orchestrator = AsyncMock()
    daemon_with_mock_db._dream_orchestrator.evaluate_sleep_trigger.return_value = True
    daemon_with_mock_db._dream_orchestrator.is_dreaming = True
    
    with patch("backend.services.ace_engine", MagicMock(get_affective_state=MagicMock(return_value="state")), create=True):
        async def dummy_sleep(*args, **kwargs):
            daemon_with_mock_db._running = False
        with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=dummy_sleep):
            await daemon_with_mock_db._tick_loop()
    
    daemon_with_mock_db._dream_orchestrator.trigger_dream_cycle.assert_awaited_once()

@pytest.mark.asyncio
async def test_tick_loop_manifest_exception(daemon_with_mock_db):
    daemon_with_mock_db._running = True
    daemon_with_mock_db.vault = AsyncMock()
    daemon_with_mock_db.vault.retrieve_secret.side_effect = Exception("vault err")
    
    async def dummy_sleep(*args, **kwargs):
        daemon_with_mock_db._running = False
    
    with patch("asyncio.sleep", new_callable=AsyncMock, side_effect=dummy_sleep) as mock_sleep:
        await daemon_with_mock_db._tick_loop()
        mock_sleep.assert_awaited()

def test_is_quiet_hours_cross_midnight(daemon_with_mock_db):
    daemon_with_mock_db.quiet_start = 22
    daemon_with_mock_db.quiet_end = 7
    with patch("backend.heartbeat.datetime") as mock_dt:
        mock_dt.now.return_value.hour = 2
        assert daemon_with_mock_db._is_quiet_hours() is True

@pytest.mark.asyncio
async def test_load_root_orders_exception(daemon_with_mock_db):
    daemon_with_mock_db.vault = AsyncMock()
    daemon_with_mock_db.vault.retrieve_secret.side_effect = Exception("Vault boom")
    res = await daemon_with_mock_db._load_root_orders()
    assert res == []

def test_load_agent_orders_exceptions(daemon_with_mock_db):
    from sqlmodel import Session
    mock_session = MagicMock()
    mock_agent1 = AgentRecord(id="a1", name="a1", status="ACTIVE", heartbeat_orders=None)
    mock_agent2 = AgentRecord(id="a2", name="a2", status="ACTIVE", heartbeat_orders="invalid json")
    
    mock_session.exec.return_value.all.return_value = [mock_agent1, mock_agent2]
    
    with patch("backend.heartbeat.Session", return_value=mock_session):
        res = daemon_with_mock_db._load_agent_orders()
        assert res == []

    # test overall exception
    with patch("backend.heartbeat.Session", side_effect=Exception("DB err")):
        res2 = daemon_with_mock_db._load_agent_orders()
        assert res2 == []

def test_is_order_due_exception(daemon_with_mock_db):
    with patch("backend.heartbeat.Session", side_effect=Exception("DB boom")):
        assert daemon_with_mock_db._is_order_due({}, None) is True

@pytest.mark.asyncio
async def test_run_order_no_change(daemon_with_mock_db):
    order = {"id": "1"}
    with patch("backend.heartbeat._run_probe", return_value=(False, "No change")):
        with patch.object(daemon_with_mock_db, "_persist_outcome") as mock_persist:
            await daemon_with_mock_db._run_order(order, None)
            mock_persist.assert_called_once_with("1", None, "task_deadline", "log_only", "no_change", "No change")

@pytest.mark.asyncio
async def test_run_order_quiet_hours(daemon_with_mock_db):
    order = {"id": "1", "action_type": "notify_ws"}
    daemon_with_mock_db._is_quiet_hours = MagicMock(return_value=True)
    with patch("backend.heartbeat._run_probe", return_value=(True, "Fired")):
        with patch.object(daemon_with_mock_db, "_persist_outcome") as mock_persist:
            await daemon_with_mock_db._run_order(order, None)
            mock_persist.assert_called_once_with("1", None, "task_deadline", "notify_ws", "skipped", "quiet_hours")

def test_persist_outcome_exception(daemon_with_mock_db):
    with patch("backend.heartbeat.Session", side_effect=Exception("DB Error")):
        # Should catch and not raise
        daemon_with_mock_db._persist_outcome("1", None, "p", "a", "success", "detail")

@pytest.mark.asyncio
async def test_evaluate_all_orders_empty(daemon_with_mock_db):
    daemon_with_mock_db._load_root_orders = AsyncMock(return_value=[])
    daemon_with_mock_db._load_agent_orders = MagicMock(return_value=[])
    await daemon_with_mock_db._evaluate_all_orders() # Returns early

@pytest.mark.asyncio
async def test_evaluate_all_orders_none_due(daemon_with_mock_db):
    daemon_with_mock_db._load_root_orders = AsyncMock(return_value=[{"id": "1"}])
    daemon_with_mock_db._load_agent_orders = MagicMock(return_value=[])
    daemon_with_mock_db._is_order_due = MagicMock(return_value=False)
    await daemon_with_mock_db._evaluate_all_orders() # Returns early

@pytest.mark.asyncio
async def test_evaluate_all_orders_gather_exception(daemon_with_mock_db):
    daemon_with_mock_db._load_root_orders = AsyncMock(return_value=[{"id": "1"}])
    daemon_with_mock_db._load_agent_orders = MagicMock(return_value=[])
    daemon_with_mock_db._is_order_due = MagicMock(return_value=True)
    daemon_with_mock_db._run_order = AsyncMock(side_effect=Exception("Run Error"))
    
    await daemon_with_mock_db._evaluate_all_orders()

def test_get_order_history(daemon_with_mock_db):
    mock_session = MagicMock()
    mock_record = MagicMock(fired_at=123, outcome="success", detail="d", signal_stored=False)
    mock_session.__enter__.return_value.exec.return_value.all.return_value = [mock_record]
    
    with patch("backend.heartbeat.Session", return_value=mock_session):
        history = daemon_with_mock_db.get_order_history("1", None)
        assert len(history) == 1
        assert history[0]["outcome"] == "success"

def test_get_order_history_exception(daemon_with_mock_db):
    with patch("backend.heartbeat.Session", side_effect=Exception("DB Err")):
        history = daemon_with_mock_db.get_order_history("1", None)
        assert history == []
