import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from backend.orchestrator import ExecutiveOrchestrator

@pytest.fixture
def mock_orchestrator(tmp_path):
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
    orch.avl = MagicMock()
    orch.health_monitor = MagicMock()
    return orch

@pytest.mark.asyncio
async def test_execute_objective_execution_loop(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check") as mock_ppn:
        poly_state = MagicMock()
        poly_state.betti = [1, 1, 1]
        poly_state.affective_tension_psi = 0.5
        mock_ppn.return_value = (True, poly_state)
        
        affective_state = MagicMock()
        affective_state.tension = 512.0
        affective_state.valence = 512.0
        mock_orchestrator.ace.get_affective_state.return_value = affective_state
        
        mock_orchestrator.health_monitor.evaluate.return_value = {"status": "OK", "is_ruptured": False}
        mock_orchestrator._create_run_record = MagicMock(return_value=1)
        mock_orchestrator._update_run_status = MagicMock()
        mock_orchestrator._build_system_context = AsyncMock(return_value="context")
        
        # Planner
        task_mock = MagicMock()
        task_mock.dict.return_value = {}
        task_mock.model_dump.return_value = {}
        mock_orchestrator.planner.generate_plan.return_value = {"t1": task_mock}
        mock_orchestrator.harmonic = MagicMock()
        mock_orchestrator.harmonic.rank_actions.return_value = [task_mock]
        mock_orchestrator.identity.sign_manifest.return_value = {"signature": "s", "signer": "me"}
        
        # Execution updates
        updated_task = MagicMock()
        updated_task.id = "t1"
        updated_task.status = "success"
        updated_task.result = "done"
        mock_orchestrator.executor.execute_dag.return_value = {"t1": updated_task}
        
        # Critic first fails, then passes
        mock_orchestrator.critic.evaluate.side_effect = [
            (False, 0.5, "needs work"),
            (True, 1.0, "perfect")
        ]
        mock_orchestrator.ace.btm.psi_from_state = MagicMock(return_value=0.5)
        
        # Geodesic
        import torch
        mock_orchestrator.geodesic_cost = MagicMock()
        mock_orchestrator.geodesic_cost.compute.return_value = 0.01
        
        # AVL passes
        mock_orchestrator.avl.verify.return_value = (True, "OK")
        
        # Refine plan
        mock_orchestrator.planner.refine_plan.return_value = {"t1": task_mock}
        
        with patch("backend.orchestrator.sync_audit_entry", new_callable=AsyncMock) as mock_audit:
            res = await mock_orchestrator.execute_objective("test obj", "auto")
            assert res["status"] == "success"
            mock_audit.assert_awaited()
            
        mock_orchestrator.hlsm.encode_from_execution.assert_awaited()

@pytest.mark.asyncio
async def test_execute_objective_avl_rejection(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check") as mock_ppn:
        poly_state = MagicMock()
        mock_ppn.return_value = (True, poly_state)
        mock_orchestrator.health_monitor.evaluate.return_value = {"status": "OK", "is_ruptured": False}
        mock_orchestrator._create_run_record = MagicMock(return_value=1)
        mock_orchestrator._update_run_status = MagicMock()
        mock_orchestrator._build_system_context = AsyncMock(return_value="context")
        mock_orchestrator.planner.generate_plan.return_value = {}
        mock_orchestrator.harmonic = MagicMock(rank_actions=MagicMock(return_value=[]))
        mock_orchestrator.identity.sign_manifest.return_value = {"signature": "s", "signer": "me"}
        mock_orchestrator.executor.execute_dag.return_value = {}
        
        mock_orchestrator.critic.evaluate.return_value = (False, 0.5, "needs work")
        mock_orchestrator.avl.verify.return_value = (False, "Violation!")
        
        with patch("backend.orchestrator.sync_audit_entry", new_callable=AsyncMock):
            res = await mock_orchestrator.execute_objective("test obj", "auto")
            assert res["status"] == "failed"
            assert res["reason"] == "Violation!"

@pytest.mark.asyncio
async def test_execute_objective_high_tension_gate(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check") as mock_ppn:
        poly_state = MagicMock()
        mock_ppn.return_value = (True, poly_state)
        mock_orchestrator.health_monitor.evaluate.return_value = {"status": "OK", "is_ruptured": False}
        mock_orchestrator._create_run_record = MagicMock(return_value=1)
        mock_orchestrator._update_run_status = MagicMock()
        mock_orchestrator._build_system_context = AsyncMock(return_value="context")
        mock_orchestrator.planner.generate_plan.return_value = {}
        mock_orchestrator.harmonic = MagicMock(rank_actions=MagicMock(return_value=[]))
        mock_orchestrator.identity.sign_manifest.return_value = {"signature": "s", "signer": "me"}
        mock_orchestrator.executor.execute_dag.return_value = {}
        
        mock_orchestrator.critic.evaluate.return_value = (False, 0.5, "needs work")
        mock_orchestrator.avl.verify.return_value = (True, "OK")
        # High tension in self-correction
        mock_orchestrator.ace.btm.psi_from_state = MagicMock(return_value=0.95)
        
        with patch("backend.orchestrator.sync_audit_entry", new_callable=AsyncMock):
            res = await mock_orchestrator.execute_objective("test obj", "auto")
            assert res["status"] == "failed"
            assert "gated" in res["reason"].lower()

@pytest.mark.asyncio
async def test_execute_objective_cycle_latency(mock_orchestrator):
    with patch.object(mock_orchestrator, "_perform_ppn_check") as mock_ppn:
        poly_state = MagicMock()
        mock_ppn.return_value = (True, poly_state)
        mock_orchestrator.health_monitor.evaluate.return_value = {"status": "OK", "is_ruptured": False}
        mock_orchestrator._create_run_record = MagicMock(return_value=1)
        mock_orchestrator._update_run_status = MagicMock()
        mock_orchestrator._build_system_context = AsyncMock(return_value="context")
        mock_orchestrator.planner.generate_plan.return_value = {}
        mock_orchestrator.harmonic = MagicMock(rank_actions=MagicMock(return_value=[]))
        mock_orchestrator.identity.sign_manifest.return_value = {"signature": "s", "signer": "me"}
        mock_orchestrator.executor.execute_dag.return_value = {}
        mock_orchestrator.critic.evaluate.return_value = (True, 1.0, "ok")
        mock_orchestrator.ace.btm.psi_from_state = MagicMock(return_value=0.5)
        
        time_counter = [0]
        def fake_time():
            time_counter[0] += 35
            return float(time_counter[0])
            
        with patch("time.time", side_effect=fake_time):
            with patch("backend.orchestrator.sync_audit_entry", new_callable=AsyncMock):
                res = await mock_orchestrator.execute_objective("obj", "auto")
                assert res["status"] == "success"
                mock_orchestrator.ace.inject_deadline_contraction.assert_called()

@pytest.mark.asyncio
async def test_multi_agent_delegate(mock_orchestrator):
    res = await mock_orchestrator.multi_agent_delegate("sub1", "do work")
    assert res["status"] == "spawned"
