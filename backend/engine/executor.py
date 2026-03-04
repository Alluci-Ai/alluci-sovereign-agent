import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, Any, Set, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from sqlmodel import Session, select

from ..models import DAGTask, TaskStatus, Run, TaskRecord
from ..adapters.registry import AdapterRegistry
from .errors import AdapterError, TaskTimeoutError, AdapterNotFoundError

logger = logging.getLogger("Engine.Executor")

class Executor:
    """
    Executes a DAG of tasks using real adapters and persists state to DB.
    """
    def __init__(self, adapter_registry: AdapterRegistry, session_factory, max_concurrent: int = 5):
        self.registry = adapter_registry
        self.session_factory = session_factory  # Function that yields a session
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.task_timeout = 60.0  # seconds

    async def execute_dag(self, run_id: int, tasks: Dict[str, DAGTask]) -> Dict[str, DAGTask]:
        """
        Main execution loop.
        """
        # Sync initial task records to DB
        self._init_task_records(run_id, tasks)

        completed_ids: Set[str] = {t_id for t_id, t in tasks.items() if t.status == TaskStatus.COMPLETED}
        failed_ids: Set[str] = set()
        
        while True:
            # 1. Identify executable tasks
            executable = []
            pending_count = 0
            
            for t_id, task in tasks.items():
                if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                    continue
                
                pending_count += 1
                
                deps_met = all(d in completed_ids for d in task.dependencies)
                deps_failed = any(d in failed_ids for d in task.dependencies)
                
                if deps_failed:
                    task.status = TaskStatus.FAILED
                    task.result = "Upstream dependency failed."
                    self._update_task_record(run_id, t_id, status="failed", error="Dependency failed")
                    failed_ids.add(t_id)
                elif deps_met and task.status == TaskStatus.PENDING:
                    executable.append(t_id)

            if not executable and pending_count > 0:
                # Deadlock or all remaining blocked
                break
                
            if pending_count == 0:
                break

            # 2. Execute batch
            futures = [self._run_task(run_id, tasks[t_id], tasks) for t_id in executable]
            results = await asyncio.gather(*futures, return_exceptions=True)
            
            for res in results:
                if isinstance(res, DAGTask):
                    if res.status == TaskStatus.COMPLETED:
                        completed_ids.add(res.id)
                    else:
                        failed_ids.add(res.id)
        
        return tasks

    async def _run_task(self, run_id: int, task: DAGTask, all_tasks: Dict[str, DAGTask]) -> DAGTask:
        async with self.semaphore:
            task.status = TaskStatus.RUNNING
            self._update_task_record(run_id, task.id, status="running", start_time=datetime.now(timezone.utc))
            
            # Context Injection
            dep_context = {
                dep: all_tasks[dep].result 
                for dep in task.dependencies 
                if all_tasks[dep].status == TaskStatus.COMPLETED
            }
            task.args["dependency_output"] = dep_context

            try:
                # Execute with Timeout
                result = await asyncio.wait_for(
                    self._execute_adapter(task.action, task.args),
                    timeout=self.task_timeout
                )
                
                task.result = str(result)
                task.status = TaskStatus.COMPLETED
                self._update_task_record(run_id, task.id, status="completed", result=str(result), end_time=datetime.now(timezone.utc))
                logger.info(f"Task {task.id} ({task.action}) ✅")
                
            except asyncio.TimeoutError:
                err_msg = f"Task exceeded {self.task_timeout}s limit."
                logger.error(f"Task {task.id} ⏳ {err_msg}")
                task.status = TaskStatus.FAILED
                task.result = err_msg
                self._update_task_record(run_id, task.id, status="failed", error=err_msg, end_time=datetime.now(timezone.utc))
                
            except Exception as e:
                logger.error(f"Task {task.id} ❌ : {e}", exc_info=True)
                safe_error = f"Task failed: {type(e).__name__}"
                task.result = safe_error
                task.status = TaskStatus.FAILED
                self._update_task_record(run_id, task.id, status="failed", error=safe_error, end_time=datetime.now(timezone.utc))
            
            return task

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True)
    async def _execute_adapter(self, action: str, args: Dict[str, Any]) -> Any:
        adapter = self.registry.get(action)
        if not adapter:
            # No mock fallbacks in production — fail explicitly
            raise AdapterNotFoundError(
                f"No adapter registered for action '{action}'. "
                f"Available adapters: {self.registry.list_tools()}"
            )
        
        return await adapter.execute(args)

    # --- Persistence Helpers ---

    def _init_task_records(self, run_id: int, tasks: Dict[str, DAGTask]):
        """Creates initial PENDING records in DB."""
        with Session(self.session_factory()) as session:
            for t_id, task in tasks.items():
                # Check if exists (idempotency)
                statement = select(TaskRecord).where(TaskRecord.run_id == run_id, TaskRecord.task_dag_id == t_id)
                existing = session.exec(statement).first()
                if not existing:
                    record = TaskRecord(
                        run_id=run_id,
                        task_dag_id=t_id,
                        action=task.action,
                        args=task.args,
                        status="pending"
                    )
                    session.add(record)
            session.commit()

    def _update_task_record(self, run_id: int, task_dag_id: str, **kwargs):
        """Updates a task record in the DB."""
        try:
            with Session(self.session_factory()) as session:
                statement = select(TaskRecord).where(TaskRecord.run_id == run_id, TaskRecord.task_dag_id == task_dag_id)
                record = session.exec(statement).first()
                if record:
                    for k, v in kwargs.items():
                        setattr(record, k, v)
                    session.add(record)
                    session.commit()
        except Exception as e:
            logger.error(f"Failed to persist task update: {e}")
