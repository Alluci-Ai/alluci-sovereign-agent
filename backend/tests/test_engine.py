import pytest
pytestmark = pytest.mark.unit

"""
Unit tests for the Execution Engine: Planner, Executor, and Critic.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock
from backend.models import DAGTask, TaskStatus


# ═══════════════════════════════════════════════════════════════════
# Planner Tests
# ═══════════════════════════════════════════════════════════════════

class TestPlanner:
    """Tests for the DAG planner and validation logic."""

    def test_build_valid_dag(self, mock_router):
        from backend.engine.planner import Planner
        planner = Planner(mock_router)

        steps = [
            {"id": "step_1", "tool": "web_search", "description": "Search", "dependencies": []},
            {"id": "step_2", "tool": "summarize", "description": "Summarize", "dependencies": ["step_1"]},
        ]
        tasks = planner._build_and_validate_dag(steps, "Test objective")

        assert len(tasks) == 2
        assert "step_1" in tasks
        assert "step_2" in tasks
        assert tasks["step_1"].dependencies == []
        assert tasks["step_2"].dependencies == ["step_1"]

    def test_self_dependency_raises(self, mock_router):
        from backend.engine.planner import Planner
        planner = Planner(mock_router)

        steps = [
            {"id": "step_1", "tool": "search", "description": "A", "dependencies": ["step_1"]},
        ]
        with pytest.raises(ValueError, match="Self-dependency"):
            planner._build_and_validate_dag(steps, "Test")

    def test_phantom_dependency_raises(self, mock_router):
        from backend.engine.planner import Planner
        planner = Planner(mock_router)

        steps = [
            {"id": "step_1", "tool": "search", "description": "A", "dependencies": ["nonexistent"]},
        ]
        with pytest.raises(ValueError, match="non-existent"):
            planner._build_and_validate_dag(steps, "Test")

    def test_cycle_detection_raises(self, mock_router):
        from backend.engine.planner import Planner
        planner = Planner(mock_router)

        # Simple cycle: A -> B, B -> A
        steps_simple = [
            {"id": "step_1", "tool": "a", "description": "A", "dependencies": ["step_2"]},
            {"id": "step_2", "tool": "b", "description": "B", "dependencies": ["step_1"]},
        ]
        with pytest.raises(ValueError, match="Cycle detected"):
            planner._build_and_validate_dag(steps_simple, "Test")

        # More complex cycle: A -> B -> C -> A
        steps_complex = [
            {"id": "A", "tool": "x", "dependencies": ["B"]},
            {"id": "B", "tool": "x", "dependencies": ["C"]},
            {"id": "C", "tool": "x", "dependencies": ["A"]}
        ]
        with pytest.raises(ValueError, match="Cycle detected"):
            planner._build_and_validate_dag(steps_complex, "Test Complex")

    def test_empty_steps_raises(self, mock_router):
        from backend.engine.planner import Planner
        planner = Planner(mock_router)

        mock_router.get_structured_plan = AsyncMock(return_value={"steps": []})

        with pytest.raises(ValueError, match="no steps"):
            asyncio.get_event_loop().run_until_complete(
                planner.generate_plan("Empty objective")
            )

    @pytest.mark.asyncio
    async def test_generate_plan_success(self, mock_router):
        from backend.engine.planner import Planner
        planner = Planner(mock_router)

        tasks = await planner.generate_plan("Test objective", "context")
        assert len(tasks) == 2
        assert all(t.status == TaskStatus.PENDING for t in tasks.values())


# ═══════════════════════════════════════════════════════════════════
# Executor Tests
# ═══════════════════════════════════════════════════════════════════

class TestExecutor:
    """Tests for the DAG executor."""

    @pytest.mark.asyncio
    async def test_execute_single_task(self, mock_adapter_registry, temp_db):
        from backend.engine.executor import Executor
        from sqlmodel import Session

        executor = Executor(mock_adapter_registry, lambda: temp_db, max_concurrent=2)

        tasks = {
            "step_1": DAGTask(
                id="step_1", action="system_query",
                args={"description": "test"}, dependencies=[]
            )
        }

        # Create a Run record first
        from backend.models import Run
        with Session(temp_db) as session:
            run = Run(objective="Test", autonomy_level="SEMI_AUTONOMOUS")
            session.add(run)
            session.commit()
            run_id = run.id

        result = await executor.execute_dag(run_id, tasks)  # type: ignore
        assert result["step_1"].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_dependency_resolution(self, mock_adapter_registry, temp_db):
        from backend.engine.executor import Executor
        from backend.models import Run
        from sqlmodel import Session
        
        executor = Executor(mock_adapter_registry, lambda: temp_db, max_concurrent=2)
        
        tasks = {
            "step_1": DAGTask(id="step_1", action="search", args={}, dependencies=[]),
            "step_2": DAGTask(id="step_2", action="summarize", args={}, dependencies=["step_1"]),
        }
        
        with Session(temp_db) as session:
            run = Run(objective="Test dep")
            session.add(run)
            session.commit()
            run_id = run.id
        
        result = await executor.execute_dag(run_id, tasks)  # type: ignore
        assert result["step_1"].status == TaskStatus.COMPLETED
        assert result["step_2"].status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_executor_propagates_agent_id(self, mock_adapter_registry, temp_db):
        from backend.engine.executor import Executor
        from backend.models import Run, TaskRecord
        from sqlmodel import Session, select

        executor = Executor(mock_adapter_registry, lambda: temp_db, max_concurrent=2)

        tasks = {
            "step_1": DAGTask(id="step_1", action="system_query", args={}, dependencies=[])
        }

        with Session(temp_db) as session:
            run = Run(objective="Test agent propagation", agent_id="sub_agent_xyz")
            session.add(run)
            session.commit()
            run_id = run.id

        await executor.execute_dag(run_id, tasks)  # type: ignore
        
        with Session(temp_db) as session:
            task_record = session.exec(select(TaskRecord).where(TaskRecord.run_id == run_id)).first()
            assert task_record is not None
            assert task_record.agent_id == "sub_agent_xyz"


    @pytest.mark.asyncio
    async def test_adapter_not_found_fails(self, temp_db):
        from backend.engine.executor import Executor
        from backend.adapters.registry import AdapterRegistry
        from backend.models import Run
        from sqlmodel import Session

        registry = AdapterRegistry()
        executor = Executor(registry, lambda: temp_db, max_concurrent=2)

        tasks = {
            "step_1": DAGTask(id="step_1", action="nonexistent_tool", args={}, dependencies=[]),
        }

        with Session(temp_db) as session:
            run = Run(objective="Test fail")
            session.add(run)
            session.commit()
            run_id = run.id

        result = await executor.execute_dag(run_id, tasks)  # type: ignore
        assert result["step_1"].status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_upstream_failure_cascades(self, temp_db):
        from backend.engine.executor import Executor
        from backend.models import Run
        from sqlmodel import Session

        # Registry that fails for step_1
        registry = MagicMock()
        registry.get = MagicMock(return_value=None)
        registry.list_tools = MagicMock(return_value=[])

        executor = Executor(registry, lambda: temp_db, max_concurrent=2)

        tasks = {
            "step_1": DAGTask(id="step_1", action="fail_me", args={}, dependencies=[]),
            "step_2": DAGTask(id="step_2", action="noop", args={}, dependencies=["step_1"]),
        }

        with Session(temp_db) as session:
            run = Run(objective="Cascade test")
            session.add(run)
            session.commit()
            run_id = run.id

        result = await executor.execute_dag(run_id, tasks)  # type: ignore
        assert result["step_1"].status == TaskStatus.FAILED
        assert result["step_2"].status == TaskStatus.FAILED
        assert result["step_2"].result is not None
        assert "dependency" in result["step_2"].result.lower()


# ═══════════════════════════════════════════════════════════════════
# Critic Tests
# ═══════════════════════════════════════════════════════════════════

class TestCritic:
    """Tests for the execution critic."""

    @pytest.mark.asyncio
    async def test_passing_score(self, mock_router):
        from backend.engine.critic import Critic
        critic = Critic(mock_router, threshold=0.75)

        mock_router.critique_result = AsyncMock(return_value={"score": 0.9, "feedback": "Great"})
        passed, score, feedback = await critic.evaluate("obj", "result")

        assert passed is True
        assert score == 0.9

    @pytest.mark.asyncio
    async def test_failing_score(self, mock_router):
        from backend.engine.critic import Critic
        critic = Critic(mock_router, threshold=0.75)

        mock_router.critique_result = AsyncMock(return_value={"score": 0.3, "feedback": "Poor"})
        passed, score, feedback = await critic.evaluate("obj", "result")

        assert passed is False
        assert score == 0.3

    @pytest.mark.asyncio
    async def test_critic_error_returns_failure(self, mock_router):
        from backend.engine.critic import Critic
        critic = Critic(mock_router, threshold=0.75)

        mock_router.critique_result = AsyncMock(side_effect=Exception("API down"))
        passed, score, feedback = await critic.evaluate("obj", "result")

        assert passed is False
        assert score == 0.0
