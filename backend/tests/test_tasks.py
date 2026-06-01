"""
Unit tests for the TaskManager (TASKS.md CRUD operations).
"""
import pytest
import os
import tempfile
from backend.tasks import TaskManager
from backend.models import TaskUpdate, TaskPriority


class TestTaskManager:
    """Tests for task CRUD and filtering operations."""

    def _make_manager(self, content: str = "") -> tuple:
        """Helper to create a TaskManager with a temp file."""
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
        f.write(content)
        f.close()
        return TaskManager(filepath=f.name), f.name

    @pytest.mark.asyncio
    async def test_parse_basic_task(self):
        content = "- [ ] Fix the bug\n"
        mgr, path = self._make_manager(content)
        
        tasks = await mgr.get_tasks()
        assert len(tasks) == 1
        assert tasks[0].completed is False
        assert "Fix the bug" in tasks[0].description
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_parse_completed_task(self):
        content = "- [x] Done task\n"
        mgr, path = self._make_manager(content)
        
        tasks = await mgr.get_tasks()
        assert len(tasks) == 1
        assert tasks[0].completed is True
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_parse_priority(self):
        content = "- [ ] [URGENT] Critical fix\n- [ ] [LOW] Nice to have\n"
        mgr, path = self._make_manager(content)
        
        tasks = await mgr.get_tasks()
        assert len(tasks) == 2
        # Should be sorted by priority (URGENT first)
        assert tasks[0].priority == TaskPriority.URGENT
        assert tasks[1].priority == TaskPriority.LOW
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_parse_due_date(self):
        content = "- [ ] Deadline task (due: 2024-06-15)\n"
        mgr, path = self._make_manager(content)
        
        tasks = await mgr.get_tasks()
        assert tasks[0].due_date == "2024-06-15"
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_add_task(self):
        mgr, path = self._make_manager("# Tasks\n")
        
        task = TaskUpdate(
            description="New task",
            completed=False,
            priority=TaskPriority.HIGH,
            due_date="2024-12-01"
        )
        result = await mgr.add_task(task)
        
        assert result is not None
        assert "New task" in result.description
        
        # Verify persisted
        tasks = await mgr.get_tasks()
        assert len(tasks) == 1
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_update_task(self):
        content = "- [ ] Original task\n"
        mgr, path = self._make_manager(content)
        
        update = TaskUpdate(
            description="Updated task",
            completed=True,
            priority=TaskPriority.HIGH
        )
        result = await mgr.update_task(0, update)
        
        assert result is not None
        assert result.completed is True
        assert "Updated" in result.description
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_delete_task(self):
        content = "- [ ] Task to delete\n- [ ] Keep this\n"
        mgr, path = self._make_manager(content)
        
        assert await mgr.delete_task(0) is True
        
        tasks = await mgr.get_tasks()
        assert len(tasks) == 1
        assert "Keep" in tasks[0].description
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_filter_by_status_active(self):
        content = "- [ ] Active task\n- [x] Done task\n"
        mgr, path = self._make_manager(content)
        
        active = await mgr.get_tasks(status="active")
        assert len(active) == 1
        assert active[0].completed is False
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_filter_by_status_completed(self):
        content = "- [ ] Active task\n- [x] Done task\n"
        mgr, path = self._make_manager(content)
        
        completed = await mgr.get_tasks(status="completed")
        assert len(completed) == 1
        assert completed[0].completed is True
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_filter_by_priority(self):
        content = "- [ ] [HIGH] Important\n- [ ] [LOW] Not important\n"
        mgr, path = self._make_manager(content)
        
        high = await mgr.get_tasks(priority="HIGH")
        assert len(high) == 1
        assert high[0].priority == TaskPriority.HIGH
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_empty_file(self):
        mgr, path = self._make_manager("")
        tasks = await mgr.get_tasks()
        assert tasks == []
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_nonexistent_file(self):
        mgr = TaskManager(filepath="/tmp/nonexistent_tasks_12345.md")
        tasks = await mgr.get_tasks()
        assert tasks == []

    @pytest.mark.asyncio
    async def test_delete_out_of_bounds(self):
        content = "- [ ] Only task\n"
        mgr, path = self._make_manager(content)
        
        assert await mgr.delete_task(99) is False
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_update_out_of_bounds(self):
        content = "- [ ] Only task\n"
        mgr, path = self._make_manager(content)
        
        result = await mgr.update_task(99, TaskUpdate(description="X", completed=False))
        assert result is None
        
        os.unlink(path)

    @pytest.mark.asyncio
    async def test_multi_agent_isolation(self):
        prefix = os.path.join(tempfile.gettempdir(), "test_tasks_multi")
        mgr = TaskManager(filepath_prefix=prefix)
        
        # Clean up existing files if any
        if os.path.exists(f"{prefix}_agent_alpha.md"): os.unlink(f"{prefix}_agent_alpha.md")
        if os.path.exists(f"{prefix}_agent_beta.md"): os.unlink(f"{prefix}_agent_beta.md")
        
        await mgr.add_task(TaskUpdate(
            description="Alpha task",
            completed=False,
            priority=TaskPriority.HIGH
        ), agent_id="agent_alpha")
        
        await mgr.add_task(TaskUpdate(
            description="Beta task",
            completed=False,
            priority=TaskPriority.LOW
        ), agent_id="agent_beta")
        
        alpha_tasks = await mgr.get_tasks(agent_id="agent_alpha")
        beta_tasks = await mgr.get_tasks(agent_id="agent_beta")
        
        assert len(alpha_tasks) == 1
        assert "Alpha" in alpha_tasks[0].description
        assert len(beta_tasks) == 1
        assert "Beta" in beta_tasks[0].description
        
        assert os.path.exists(f"{prefix}_agent_alpha.md")
        assert os.path.exists(f"{prefix}_agent_beta.md")
        
        os.unlink(f"{prefix}_agent_alpha.md")
        os.unlink(f"{prefix}_agent_beta.md")

