import pytest
from unittest.mock import MagicMock, AsyncMock, patch
pytestmark = pytest.mark.unit

from backend.heartbeat import HeartbeatDaemon, _probe_topological_drift, _probe_subagent_loop
from backend.topology.barcode_clock import TopologicalBarcodeClock
from backend import services


@pytest.fixture(autouse=True)
def cleanup_services():
    yield
    services.avl_gate = None
    services.barcode_clock = None


@pytest.mark.asyncio
async def test_probe_topological_drift_stable_and_strike():
    mock_avl = MagicMock()
    mock_avl.get_saturation_strikes.return_value = 0
    services.avl_gate = mock_avl

    fired, detail = await _probe_topological_drift({"max_strikes": 2})
    assert fired is False
    assert "Topology stable" in detail

    # High strikes
    mock_avl.get_saturation_strikes.return_value = 3
    fired_drift, detail_drift = await _probe_topological_drift({"max_strikes": 2})
    assert fired_drift is True
    assert "Topological drift detected" in detail_drift


@pytest.mark.asyncio
async def test_probe_subagent_loop_acyclic_and_loop():
    clock = TopologicalBarcodeClock()
    services.barcode_clock = clock

    fired, detail = await _probe_subagent_loop({})
    assert fired is False
    assert "acyclic" in detail

    # Register active 1D cycle
    clock.register_birth(dimension=1, generator_id="stuck_tool_loop")
    fired_loop, detail_loop = await _probe_subagent_loop({})
    assert fired_loop is True
    assert "Sub-agent reasoning loop detected" in detail_loop


@pytest.mark.asyncio
async def test_heartbeat_barcode_tick_and_dream():
    daemon = HeartbeatDaemon(orchestrator=MagicMock(), vault=MagicMock())
    assert daemon.barcode_clock.clock == 0

    daemon.barcode_clock.tick()
    assert daemon.barcode_clock.clock == 1

    # Test dreaming cycle execution
    with patch("backend.heartbeat.time.time", return_value=1700000000.0):
        await daemon._run_quiet_hours_dreaming_cycle()
        assert daemon._last_dream_cycle_ts == 1700000000.0
