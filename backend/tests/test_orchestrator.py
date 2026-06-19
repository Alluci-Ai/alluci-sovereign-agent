import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock, ANY
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
        autonomy_level="autonomous",
        status=RunStatus.ACTIVE,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    task_rec = TaskRecord(
        run_id=run.id,
        task_id=1,
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
    
    with patch("backend.task_queue.record_result") as mock_record:
        # Check that it completes
        await orchestrator._run_research("Test research", "task_123")
        assert orchestrator.planner.router.get_response.call_count == 2
        mock_record.assert_called_once()

@pytest.mark.asyncio
async def test_handle_inbound_message(orchestrator):
    """Inbound messages addressed to Alluci use the direct LLM conversational path (not execute_objective)."""
    mock_router = AsyncMock()
    # First call is classification (returns JSON), second is the conversational response
    mock_router.get_response = AsyncMock(side_effect=['{"is_objective": false}', "Hi there!"])
    orchestrator._build_system_context = AsyncMock(return_value="You are Alluci.")
    msg = {"body": "Alluci hello", "from": "user1", "protocol": "NOSTR"}
    with patch("backend.services.router", mock_router), \
         patch("backend.services.channel_registry", {"nostr": AsyncMock(is_connected=True, send=AsyncMock(return_value={"status": "success"}))}):
        await orchestrator.handle_inbound_message(msg)
    assert mock_router.get_response.call_count == 2

@pytest.mark.asyncio
async def test_handle_inbound_message_not_addressed_to_alluci(orchestrator):
    """Messages not addressed to Alluci are stored to H-LSM but do not trigger execution."""
    orchestrator.execute_objective = AsyncMock()
    msg = {"body": "hey whats up", "from": "user1", "protocol": "NOSTR"}
    await orchestrator.handle_inbound_message(msg)
    orchestrator.execute_objective.assert_not_called()

@pytest.mark.asyncio
async def test_handle_inbound_message_flow_mode_filtered(orchestrator):
    orchestrator.execute_objective = AsyncMock()
    orchestrator.ace.current_state = {"flow_mode": "DEEP_WORK"}
    msg = {"body": "Alluci hello", "from": "user1", "protocol": "NOSTR"}
    await orchestrator.handle_inbound_message(msg)
    # Should be ignored due to DEEP_WORK
    orchestrator.execute_objective.assert_not_called()

@pytest.mark.asyncio
async def test_ws_gateway_property(orchestrator):
    mock_ws = MagicMock()
    orchestrator.heartbeat = MagicMock()
    orchestrator.ws_gateway = mock_ws
    assert orchestrator.ws_gateway == mock_ws
    assert orchestrator.heartbeat.ws_gateway == mock_ws

@pytest.mark.asyncio
async def test_broadcast_artifact(orchestrator):
    mock_ws = AsyncMock()
    orchestrator.ws_gateway = mock_ws
    await orchestrator.broadcast_artifact("test", "content", "markdown")
    mock_ws.broadcast_event.assert_awaited_once_with(
        'orchestrator.artifact.updated',
        {"title": "test", "content": "content", "language": "markdown", "timestamp": ANY}
    )

@pytest.mark.asyncio
async def test_handle_task_complete(orchestrator):
    mock_ws = AsyncMock()
    orchestrator.ws_gateway = mock_ws
    
    # Artifact creation task
    task = MagicMock()
    task.action = "write_file"
    task.result = "some long text " * 10
    task.args = {"filename": "test.py"}
    
    await orchestrator._handle_task_complete(task)
    mock_ws.broadcast_event.assert_awaited_once()

@pytest.mark.asyncio
async def test_build_system_context(orchestrator):
    orchestrator.skill_manager = MagicMock()
    orchestrator.skill_manager.list_skills = AsyncMock(return_value=[{"name": "test_skill", "description": "desc", "verified": True}])
    
    orchestrator.hlsm = MagicMock()
    mock_ctx = MagicMock()
    mock_ctx.to_prompt_block.return_value = "MEMORY_BLOCK"
    orchestrator.hlsm.retrieve_context = AsyncMock(return_value=mock_ctx)
    
    # Manifest mock
    orchestrator.vault.retrieve_secret = AsyncMock(return_value={
        "identityCore": "Core test",
        "reasoningStyle": "Reason test",
        "frameworks": ["F1"],
        "mindsets": ["M1"],
        "methodologies": ["M2"],
        "logic": ["L1"],
        "chainsOfThought": ["COT"],
        "bestPractices": ["BP"],
        "executionGraph": {"edges": [{"source": "A", "target": "B"}]}
    })
    
    ctx = await orchestrator._build_system_context(include_memory=True)
    assert "Core test" in ctx
    assert "F1" in ctx
    assert "A MUST PRECEDE B" in ctx
    assert "test_skill" in ctx
    assert "MEMORY_BLOCK" in ctx

@pytest.mark.asyncio
async def test_perform_ppn_check(orchestrator):
    # Remove the mock and test the real method
    delattr(orchestrator, "_perform_ppn_check")
    
    orchestrator.ace.btm.psi_from_state.return_value = 0.5
    
    orchestrator.ppn = MagicMock()
    import torch
    orchestrator.ppn.return_value = (None, None, torch.tensor([1,1,1]), None, 1.0, 0.5, 0.8, 1.0, 1.0, None)
    orchestrator.ppn.extract_simplex_counts.return_value = (3, 2, 1)
    
    orchestrator.dpk.compute_signature_hash.return_value = "hash123"
    orchestrator.dpk.verify_manifold_integrity.return_value = (True, "OK")
    
    ok, state = orchestrator._perform_ppn_check("test obj", "autonomous")
    assert ok is True
    assert state.vertices_V == 3

@pytest.mark.asyncio
async def test_compact_all_memory(orchestrator):
    orchestrator.hlsm = AsyncMock()
    
    mock_mem1 = MagicMock()
    mock_mem1.source = "system"
    mock_mem1.content = "mem1"
    mock_mem1.id = 1
    
    orchestrator.hlsm.l1_get_recent.return_value = [mock_mem1]
    
    orchestrator.planner.router.get_response = AsyncMock(return_value="synthesis")
    
    await orchestrator.compact_all_memory()
    
    orchestrator.hlsm.l1_store.assert_awaited_once_with(
        content="synthesis", 
        source="daily_synthesis",
        topological_importance=1.5
    )
    orchestrator.hlsm.delete.assert_awaited_once_with(1)

@pytest.mark.asyncio
async def test_multi_agent_delegate(orchestrator):
    # This tests lines 829-856 which are the multi_agent_delegate method of orchestrator
    orchestrator.planner = MagicMock()
    orchestrator.planner.router = MagicMock()
    
    with patch("backend.orchestrator.asyncio.create_task") as mock_create_task:
        res = await orchestrator.multi_agent_delegate("sub1", "test objective")
        assert res["status"] == "spawned"
        assert res["agent_id"] == "sub1"
        mock_create_task.assert_called_once()
