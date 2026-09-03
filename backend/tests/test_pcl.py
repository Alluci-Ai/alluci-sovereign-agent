import pytest
pytestmark = pytest.mark.unit

import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
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
    judge._check_cooldown = MagicMock(return_value=(True, "passed"))  # type: ignore
    judge._check_quiet_hours = MagicMock(return_value=(True, "passed"))  # type: ignore
    judge._check_deduplication = MagicMock(return_value=(True, "passed"))  # type: ignore
    
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


# ─── _observe_memory fix verification ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_observe_memory_uses_dataclass_attributes(pcl_engine, mock_hlsm):
    """
    Regression test for the two bugs fixed in F-01:
      1. world.recent_learnings was built with m.get('content') on HLSMRetrievalResult
         dataclasses → AttributeError.
      2. The recurring-topic loop iterated over 'recent' (undefined) → NameError.
    Both were silently swallowed by except Exception; this test forces them
    to surface if the bugs regress.
    """
    from backend.memory.hlsm_manager import HLSMRetrievalResult

    # Build mock return values as proper HLSMRetrievalResult dataclasses
    entries = [
        HLSMRetrievalResult(
            id=f"mem_{i:02d}",
            content=f"Memory entry {i}: sovereign agent processed goal number {i}",
            tier=1,
            source="task_result" if i % 2 == 0 else "heartbeat_signal",
            relevance_score=0.9 - i * 0.05,
            retention_score=0.8,
        )
        for i in range(5)
    ]
    mock_hlsm.l1_get_recent = AsyncMock(return_value=entries)
    mock_hlsm.l2_search = AsyncMock(return_value=[])

    world = WorldModel()
    # This call should not raise AttributeError or NameError
    await pcl_engine._observe_memory(world)

    # Verify recent_learnings populated correctly with attribute access
    assert len(world.recent_learnings) == 5
    # Each entry should include the content and source (dot-accessed, not .get())
    for i, entry in enumerate(entries):
        assert entry.content in world.recent_learnings[i]
        assert entry.source in world.recent_learnings[i]


@pytest.mark.asyncio
async def test_observe_memory_heartbeat_signals_surface_to_learnings(pcl_engine, mock_hlsm):
    """
    Verify that [PCL_SIGNAL] entries stored by heartbeat pcl_signal actions
    appear in world.recent_learnings where HeartbeatSignalDetector can find them.
    """
    from backend.memory.hlsm_manager import HLSMRetrievalResult

    pcl_signal_entry = HLSMRetrievalResult(
        id="sig_001",
        content="[PCL_SIGNAL] Check URL: content changed (priority=2, order_id=url_watch_01)",
        tier=1,
        source="heartbeat_signal",
        relevance_score=0.95,
        retention_score=0.90,
    )
    mock_hlsm.l1_get_recent = AsyncMock(return_value=[pcl_signal_entry])
    mock_hlsm.l2_search = AsyncMock(return_value=[])

    world = WorldModel()
    await pcl_engine._observe_memory(world)

    # The [PCL_SIGNAL] marker must appear in recent_learnings
    assert any("[PCL_SIGNAL]" in entry for entry in world.recent_learnings), (
        "PCL_SIGNAL entry not found in world.recent_learnings — "
        "HeartbeatSignalDetector will be starved of data"
    )


@pytest.mark.asyncio
async def test_observe_memory_recurring_topics_detected(pcl_engine, mock_hlsm):
    """
    Verify recurring topic detection via L2 semantic search works correctly
    after the 'recent' variable NameError was fixed.
    """
    from backend.memory.hlsm_manager import HLSMRetrievalResult

    # Long content entries that will be checked for L2 similarity
    entries = [
        HLSMRetrievalResult(
            id=f"long_{i}",
            content=f"The project deployment pipeline needs attention: CI failing on integration tests since Monday, blocking all releases. Step {i}",
            tier=1, source="task_result",
            relevance_score=0.85, retention_score=0.80,
        )
        for i in range(3)
    ]

    # L2 returns 3 high-similarity matches → should trigger recurring detection
    high_sim_matches = [
        HLSMRetrievalResult(
            id=f"l2_match_{j}",
            content=entries[0].content,
            tier=2, source="task_result",
            relevance_score=0.92,
            retention_score=0.80,
        )
        for j in range(3)
    ]
    mock_hlsm.l1_get_recent = AsyncMock(return_value=entries)
    mock_hlsm.l2_search = AsyncMock(return_value=high_sim_matches)

    world = WorldModel()
    await pcl_engine._observe_memory(world)

    # Recurring topics should now be populated
    assert len(world.recurring_topics) >= 1
    assert any("deployment" in t.lower() or "project" in t.lower()
               for t in world.recurring_topics)


# ─── HeartbeatSignalDetector ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_heartbeat_signal_detector_fires_on_pcl_signal_entry():
    from backend.pcl import HeartbeatSignalDetector
    from backend.pcl import WorldModel

    detector = HeartbeatSignalDetector()
    world = WorldModel()
    world.recent_learnings = [
        "[PCL_SIGNAL] Check URL: Content changed at https://status.example.com (priority=2, order_id=url_watch_01) [source:heartbeat_signal]"
    ]

    opp = await detector.detect(world)
    assert opp is not None
    assert opp.detector_name == "HeartbeatSignalDetector"
    assert opp.priority == 2
    assert opp.recommended_action == "execute"  # P2 → execute
    assert "Check URL" in opp.title or "Heartbeat signal" in opp.title


@pytest.mark.asyncio
async def test_heartbeat_signal_detector_p3_routes_to_notify():
    from backend.pcl import HeartbeatSignalDetector, WorldModel

    detector = HeartbeatSignalDetector()
    world = WorldModel()
    world.recent_learnings = [
        "[PCL_SIGNAL] Monitor tasks: 2 items overdue (priority=3, order_id=task_watch_01) [source:heartbeat_signal]"
    ]

    opp = await detector.detect(world)
    assert opp is not None
    assert opp.priority == 3
    assert opp.recommended_action == "notify"  # P3 → notify, not execute


@pytest.mark.asyncio
async def test_heartbeat_signal_detector_silent_without_signals():
    from backend.pcl import HeartbeatSignalDetector, WorldModel

    detector = HeartbeatSignalDetector()
    world = WorldModel()
    world.recent_learnings = [
        "Regular memory entry: completed task A [source:task_result]",
        "Another normal memory [source:orchestrator]",
    ]

    opp = await detector.detect(world)
    assert opp is None


@pytest.mark.asyncio
async def test_heartbeat_signal_detector_in_registered_detectors(pcl_engine):
    """HeartbeatSignalDetector must be registered in the PCL detector list."""
    from backend.pcl import HeartbeatSignalDetector
    names = [d.name for d in pcl_engine.detectors]
    assert "HeartbeatSignalDetector" in names, (
        f"HeartbeatSignalDetector not registered. Detectors: {names}"
    )
    assert len(names) == 9, (
        f"Expected 9 detectors, got {len(names)}: {names}"
    )

@pytest.mark.asyncio
async def test_base_detector_warning():
    from backend.pcl import BaseDetector, WorldModel
    class MyDetector(BaseDetector):
        pass
        
    detector = MyDetector()
    world = WorldModel()
    
    # Should not crash and should return None
    res = await detector.detect(world)
    assert res is None
    # Verify the warned flag was set
    assert MyDetector._warned is True

@pytest.mark.asyncio
async def test_recurring_topic_detector_conditions():
    from backend.pcl import RecurringTopicDetector, WorldModel
    detector = RecurringTopicDetector()
    
    # Empty world
    world = WorldModel()
    assert await detector.detect(world) is None
    
    # Short learning
    world.recent_learnings = ["short"]
    assert await detector.detect(world) is None

@pytest.mark.asyncio
async def test_task_failure_pattern_detector():
    from backend.pcl import TaskFailurePatternDetector, WorldModel
    detector = TaskFailurePatternDetector()
    world = WorldModel()
    
    # Not enough failures
    world.recent_failures = ["task_a", "task_a"]
    assert await detector.detect(world) is None
    
    # Enough failures
    world.recent_failures = ["task_a", "task_a", "task_a", "task_b"]
    opp = await detector.detect(world)
    assert opp is not None
    assert opp.priority == 2
    assert "Repeated failures: task_a (3×)" in opp.title

@pytest.mark.asyncio
async def test_memory_gap_detector():
    from backend.pcl import MemoryGapDetector, WorldModel
    detector = MemoryGapDetector()
    world = WorldModel()
    
    goal_active = MagicMock(id=1, title="G1", status="active", l1_memory_count=0, days_since_update=8.0)
    goal_inactive = MagicMock(id=2, title="G2", status="completed", l1_memory_count=0, days_since_update=8.0)
    goal_recent = MagicMock(id=3, title="G3", status="active", l1_memory_count=5, days_since_update=8.0)
    
    world.active_goals = [goal_active, goal_inactive, goal_recent]
    opp = await detector.detect(world)
    
    assert opp is not None
    assert "Forgotten goal" in opp.title
    assert opp.affects_goal_id == 1

@pytest.mark.asyncio
async def test_peak_opportunity_detector():
    from backend.pcl import PeakOpportunityDetector, WorldModel
    detector = PeakOpportunityDetector()
    world = WorldModel()
    
    # Not peak performance
    world.current_flow_mode = "STANDARD"
    assert await detector.detect(world) is None
    
    # Peak performance but no high priority goals
    world.current_flow_mode = "PEAK_PERFORMANCE"
    goal_low = MagicMock(id=1, title="L", status="active", priority="LOW", metric_current=10, metric_target=100)
    world.active_goals = [goal_low]
    assert await detector.detect(world) is None
    
    # High priority pending goal
    goal_high = MagicMock(id=2, title="H", status="active", priority="URGENT", metric_current=10, metric_target=100)
    world.active_goals = [goal_high]
    opp = await detector.detect(world)
    
    assert opp is not None
    assert opp.recommended_action == "execute"
    assert "Peak performance" in opp.title


@pytest.mark.asyncio
async def test_judge_intervention_additional():
    from backend.pcl import InterventionJudge, WorldModel, Opportunity
    
    class MockDb:
        def __init__(self, should_find=False):
            self.should_find = should_find
        def exec(self, query):
            mock_res = MagicMock()
            if self.should_find:
                mock_opp = MagicMock(actioned_at=time.time() - 100, detected_at=time.time() - 100)
                mock_res.first.return_value = mock_opp
            else:
                mock_res.first.return_value = None
            return mock_res
    
    class MockSession:
        def __init__(self, db):
            self.db = db
        def __enter__(self):
            return self.db
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    mock_db = MagicMock()
    # In PCL, `with Session(self.db_engine) as session:` is used. 
    # To mock this without importing sqlmodel, we can mock `backend.pcl.Session`.
    
    with patch("backend.pcl.Session") as mock_session_cls:
        mock_session_cls.return_value = MockSession(MockDb(should_find=True))
        judge = InterventionJudge(mock_db, settings_obj=MagicMock(PCL_QUIET_START_HOUR=22, PCL_QUIET_END_HOUR=7))
        world = WorldModel(current_flow_mode="STANDARD")
        opp = Opportunity(id="test_id", detector_name="T", title="T", description="T", priority=3, confidence=0.9, recommended_action="notify", cooldown_minutes=60)
        
        # Test cooldown failure
        res, reason = judge._check_cooldown(opp)
        assert res is False
        assert "Cooldown" in reason
        
        # Test deduplication failure
        res, reason = judge._check_deduplication(opp)
        assert res is False
        assert "Deduplicated" in reason

    with patch("backend.pcl.Session") as mock_session_cls:
        mock_session_cls.return_value = MockSession(MockDb(should_find=False))
        judge = InterventionJudge(mock_db, settings_obj=MagicMock(PCL_QUIET_START_HOUR=22, PCL_QUIET_END_HOUR=7))
        
        # Test cooldown pass
        res, reason = judge._check_cooldown(opp)
        assert res is True
        
        # Test dedup pass
        res, reason = judge._check_deduplication(opp)
        assert res is True
        
        # Test low confidence execute
        opp_exec = Opportunity(id="test_id", detector_name="T", title="T", description="T", priority=3, confidence=0.7, recommended_action="execute")
        res, reason = judge._check_confidence(opp_exec)
        assert res is False
        
        # Test low confidence notify
        opp_notify = Opportunity(id="test_id", detector_name="T", title="T", description="T", priority=3, confidence=0.5, recommended_action="notify")
        res, reason = judge._check_confidence(opp_notify)
        assert res is False

    # Test quiet hours logic without mocking datetime
    from datetime import datetime, timezone
    now_hour = datetime.now(timezone.utc).hour
    
    # Inside quiet hours
    quiet_start = (now_hour - 1) % 24
    quiet_end = (now_hour + 2) % 24
    judge_in_quiet = InterventionJudge(mock_db, settings_obj=MagicMock(PCL_QUIET_START_HOUR=quiet_start, PCL_QUIET_END_HOUR=quiet_end))
    
    opp_normal = Opportunity(id="test_id", detector_name="T", title="T", description="T", priority=3, confidence=0.9, recommended_action="notify")
    res, reason = judge_in_quiet._check_quiet_hours(opp_normal)
    assert res is False
    
    # Critical execute bypasses quiet hours
    opp_critical = Opportunity(id="test_id", detector_name="T", title="T", description="T", priority=1, confidence=0.9, recommended_action="execute")
    res, reason = judge_in_quiet._check_quiet_hours(opp_critical)
    assert res is True

    # Outside quiet hours
    quiet_start = (now_hour + 2) % 24
    quiet_end = (now_hour + 5) % 24
    judge_out_quiet = InterventionJudge(mock_db, settings_obj=MagicMock(PCL_QUIET_START_HOUR=quiet_start, PCL_QUIET_END_HOUR=quiet_end))
    res, reason = judge_out_quiet._check_quiet_hours(opp_normal)
    assert res is True

