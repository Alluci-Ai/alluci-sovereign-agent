import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.engine.planner import Planner

@pytest.mark.asyncio
async def test_planner_psi_prompt():
    router = MagicMock()
    # Mock return value to satisfy build_and_validate_dag
    router.get_structured_plan = AsyncMock(return_value={"steps": [{"id": "1", "tool": "test"}]})
    planner = Planner(router)
    
    await planner.generate_plan("task", psi=0.88)
    
    # Verify prompt contains psi
    call_args = router.get_structured_plan.call_args[0][0]
    assert "AFFECTIVE TENSION (psi): 0.88" in call_args
