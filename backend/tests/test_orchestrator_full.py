import pytest
pytestmark = pytest.mark.unit

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from backend.orchestrator import ExecutiveOrchestrator
from backend.models import Run, TaskRecord, RunStatus

@pytest.fixture
def mock_orchestrator(tmp_path, temp_db):
    router = AsyncMock()
    vault = AsyncMock()
    ace = MagicMock()
    settings = MagicMock()
    settings.MAX_AUTONOMY_RETRIES = 3
    settings.MAX_CONTEXT_TOKENS = 100
    skill_manager = AsyncMock()
    approval_manager = AsyncMock()
    analytics = MagicMock()
    vault_root = str(tmp_path)
    memory_manager = AsyncMock()
    hlsm = AsyncMock()

    orch = ExecutiveOrchestrator(
        router=router, vault=vault, ace=ace, settings=settings,
        skill_manager=skill_manager, approval_manager=approval_manager,
        analytics=analytics, vault_root=vault_root, memory_manager=memory_manager,
        hlsm_manager=hlsm
    )
    orch.logger = MagicMock()
    orch.heartbeat = AsyncMock()
    orch.planner = AsyncMock()
    orch.executor = AsyncMock()
    orch.critic = AsyncMock()
    orch.identity = MagicMock()
    orch.ws_gateway = AsyncMock()
    orch.dpk = MagicMock()
    orch.dpk.project_state = MagicMock(return_value=MagicMock(phi_total=0.9))
    
    affective_state = MagicMock()
    affective_state.tension = 512.0
    affective_state.valence = 512.0
    orch.ace.get_affective_state.return_value = affective_state
    orch.ace.btm.psi_from_state = MagicMock(return_value=0.5)
    return orch



@pytest.mark.asyncio
async def test_preview_plan(mock_orchestrator):
    mock_orchestrator.planner.generate_plan.return_value = {
        "t1": MagicMock(action="a1", args={"description": "d"}, dependencies=[], priority_score=1)
    }
    mock_orchestrator._build_system_context = AsyncMock(return_value="context")
    res = await mock_orchestrator.preview_plan("obj")
    assert len(res) == 1
    assert res[0]["action"] == "a1"

@pytest.mark.asyncio
async def test_background_services(mock_orchestrator):
    await mock_orchestrator.start_background_services()
    assert mock_orchestrator.heartbeat_task is not None
    await mock_orchestrator.stop_background_services()
    mock_orchestrator.heartbeat.stop.assert_awaited_once()

@pytest.mark.asyncio
async def test_handle_inbound_message_exceptions(mock_orchestrator):
    mock_orchestrator.hlsm.encode_message.side_effect = Exception("encode err")
    mock_orchestrator.execute_objective = AsyncMock(return_value="res")
    mock_orchestrator.analytics = MagicMock()
    
    await mock_orchestrator.handle_inbound_message({"body": "hi", "from": "user", "protocol": "web"})
    # encode_message exception should be logged but not raise
    
    mock_orchestrator.execute_objective.side_effect = Exception("exec err")
    await mock_orchestrator.handle_inbound_message({"body": "hi", "from": "user", "protocol": "web"})
    mock_orchestrator.analytics.record_message.assert_called()

@pytest.mark.asyncio
async def test_build_system_context_exceptions(mock_orchestrator):
    mock_orchestrator.vault.retrieve_secret.side_effect = Exception("vault err")
    mock_orchestrator.skill_manager.list_skills.side_effect = Exception("skill err")
    mock_orchestrator.hlsm.retrieve_context.side_effect = Exception("hlsm err")
    
    res = await mock_orchestrator._build_system_context(include_memory=True)
    assert isinstance(res, str)
    
@pytest.mark.asyncio
async def test_perform_ppn_check_exception(mock_orchestrator):
    mock_orchestrator.ace.get_affective_state.side_effect = Exception("ace err")
    valid, state = mock_orchestrator._perform_ppn_check("test", "test")
    assert valid is False
    assert state is None

@pytest.mark.asyncio
async def test_execute_objective_research(mock_orchestrator):
    mock_orchestrator.execute_research = AsyncMock(return_value={"res": "research"})
    res = await mock_orchestrator.execute_objective("test", "auto", mode="research")
    assert res == {"res": "research"}
    
@pytest.mark.asyncio
async def test_execute_objective_manifold_unstable(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check", return_value=(False, None)):
        res = await mock_orchestrator.execute_objective("test", "auto")
        assert res["status"] == "halted"

@pytest.mark.asyncio
async def test_execute_objective_rupture(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check", return_value=(True, MagicMock())):
        mock_orchestrator.health_monitor = MagicMock()
        mock_orchestrator.health_monitor.evaluate.return_value = {
            "status": "CRITICAL", "is_ruptured": True, "pvt": {"T": 1.0}, "issues": []
        }
        res = await mock_orchestrator.execute_objective("test", "auto")
        assert res["status"] == "halted"
        assert "rupture" in res["reason"].lower()

@pytest.mark.asyncio
async def test_execute_objective_planning_failed(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check", return_value=(True, None)):
        mock_orchestrator.health_monitor = MagicMock(evaluate=MagicMock(return_value={"status": "OK", "is_ruptured": False}))
        mock_orchestrator._create_run_record = MagicMock(return_value=1)
        mock_orchestrator._update_run_status = MagicMock()
        mock_orchestrator.planner.generate_plan.side_effect = Exception("plan boom")
        
        res = await mock_orchestrator.execute_objective("test", "auto")
        assert res["status"] == "failed"

@pytest.mark.asyncio
async def test_execute_objective_compaction(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check", return_value=(True, None)):
        mock_orchestrator.health_monitor = MagicMock(evaluate=MagicMock(return_value={"status": "OK", "is_ruptured": False}))
        mock_orchestrator._create_run_record = MagicMock(return_value=1)
        mock_orchestrator._update_run_status = MagicMock()
        mock_orchestrator._build_system_context = AsyncMock(return_value="large text " * 1000)
        mock_orchestrator.settings.MAX_CONTEXT_TOKENS = 10
        mock_orchestrator.planner.generate_plan.return_value = {}
        mock_orchestrator.harmonic = MagicMock(rank_actions=MagicMock(return_value=[]))
        mock_orchestrator.identity.sign_manifest.return_value = {"signature": "s", "signer": "me"}
        
        # mock execute loop to exit immediately by critic passing
        mock_orchestrator.executor.execute_dag.return_value = {}
        mock_orchestrator.critic.evaluate.return_value = (True, 1.0, "ok")
        
        # Exception in DPk project_state to trigger 575-579
        mock_orchestrator.dpk.project_state.side_effect = Exception("pruning failed")
        
        res = await mock_orchestrator.execute_objective("test", "auto")
        assert res["status"] == "success"

@pytest.mark.asyncio
async def test_execute_objective_refine_plan_exception(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check", return_value=(True, None)):
        mock_orchestrator.health_monitor = MagicMock(evaluate=MagicMock(return_value={"status": "OK", "is_ruptured": False}))
        mock_orchestrator._create_run_record = MagicMock(return_value=1)
        mock_orchestrator._update_run_status = MagicMock()
        mock_orchestrator._build_system_context = AsyncMock(return_value="small text")
        mock_orchestrator.planner.generate_plan.return_value = {}
        mock_orchestrator.harmonic = MagicMock(rank_actions=MagicMock(return_value=[]))
        mock_orchestrator.identity.sign_manifest.return_value = {"signature": "s", "signer": "me"}
        mock_orchestrator.executor.execute_dag.return_value = {}
        mock_orchestrator.critic.evaluate.return_value = (False, 0.5, "needs work")
        mock_orchestrator.planner.refine_plan.side_effect = Exception("refine boom")
        
        res = await mock_orchestrator.execute_objective("test", "auto")
        assert res["status"] == "failed"

@pytest.mark.asyncio
async def test_execute_research_json_fallback(mock_orchestrator):
    mock_orchestrator.planner.router.get_response.side_effect = ["invalid json", "report"]
    mock_search = AsyncMock()
    mock_search.execute = AsyncMock(return_value={"results": []})
    mock_fetch = AsyncMock()
    mock_fetch.execute = AsyncMock(return_value={"text": ""})
    
    mock_orchestrator.adapter_registry.get = MagicMock(side_effect=lambda name: mock_search if name == "web_search" else mock_fetch)
    
    await mock_orchestrator._run_research("obj", "task_123")
    assert mock_orchestrator.planner.router.get_response.call_count == 2

@pytest.mark.asyncio
async def test_compact_all_memory(mock_orchestrator):
    mock_orchestrator.hlsm.l1_get_recent.return_value = [
        MagicMock(source="test", content="c1"),
        MagicMock(source="daily_synthesis", content="c2")
    ]
    mock_orchestrator.planner.router.get_response.return_value = "summary"
    await mock_orchestrator.compact_all_memory()
    mock_orchestrator.hlsm.l1_store.assert_awaited_once()

    # Empty test
    mock_orchestrator.hlsm.l1_get_recent.return_value = []
    await mock_orchestrator.compact_all_memory()

    # Exception test
    mock_orchestrator.hlsm.l1_get_recent.return_value = [MagicMock(source="test", content="c1")]
    mock_orchestrator.planner.router.get_response.side_effect = Exception("boom")
    await mock_orchestrator.compact_all_memory()

def test_persistence_methods(mock_orchestrator):
    from backend.database import engine
    from sqlmodel import Session, SQLModel
    SQLModel.metadata.create_all(engine)
    
    with patch("backend.orchestrator.db_engine", engine):
        rid = mock_orchestrator._create_run_record("obj", "auto")
        from backend.models import RunStatus
        mock_orchestrator._update_run_status(rid, RunStatus.COMPLETED, 1.0, "f")
        mock_orchestrator._save_manifest(rid, "sig")
        
        with Session(engine) as session:
            r = session.get(Run, rid)
            assert r.status == RunStatus.COMPLETED
            assert r.score == 1.0
            assert r.manifest_signature == "sig"
