import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.orchestrator import ExecutiveOrchestrator
from backend.ace.engine import AffectiveEngine
from backend.config import Settings
from sqlmodel import Session
from backend.models import Run, RunStatus, TaskRecord, TaskStatus
from datetime import datetime, timezone

@pytest.fixture
def mock_ace():
    ace = MagicMock(spec=AffectiveEngine)
    ace.current_state = {"flow_mode": "STANDARD"}
    
    mock_affective_state = MagicMock()
    mock_affective_state.tension = 500
    mock_affective_state.valence = 500
    ace.get_affective_state.return_value = mock_affective_state
    
    ace.btm = MagicMock()
    ace.btm.psi_from_state.return_value = 0.5
    
    ace.should_throttle.return_value = False
    return ace

@pytest.fixture
def orchestrator(mock_router, temp_vault, mock_ace, mock_settings):
    # Construct with dependencies from conftest
    orc = ExecutiveOrchestrator(
        router=mock_router,
        vault=temp_vault,
        ace=mock_ace,
        settings=mock_settings,
        agent_id="test_exec",
        vault_root=temp_vault.vault_root
    )
    # Mock some internal components to prevent real execution/DB calls where complex
    orc.identity = MagicMock()
    orc.identity.sign_manifest.return_value = {"signature": "mock_sig", "signer": "test"}
    orc._save_manifest = MagicMock()
    orc._update_run_status = MagicMock()
    orc._create_run_record = MagicMock(return_value=123)
    orc.dpk = MagicMock()
    orc.dpk.authorize_execution.return_value = True
    orc.dpk.compute_signature_hash.return_value = "hash123"
    
    # Mock _perform_ppn_check to bypass deep neural logic
    mock_state = MagicMock()
    mock_state.budget_used = 0.5
    mock_state.coherence = 0.8
    mock_state.phi_total = 1.0
    mock_state.affective_tension_psi = 0.5
    mock_state.betti = [1, 1, 1]
    orc._perform_ppn_check = MagicMock(return_value=(True, mock_state))
    
    return orc

@pytest.mark.asyncio
async def test_orchestrator_initialization(orchestrator):
    assert orchestrator.agent_id == "test_exec"
    assert orchestrator.vault is not None
    assert orchestrator.ace is not None
    assert orchestrator.planner is not None
    assert orchestrator.critic is not None

@pytest.mark.asyncio
async def test_preview_plan(orchestrator):
    plan = await orchestrator.preview_plan("Test objective")
    assert isinstance(plan, list)
    assert len(plan) == 2  # Based on mock_router's get_structured_plan

@pytest.mark.asyncio
async def test_cancel_run(orchestrator, db_session):
    # Create a real DB run to cancel
    run = Run(
        objective="Test Run",
        status="running",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    task_rec = TaskRecord(
        run_id=run.id,
        task_dag_id="task_1",
        action="test",
        args="{}",
        status="pending"
    )
    db_session.add(task_rec)
    db_session.commit()

    with patch("backend.orchestrator.db_engine", db_session.get_bind()):
        success = await orchestrator.cancel_run(run.id)
        assert success is True

    db_session.refresh(run)
    db_session.refresh(task_rec)
    assert run.status == "failed"
    assert task_rec.status == "failed"

@pytest.mark.asyncio
async def test_background_services(orchestrator):
    orchestrator.heartbeat.start = AsyncMock()
    orchestrator.heartbeat.stop = AsyncMock()
    
    await orchestrator.start_background_services()
    assert orchestrator.heartbeat_task is not None
    
    await orchestrator.stop_background_services()
    orchestrator.heartbeat.stop.assert_awaited_once()

@pytest.mark.asyncio
async def test_execute_objective_success(orchestrator):
    # Mock executor to return successful tasks
    mock_task = MagicMock()
    mock_task.id = "step_1"
    mock_task.status = TaskStatus.COMPLETED
    mock_task.result = "Success"
    
    orchestrator.executor.execute_dag = AsyncMock(return_value={"step_1": mock_task})
    
    result = await orchestrator.execute_objective("Test success", "autonomous")
    assert result["status"] == "success"
    assert result["run_id"] == 123
    assert result["score"] == 0.88 # from mock_router.critique_result

@pytest.mark.asyncio
async def test_execute_objective_throttle(orchestrator):
    orchestrator.ace.should_throttle.return_value = True
    result = await orchestrator.execute_objective("Test throttle", "RESTRICTED")
    assert result["status"] == "halted"
    assert "Biometric stress limit" in result["reason"]

@pytest.mark.asyncio
async def test_execute_research(orchestrator):
    # Research mode has its own flow
    orchestrator.planner.router.get_response = AsyncMock(return_value='["query1"]')
    
    # Mock adapters
    mock_search = MagicMock()
    mock_search.execute = AsyncMock(return_value={"results": [{"link": "http://test.com"}]})
    mock_fetch = MagicMock()
    mock_fetch.execute = AsyncMock(return_value={"content": "fetched content"})
    
    orchestrator.adapter_registry.get = MagicMock(side_effect=lambda name: mock_search if name == "web_search" else mock_fetch)
    
    # The method uses self._save_manifest which we already mocked
    # We just want to check it completes and returns a dict
    result = await orchestrator.execute_research("Test research")
    assert isinstance(result, dict)
    assert result["status"] == "success"
    # The execute_research method writes the results to a file or returns a specific payload
    # Let's just check the sources or result contains the query
    assert "sources" in result or "result" in result

@pytest.mark.asyncio
async def test_handle_inbound_message(orchestrator):
    orchestrator.execute_objective = AsyncMock(return_value={"status": "success"})
    msg = {"body": "hello", "from": "user1", "protocol": "NOSTR"}
    await orchestrator.handle_inbound_message(msg)
    orchestrator.execute_objective.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_inbound_message_flow_mode_filtered(orchestrator):
    orchestrator.execute_objective = AsyncMock()
    orchestrator.ace.current_state = {"flow_mode": "DEEP_WORK"}
    msg = {"body": "hello", "from": "user1", "protocol": "NOSTR"}
    await orchestrator.handle_inbound_message(msg)
    # Should be ignored due to DEEP_WORK
    orchestrator.execute_objective.assert_not_called()
