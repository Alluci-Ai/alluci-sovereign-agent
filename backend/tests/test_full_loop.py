import pytest
torch = pytest.importorskip("torch")
from unittest.mock import patch, MagicMock
from backend.orchestrator import ExecutiveOrchestrator

@pytest.mark.asyncio
async def test_objective_execute_success(mock_router, temp_db, mock_adapter_registry, mock_settings):
    """
    Integration test for the full Objective -> Plan -> Execute -> Critique cycle.
    """
    from backend.engine.planner import Planner
    from backend.engine.executor import Executor
    from backend.engine.critic import Critic
    from backend.skill_manager import SkillManager
    from backend.security.vault import VaultManager
    from cryptography.fernet import Fernet
    import tempfile
    
    key = Fernet.generate_key().decode()
    import types
    with tempfile.TemporaryDirectory() as vdir, \
         patch('backend.orchestrator.db_engine', temp_db), \
         patch.object(ExecutiveOrchestrator, '_perform_ppn_check', return_value=(True, types.SimpleNamespace(
             coherence=1.0,
             budget_used=0.1,
             affective_tension_psi=0.1,
             phi_total=1.0,
             betti=[1, 0, 0]
         ))):
        
        vault = VaultManager(key, vault_root=vdir)
        skill_mgr = SkillManager(vault)
        
        # Mock ACE and BTM to return numeric psi
        mock_ace = MagicMock()
        mock_ace.get_affective_state.return_value = {}
        mock_ace.btm.psi_from_state.return_value = 0.1
        
        # 1. Initialize Orchestrator with mocks
        orchestrator = ExecutiveOrchestrator(
            router=mock_router,
            vault=vault,
            ace=mock_ace,
            settings=mock_settings,
            skill_manager=skill_mgr
        )
        
        # Override the sub-components with our test ones
        orchestrator.planner = Planner(mock_router)
        orchestrator.executor = Executor(mock_adapter_registry, lambda: temp_db, max_concurrent=2)
        orchestrator.critic = Critic(mock_router, threshold=0.5)
        
        # 2. Mock model responses
        mock_router.get_structured_plan.return_value = {
            "steps": [
                {"id": "step1", "description": "Search something", "tool": "web_search", "dependencies": []}
            ]
        }
        mock_router.critique_result.return_value = {"score": 0.9, "feedback": "Excellent task completion."}
        
        # 3. Execute full cycle
        result = await orchestrator.execute_objective("Explain the Polytope protocol", "SEMI_AUTONOMOUS")
        
        # 4. Verify results
        assert result["status"] == "success"
        assert result["score"] == 0.9
        assert "result" in result
        
        # Parse the JSON results summary
        import json
        summary = json.loads(result["result"])
        assert "step1" in summary
        assert summary["step1"] == "adapter output"
