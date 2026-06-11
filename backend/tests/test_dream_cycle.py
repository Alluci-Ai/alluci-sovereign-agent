import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from backend.engine.dream_cycle import CognitiveDistiller, DreamingCycleDaemon, SleepStateOrchestrator
from backend.ace.affect_kernel import AffectiveState

@pytest.fixture
def mock_hlsm():
    hlsm = MagicMock()
    hlsm.l1_get_recent = AsyncMock(return_value=[MagicMock(content="memory1")])
    hlsm.l2_store = AsyncMock()
    return hlsm

@pytest.fixture
def mock_router():
    router = MagicMock()
    router.get_response = AsyncMock(return_value="Semantic Truth")
    return router

@pytest.mark.asyncio
async def test_cognitive_distiller(mock_hlsm, mock_router):
    distiller = CognitiveDistiller(mock_hlsm, mock_router)
    await distiller.distill_day_logs()
    
    mock_hlsm.l1_get_recent.assert_called_once()
    mock_router.get_response.assert_called_once()
    mock_hlsm.l2_store.assert_called_once()

@pytest.mark.asyncio
async def test_cognitive_distiller_empty(mock_hlsm, mock_router):
    mock_hlsm.l1_get_recent = AsyncMock(return_value=[])
    distiller = CognitiveDistiller(mock_hlsm, mock_router)
    await distiller.distill_day_logs()
    
    mock_router.get_response.assert_not_called()

@pytest.mark.asyncio
async def test_dreaming_daemon_skip():
    # Will skip because MLX isn't fully mocked
    daemon = DreamingCycleDaemon("test_path")
    await daemon.execute_nightly_optimization("agent_1")
    await daemon.execute_micro_tuning_step()

@pytest.mark.asyncio
@patch("psutil.virtual_memory")
async def test_sleep_orchestrator(mock_vm, mock_hlsm, mock_router):
    mock_mem = MagicMock()
    mock_mem.available = 4 * 1024 * 1024 * 1024 # 4GB
    mock_vm.return_value = mock_mem
    
    orchestrator = SleepStateOrchestrator(mock_hlsm, mock_router, MagicMock())
    affect = AffectiveState(arousal=100.0, tension=100.0)
    
    assert await orchestrator.evaluate_sleep_trigger(affect) is True
    
    # Try high arousal
    affect = AffectiveState(arousal=300.0, tension=100.0)
    assert await orchestrator.evaluate_sleep_trigger(affect) is False

@pytest.mark.asyncio
@patch("psutil.virtual_memory")
async def test_sleep_orchestrator_insufficient_ram(mock_vm, mock_hlsm, mock_router):
    mock_mem = MagicMock()
    mock_mem.available = 1 * 1024 * 1024 * 1024 # 1GB
    mock_vm.return_value = mock_mem
    
    orchestrator = SleepStateOrchestrator(mock_hlsm, mock_router, MagicMock())
    affect = AffectiveState(arousal=100.0, tension=100.0)
    assert await orchestrator.evaluate_sleep_trigger(affect) is False

@pytest.mark.asyncio
@patch("sqlmodel.Session")
async def test_trigger_dream_cycle(mock_session_cls, mock_hlsm, mock_router):
    orchestrator = SleepStateOrchestrator(mock_hlsm, mock_router, MagicMock())
    orchestrator.distiller.distill_day_logs = AsyncMock()
    orchestrator.teacher_distiller.execute_nightly_optimization = AsyncMock()
    orchestrator.teacher_distiller.execute_micro_tuning_step = AsyncMock()
    orchestrator.trainer.run_training_step = AsyncMock()
    
    mock_session = MagicMock()
    mock_session.exec.return_value.all.return_value = [MagicMock(id="agent_1")]
    mock_session_cls.return_value.__enter__.return_value = mock_session
    
    await orchestrator.trigger_dream_cycle()
    
    orchestrator.distiller.distill_day_logs.assert_called_once()
    assert orchestrator.teacher_distiller.execute_nightly_optimization.call_count == 2 # agent_1 + executive
    orchestrator.teacher_distiller.execute_micro_tuning_step.assert_called_once()
