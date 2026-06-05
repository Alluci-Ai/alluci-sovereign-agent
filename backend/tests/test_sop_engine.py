import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from sqlmodel import Session, create_engine, SQLModel
from backend.models import SOPRecord
from backend.sop.engine import SOPEngine

@pytest.fixture
def sqlite_engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    yield engine

@pytest.fixture
def sop_engine(sqlite_engine):
    return SOPEngine(engine=sqlite_engine)

@pytest.mark.asyncio
async def test_register_and_get_sop(sop_engine):
    steps = [{"action": "test", "description": "test step"}]
    sop_id = await sop_engine.register_sop("Test SOP", "Description", steps)
    
    sop = sop_engine.get_sop(sop_id)
    assert sop is not None
    assert sop.name == "Test SOP"
    assert sop.description == "Description"
    assert sop.steps["steps"] == steps

def test_list_sops(sop_engine, sqlite_engine):
    with Session(sqlite_engine) as session:
        sop1 = SOPRecord(name="SOP1", description="desc1", steps={"steps":[]}, is_active=True)
        sop2 = SOPRecord(name="SOP2", description="desc2", steps={"steps":[]}, is_active=False)
        session.add(sop1)
        session.add(sop2)
        session.commit()
        
    sops = sop_engine.list_sops()
    assert len(sops) == 1
    assert sops[0].name == "SOP1"

@pytest.mark.asyncio
@patch("backend.services.orchestrator")
async def test_execute_sop_success(mock_orchestrator, sop_engine):
    mock_orchestrator._create_run_record.return_value = 1
    mock_orchestrator.execute_objective = AsyncMock(return_value={"status": "success", "result": "done"})
    
    steps = [{"action": "step1", "description": "do step 1"}]
    sop_id = await sop_engine.register_sop("Test SOP", "desc", steps)
    
    res = await sop_engine.execute_sop(sop_id, context_overrides={"foo": "bar"})
    assert res["status"] == "success"
    assert len(res["history"]) == 1
    assert res["history"][0]["status"] == "success"
    
    mock_orchestrator._create_run_record.assert_called_once()
    mock_orchestrator.execute_objective.assert_called_once()
    mock_orchestrator._update_run_status.assert_called()

@pytest.mark.asyncio
@patch("backend.services.orchestrator")
async def test_execute_sop_failure(mock_orchestrator, sop_engine):
    mock_orchestrator._create_run_record.return_value = 1
    mock_orchestrator.execute_objective = AsyncMock(return_value={"status": "failed", "reason": "error"})
    
    steps = [{"action": "step1", "description": "do step 1"}, {"action": "step2"}]
    sop_id = await sop_engine.register_sop("Test SOP", "desc", steps)
    
    res = await sop_engine.execute_sop(sop_id)
    assert res["status"] == "failed"
    assert res["step"] == 1
    assert len(res["history"]) == 1
    
    mock_orchestrator.execute_objective.assert_called_once()

@pytest.mark.asyncio
@patch("backend.services.orchestrator")
async def test_execute_sop_not_found(mock_orchestrator, sop_engine):
    with pytest.raises(ValueError, match="not found"):
        await sop_engine.execute_sop(999)

@pytest.mark.asyncio
@patch("backend.sop.engine.logger")
async def test_execute_sop_exception(mock_logger, sop_engine):
    # If orchestrator is not initialized (mock it as None in services)
    steps = [{"action": "step1"}]
    sop_id = await sop_engine.register_sop("Test SOP", "desc", steps)
    
    with patch("backend.services.orchestrator", None):
        with pytest.raises(RuntimeError, match="Orchestrator not initialized"):
            await sop_engine.execute_sop(sop_id)

@pytest.mark.asyncio
@patch("backend.services.orchestrator")
async def test_execute_sop_crash(mock_orchestrator, sop_engine):
    mock_orchestrator._create_run_record.return_value = 1
    mock_orchestrator.execute_objective.side_effect = Exception("System Crash")
    
    steps = [{"action": "step1"}]
    sop_id = await sop_engine.register_sop("Test SOP", "desc", steps)
    
    with pytest.raises(Exception, match="System Crash"):
        await sop_engine.execute_sop(sop_id)
