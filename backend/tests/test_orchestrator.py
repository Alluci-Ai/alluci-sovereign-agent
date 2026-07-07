import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_orchestrator_tool_flagging():
    from backend.orchestrator import ExecutiveOrchestrator
    
    mock_router = MagicMock()
    mock_vault = MagicMock()
    mock_ace = MagicMock()
    mock_settings = MagicMock()
    
    orch = ExecutiveOrchestrator(router=mock_router, vault=mock_vault, ace=mock_ace, settings=mock_settings)
    
    called_with_tool_action = False
    original_check = orch._perform_ppn_check
    
    def mock_check(*args, **kwargs):
        nonlocal called_with_tool_action
        if kwargs.get("is_tool_action", False):
            called_with_tool_action = True
        return True, None
        
    orch._perform_ppn_check = mock_check
    orch.executor = AsyncMock()
    orch.executor._execute_adapter.return_value = "Success"
    try:
        await orch.execute_tool_action("test_tool", {"arg": "value"})
        assert called_with_tool_action is True
    finally:
        orch._perform_ppn_check = original_check
