import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock
from sqlmodel import Session, select

from backend.pcl import (
    ProactiveCognitionLoop, WorldModel, Opportunity,
    GoalStallDetector, GoalDeadlineDetector, UnresolvedBridgeDetector,
    InterventionJudge
)
from backend.models import PCLOpportunity, PCLWorldModelSnapshot, GoalRecord
from backend.config import settings

@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.PCL_CYCLE_INTERVAL = 1.0
    s.PCL_QUIET_START_HOUR = 22
    s.PCL_QUIET_END_HOUR = 7
    s.CRITIC_THRESHOLD = 0.75
    return s
@pytest.fixture
def mock_db_engine():
    return MagicMock()

@pytest.fixture
def mock_orchestrator():
    orchestrator = MagicMock()
    orchestrator.execute_objective = AsyncMock(return_value={"status": "success"})
    return orchestrator

@pytest.fixture
def mock_ace():
    ace = MagicMock()
    ace.get_affective_state.return_value = MagicMock(tension=100, valence=512, arousal=200)
    ace.current_state = {"flow_mode": "STANDARD"}
    return ace

@pytest.fixture
def mock_goal_engine():
    engine = MagicMock()
    engine.list_goals = AsyncMock(return_value=[])
    return engine

@pytest.fixture
def mock_hlsm():
    hlsm = MagicMock()
    hlsm.l1_search = AsyncMock(return_value=[])
    hlsm.l1_get_recent = AsyncMock(return_value=[])
    hlsm.l1_store = AsyncMock()
    return hlsm

@pytest.fixture
def pcl_engine(mock_db_engine, mock_orchestrator, mock_ace, mock_goal_engine, mock_hlsm, mock_settings):
    return ProactiveCognitionLoop(
        db_engine=mock_db_engine,
        orchestrator=mock_orchestrator,
        ace_engine=mock_ace,
        goal_engine=mock_goal_engine,
        hlsm_manager=mock_hlsm,
        settings=mock_settings,
        cycle_interval=1.0
    )
@pytest.mark.asyncio
async def test_world_model_building(pcl_engine, mock_goal_engine):
    # Setup mock goals
    from datetime import datetime, timezone
    mock_goal_engine.list_goals.return_value = [
        GoalRecord(
            id=1, title="Test Goal", deadline=datetime(2026, 12, 31, tzinfo=timezone.utc),
            priority="HIGH", status="active", metric_current=10, metric_target=100
        )
    ]
    
    world = await pcl_engine.build_world_model()
    
    assert len(world.active_goals) == 1
    assert world.active_goals[0].title == "Test Goal"
    assert world.active_goals[0].has_deadline is True
    assert world.current_flow_mode == "STANDARD"

@pytest.mark.asyncio
async def test_goal_stall_detector():
    detector = GoalStallDetector()
    world = WorldModel()
    
    # Not stalled
    world.active_goals = [
        MagicMock(id=1, title="Fresh", days_since_update=0.1, status="active", priority="HIGH", metric_current=0, metric_target=100)
    ]
    assert await detector.detect(world) is None
    
    # Stalled
    world.active_goals = [
        MagicMock(id=2, title="Stalled", days_since_update=3.0, status="active", priority="HIGH", metric_current=0, metric_target=100)
    ]
    opp = await detector.detect(world)
    assert opp is not None
    assert "Goal stalled" in opp.title
    assert opp.affects_goal_id == 2

@pytest.mark.asyncio
async def test_goal_deadline_detector():
    detector = GoalDeadlineDetector()
    world = WorldModel()
    
    # Approaching deadline (24 hours)
    goal = MagicMock(
        id=3, title="Closing", has_deadline=True, days_to_deadline=1.0, 
        metric_current=10, metric_target=100, status="active", priority="URGENT"
    )
    world.goals_at_risk = [goal]
    
    opp = await detector.detect(world)
    assert opp is not None
    assert "Deadline approaching" in opp.title
    assert opp.recommended_action == "execute" # Urgent deadline -> execute

@pytest.mark.asyncio
async def test_unresolved_bridge_detector():
    detector = UnresolvedBridgeDetector()
    world = WorldModel()
    
    from backend.pcl import BridgeThread
    world.unanswered_threads = [
        BridgeThread(bridge_id="telegram", sender="Alice", last_message="Hello?", hours_unanswered=5.0)
    ]
    
    opp = await detector.detect(world)
    assert opp is not None
    assert "Unanswered message" in opp.title
    assert opp.recommended_action == "execute"

@pytest.mark.asyncio
async def test_judge_intervention_logic(pcl_engine, mock_db_engine, mock_settings):
    judge = InterventionJudge(mock_db_engine, settings_obj=mock_settings)
    world = WorldModel(current_flow_mode="STANDARD")
    
    opp = Opportunity(
        id="test_opp", detector_name="Test", title="Test", description="Test",
        priority=3, confidence=0.9, recommended_action="notify", cooldown_minutes=60
    )
    
    # Mock database session for cooldown check
    mock_session = MagicMock()
    mock_session.__enter__.return_value = mock_session
    mock_db_engine.Session.return_value = mock_session # Not how it works with 'with Session(db_engine)'
    
    # Let's simplify and mock the _check methods directly for logic verification
    judge._check_cooldown = MagicMock(return_value=(True, "passed"))
    judge._check_deduplication = MagicMock(return_value=(True, "passed"))
    
    # 1. Standard mode - Approved
    approved, reason = judge.evaluate(opp, world)
    assert approved is True
    
    # 2. Recovery mode - Blocked
    world.current_flow_mode = "RECOVERY_MODE"
    approved, reason = judge.evaluate(opp, world)
    assert approved is False
    assert "RECOVERY_MODE" in reason
    
    # 3. Deep Work - Blocked P3
    world.current_flow_mode = "DEEP_WORK"
    approved, reason = judge.evaluate(opp, world)
    assert approved is False
    assert "DEEP_WORK" in reason

@pytest.mark.asyncio
async def test_full_cycle_execution(pcl_engine, mock_orchestrator, mock_hlsm):
    # Setup world model with an opportunity
    pcl_engine.build_world_model = AsyncMock(return_value=WorldModel(
        active_goals=[MagicMock(id=1, title="Stalled Goal", days_since_update=5.0, status="active", priority="HIGH", metric_current=0, metric_target=100)],
        current_flow_mode="STANDARD"
    ))
    
    # Mock persistence
    pcl_engine._persist_opportunity = MagicMock(return_value=MagicMock(id="test_opt"))
    pcl_engine._update_opportunity_outcome = MagicMock()
    pcl_engine._persist_world_snapshot = MagicMock()
    pcl_engine._prune_old_snapshots = MagicMock()
    
    # Mock judge to always pass for the cycle test
    pcl_engine.judge.evaluate = MagicMock(return_value=(True, "mocked_pass"))
    
    summary = await pcl_engine.run_cycle()
    
    assert summary["opportunities_detected"] > 0
    assert summary["opportunities_actioned"] > 0
    assert mock_orchestrator.execute_objective.called or mock_hlsm.l1_store.called
