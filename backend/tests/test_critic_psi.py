import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, MagicMock
from backend.engine.critic import Critic

@pytest.mark.asyncio
async def test_critic_psi_weighting():
    router = MagicMock()
    router.critique_result = AsyncMock(return_value={"score": 0.8, "feedback": "ok"})
    critic = Critic(router, threshold=0.75)
    
    # 1. Low psi (0.0). Threshold = 0.75. Score 0.8 -> Passed
    passed, score, _ = await critic.evaluate("obj", "res", psi=0.0)
    assert passed
    
    # 2. High psi (1.0). Threshold = 0.75 + 0.15 = 0.90. Score 0.8 -> Failed
    passed, score, _ = await critic.evaluate("obj", "res", psi=1.0)
    assert not passed
