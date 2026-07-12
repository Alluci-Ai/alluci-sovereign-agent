import pytest
pytestmark = pytest.mark.unit

"""
Planner Unit Tests

Tests DAG construction, all three validation layers (self-dependency,
phantom dependency, cycle detection), and plan generation error handling.

INVARIANTS:
  - Self-dependency always raises ValueError
  - Phantom dependency always raises ValueError
  - Any cycle in the dependency graph always raises ValueError
  - Valid DAGs with complex topologies are built correctly
  - Empty plan from LLM raises ValueError
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock
from backend.engine.planner import Planner
from backend.models import DAGTask, TaskStatus


class TestDAGConstruction:

    @pytest.mark.unit
    def test_linear_chain(self, mock_router):
        """A → B → C builds correctly with correct dependency lists."""
        planner = Planner(mock_router)
        steps = [
            {"id": "A", "tool": "search", "description": "Search",    "dependencies": []},
            {"id": "B", "tool": "analyze","description": "Analyze",   "dependencies": ["A"]},
            {"id": "C", "tool": "report", "description": "Report",    "dependencies": ["B"]},
        ]
        tasks = planner._build_and_validate_dag(steps, "test")
        assert len(tasks) == 3
        assert tasks["A"].dependencies == []
        assert tasks["B"].dependencies == ["A"]
        assert tasks["C"].dependencies == ["B"]

    @pytest.mark.unit
    def test_diamond_topology(self, mock_router):
        """
        Diamond: A → B, A → C, B → D, C → D
        Both B and C depend on A; D depends on both B and C.
        """
        planner = Planner(mock_router)
        steps = [
            {"id": "A", "tool": "t", "description": "", "dependencies": []},
            {"id": "B", "tool": "t", "description": "", "dependencies": ["A"]},
            {"id": "C", "tool": "t", "description": "", "dependencies": ["A"]},
            {"id": "D", "tool": "t", "description": "", "dependencies": ["B", "C"]},
        ]
        tasks = planner._build_and_validate_dag(steps, "diamond")
        assert len(tasks) == 4
        assert set(tasks["D"].dependencies) == {"B", "C"}

    @pytest.mark.unit
    def test_parallel_roots(self, mock_router):
        """Multiple tasks with no dependencies run in parallel."""
        planner = Planner(mock_router)
        steps = [
            {"id": "root_1", "tool": "t", "description": "", "dependencies": []},
            {"id": "root_2", "tool": "t", "description": "", "dependencies": []},
            {"id": "root_3", "tool": "t", "description": "", "dependencies": []},
        ]
        tasks = planner._build_and_validate_dag(steps, "parallel")
        assert all(len(t.dependencies) == 0 for t in tasks.values())

    @pytest.mark.unit
    def test_single_node_dag(self, mock_router):
        """Single-task plan builds successfully."""
        planner = Planner(mock_router)
        steps = [{"id": "solo", "tool": "t", "description": "only task", "dependencies": []}]
        tasks = planner._build_and_validate_dag(steps, "solo")
        assert len(tasks) == 1
        assert "solo" in tasks

    @pytest.mark.unit
    def test_assignee_parsing(self, mock_router):
        """Task with assignee uses correct assignee, default to executive."""
        planner = Planner(mock_router)
        steps = [
            {"id": "A", "tool": "t", "description": "", "dependencies": [], "assignee": "rocco"},
            {"id": "B", "tool": "t", "description": "", "dependencies": ["A"]}
        ]
        tasks = planner._build_and_validate_dag(steps, "test")
        assert tasks["A"].assignee == "rocco"
        assert tasks["B"].assignee == "executive"


class TestDAGValidation:

    @pytest.mark.unit
    def test_self_dependency_raises(self, mock_router):
        """A task that lists itself as a dependency must raise ValueError."""
        planner = Planner(mock_router)
        steps = [{"id": "A", "tool": "t", "description": "", "dependencies": ["A"]}]
        with pytest.raises(ValueError, match="[Ss]elf.depend"):
            planner._build_and_validate_dag(steps, "test")

    @pytest.mark.unit
    def test_phantom_dependency_raises(self, mock_router):
        """A dependency referencing a non-existent task ID must raise ValueError."""
        planner = Planner(mock_router)
        steps = [{"id": "A", "tool": "t", "description": "", "dependencies": ["ghost_task"]}]
        with pytest.raises(ValueError):
            planner._build_and_validate_dag(steps, "test")

    @pytest.mark.unit
    def test_direct_cycle_raises(self, mock_router):
        """A → B, B → A is a direct cycle — must raise ValueError."""
        planner = Planner(mock_router)
        steps = [
            {"id": "A", "tool": "t", "description": "", "dependencies": ["B"]},
            {"id": "B", "tool": "t", "description": "", "dependencies": ["A"]},
        ]
        with pytest.raises(ValueError, match="[Cc]ycle"):
            planner._build_and_validate_dag(steps, "cycle test")

    @pytest.mark.unit
    def test_indirect_cycle_raises(self, mock_router):
        """A → B → C → A is a 3-node cycle — must raise ValueError."""
        planner = Planner(mock_router)
        steps = [
            {"id": "A", "tool": "t", "description": "", "dependencies": ["C"]},
            {"id": "B", "tool": "t", "description": "", "dependencies": ["A"]},
            {"id": "C", "tool": "t", "description": "", "dependencies": ["B"]},
        ]
        with pytest.raises(ValueError, match="[Cc]ycle"):
            planner._build_and_validate_dag(steps, "indirect cycle")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_empty_plan_raises(self, mock_router):
        """LLM returning zero steps must raise ValueError."""
        planner = Planner(mock_router)
        mock_router.get_structured_plan = AsyncMock(return_value={"steps": []})
        with pytest.raises(ValueError):
            await planner.generate_plan("empty objective", context={})  # type: ignore


class TestExecutorParallelism:
    """Executor correctly identifies and runs ready tasks in parallel."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_independent_tasks_run_in_parallel(self, mock_adapter_registry, temp_db):
        """
        Tasks with no dependencies should be submitted to asyncio.gather()
        in the same wave, not sequentially.
        """
        from backend.engine.executor import Executor
        from backend.models import DAGTask, TaskStatus

        execution_order = []

        # adapter.execute(args) takes one argument
        async def mock_execute(args, **kwargs):
            # args can be anything, we just sleep
            await asyncio.sleep(0.1)
            return "ok"

        mock_adapter_registry.get = lambda name: MagicMock(
            execute=AsyncMock(side_effect=mock_execute)
        )

        executor = Executor(mock_adapter_registry, session_factory=lambda: temp_db, max_concurrent=5)
        # Mock out DB commits to avoid SQLite skewing parallel timing
        executor._update_task_record = MagicMock()  # type: ignore
        executor._init_task_records = MagicMock()  # type: ignore

        tasks = {
            "t1": DAGTask(id="t1", action="tool_a", args={}, dependencies=[]),
            "t2": DAGTask(id="t2", action="tool_b", args={}, dependencies=[]),
            "t3": DAGTask(id="t3", action="tool_c", args={}, dependencies=[]),
        }

        # All three should execute; check that all complete
        import time
        start = time.monotonic()
        results = await executor.execute_dag(run_id=1, tasks=tasks)
        elapsed = time.monotonic() - start

        # If truly parallel, 3 × 0.1s tasks complete in ~0.1s + DB overhead, not 0.3s
        assert elapsed < 0.25, f"Tasks appear to be running sequentially: {elapsed:.3f}s"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_failed_task_cascades_to_downstream(self, mock_adapter_registry, temp_db):
        """
        If task A fails, all tasks that depend on A must be marked FAILED.
        Tasks on independent branches must still complete.
        """
        from backend.engine.executor import Executor
        from backend.models import DAGTask, TaskStatus

        call_log = []

        def make_mock_execute(name):
            async def _mock(args, **kwargs):
                call_log.append(name)
                if name == "failing_tool":
                    raise RuntimeError("Simulated tool failure")
                return f"ok_{name}"
            return _mock

        mock_adapter_registry.get = lambda name: MagicMock(
            execute=AsyncMock(side_effect=make_mock_execute(name))
        )

        executor = Executor(mock_adapter_registry, session_factory=lambda: temp_db, max_concurrent=5)

        tasks = {
            "root":       DAGTask(id="root",       action="failing_tool",  args={}, dependencies=[]),
            "dependent":  DAGTask(id="dependent",  action="dependent_tool", args={}, dependencies=["root"]),
            "independent":DAGTask(id="independent",action="good_tool",      args={}, dependencies=[]),
        }

        results = await executor.execute_dag(run_id=1, tasks=tasks)

        assert tasks["root"].status == TaskStatus.FAILED
        assert tasks["dependent"].status == TaskStatus.FAILED
        # Independent task should have run and succeeded
        assert tasks["independent"].status == TaskStatus.COMPLETED
        assert "good_tool" in call_log
        assert "dependent_tool" not in call_log
