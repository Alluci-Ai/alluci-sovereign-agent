import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Set
from tenacity import stop_after_attempt, wait_exponential
from sqlmodel import Session, select

from ..models import DAGTask, TaskStatus, TaskRecord
from ..adapters.registry import AdapterRegistry
from .errors import AdapterNotFoundError
from ..logging_config import get_logger
from opentelemetry import trace
from .supervisor import SupervisorAgent
from ..ace.watch_auth import BioTelemetryAuth
from ..config import Settings

logger = get_logger("Engine.Executor")

class Executor:
    """
    Executes a DAG of tasks using real adapters and persists state to DB.
    """
    def __init__(self, adapter_registry: AdapterRegistry, session_factory, 
                 max_concurrent: int = 5, task_timeout: float = 60.0,
                 approval_manager=None, ace=None, on_task_complete=None):
        self.registry = adapter_registry
        self.session_factory = session_factory
        self._max_concurrent = max_concurrent
        self._semaphore = None
        self.task_timeout = task_timeout
        self.approval_manager = approval_manager
        self.on_task_complete = on_task_complete
        
        # [ PPN-015 ] SupervisorAgent for Context Optimization
        self.supervisor = SupervisorAgent()
        
        # [ PPN-017 ] Sovereign Kill Switch Daemon
        settings = Settings()
        self.watch_auth = BioTelemetryAuth(require_telemetry=settings.REQUIRE_WATCH_TELEMETRY)
        self.ace = ace

    @property
    def semaphore(self):
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self._max_concurrent)
        return self._semaphore

    async def execute_dag(self, run_id: int, tasks: Dict[str, DAGTask]) -> Dict[str, DAGTask]:
        """
        Main execution loop.
        """
        from ..tracing_config import get_tracer
        tracer = get_tracer("Engine.Executor")
        
        with tracer.start_as_current_span("execute_dag") as span:
            span.set_attribute("run_id", run_id)
            span.set_attribute("task_count", len(tasks))
            
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
        from ..tracing_config import get_tracer
        tracer = get_tracer("Engine.Executor")
        
        async with self.semaphore:
            with tracer.start_as_current_span("run_task") as span:
                span.set_attribute("run_id", run_id)
                span.set_attribute("task_id", task.id)
                span.set_attribute("action", task.action)
                
                task.status = TaskStatus.RUNNING
                self._update_task_record(run_id, task.id, status="running")
                
                # Context Injection
                raw_dep_context = {
                    dep: all_tasks[dep].result 
                    for dep in task.dependencies 
                    if all_tasks[dep].status == TaskStatus.COMPLETED
                }
                
                # Condense verbose dependency outputs via SupervisorAgent to save tokens
                dep_context = self.supervisor.condense_context(raw_dep_context)
                task.args["dependency_output"] = dep_context

                from ..security.exceptions import SecurityException
                from ..security.resolution import resolution_manager
                
                while True:
                    try:
                        # Execute with Timeout
                        result = await asyncio.wait_for(
                            self._execute_adapter(task.action, task.args, task.id),
                            timeout=self.task_timeout
                        )
                        
                        task.result = str(result)
                        task.status = TaskStatus.COMPLETED
                        self._update_task_record(run_id, task.id, status="completed", result=str(result), end_time=datetime.now(timezone.utc))
                        logger.info(f"Task {task.id} ({task.action}) ✅")
                        
                        # Fire DAG execution hook for real-time artifact streaming
                        if self.on_task_complete:
                            try:
                                await self.on_task_complete(task)
                            except Exception as hook_err:
                                logger.error(f"Task completion hook failed: {hook_err}")
                        break
                        
                    except SecurityException as se:
                        logger.warning(f"Task {task.id} 🛑 BLOCKED BY SECURITY: {se.message}")
                        task.status = TaskStatus.SUSPENDED_SECURITY
                        self._update_task_record(run_id, task.id, status="suspended_security", error=se.message)
                        
                        resolution = await resolution_manager.request_resolution(task.id, se)
                        if resolution == "CANCEL_TASK":
                            raise Exception("User cancelled the task following a security block.")
                        
                        logger.info(f"Task {task.id} 🟢 SECURITY RESOLVED ({resolution}). Retrying...")
                        task.status = TaskStatus.RUNNING
                        self._update_task_record(run_id, task.id, status="running")
                        continue
                        
                    except asyncio.TimeoutError:
                        err_msg = f"Task exceeded {self.task_timeout}s limit."
                        logger.error(f"Task {task.id} ⏳ {err_msg}")
                        task.status = TaskStatus.FAILED
                        task.result = err_msg
                        self._update_task_record(run_id, task.id, status="failed", error=err_msg, end_time=datetime.now(timezone.utc))
                        span.set_status(trace.Status(trace.StatusCode.ERROR, err_msg))
                        break
                        
                    except Exception as e:
                        logger.error(f"Task {task.id} ❌ : {e}", exc_info=True)
                        safe_error = f"Task failed: {type(e).__name__}"
                        task.result = safe_error
                        task.status = TaskStatus.FAILED
                        self._update_task_record(run_id, task.id, status="failed", error=safe_error, end_time=datetime.now(timezone.utc))
                        span.record_exception(e)
                        span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                        break
                
                return task

    # --- Persistence Helpers ---

    def _init_task_records(self, run_id: int, tasks: Dict[str, DAGTask]):
        """Creates initial PENDING records in DB."""
        from ..models import Run
        with Session(self.session_factory()) as session:
            run = session.get(Run, run_id)
            agent_id = run.agent_id if run else "executive"
            for t_id, task in tasks.items():
                # Check if exists (idempotency)
                statement = select(TaskRecord).where(TaskRecord.run_id == run_id, TaskRecord.task_dag_id == t_id)
                existing = session.exec(statement).first()
                if not existing:
                    record = TaskRecord(
                        run_id=run_id,
                        agent_id=agent_id,
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

    async def _execute_adapter(self, action: str, args: Dict[str, Any], task_id: str = "") -> Any:
        from tenacity import AsyncRetrying
        
        async for attempt in AsyncRetrying(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10), reraise=True):
            with attempt:
                # [ PPN-017 ] Kill Switch Check before routing
                # Synchronize watch_auth with real ACE biometrics if available
                if self.ace:
                    state = self.ace.get_affective_state()
                    # If we have a heart rate, we assume it's on-wrist for the kill switch check
                    self.watch_auth.update_sensors(
                        is_on_wrist=state.heart_rate > 0, 
                        heart_rate=state.heart_rate
                    )

                if self.watch_auth.locked or not self.watch_auth.verify_liveness(action):
                    raise PermissionError(f"Sovereign Kill Switch Active: Biological Liveness not verified for action '{action}'.")
                    
                adapter = self.registry.get(action)
                if not adapter:
                    raise AdapterNotFoundError(f"No adapter registered for action '{action}'.")

                # Sprint 3: Exec Approval Interceptor
                if self.approval_manager:
                    sensitive_tools = ["shell", "os_exec", "file_overwrite", "db_write"]
                    command = str(args.get("command", args.get("script", args.get("sql", ""))))
                    
                    # Request approval for sensitive tools
                    if action in sensitive_tools or command:
                        res = await self.approval_manager.request_approval(
                            command=command or action,
                            tool_name=action,
                            context=f"Task ID: {task_id}"
                        )
                        if not res.get("approved"):
                            raise PermissionError(f"Action '{action}' was denied by ExecApprovalManager.")
                
                # Fetch Tool Manifest Params (if available) to inject API keys, etc.
                from sqlmodel import Session as SqlSession
                from ..models import Run, AgentRecord
                import json
                
                injected_args = dict(args)
                with SqlSession(self.session_factory()) as session:
                    # Find agent_id from task_id -> task_record
                    from ..models import TaskRecord
                    statement = select(TaskRecord).where(TaskRecord.task_dag_id == task_id)
                    task_record = session.exec(statement).first()
                    if task_record and task_record.agent_id:
                        agent = session.get(AgentRecord, task_record.agent_id)
                        if agent and agent.tools_manifest:
                            def _safe_loads(val):
                                if not val: return {}
                                if isinstance(val, dict): return val
                                try: return json.loads(val)
                                except Exception: return {}
                            tools_data = _safe_loads(agent.tools_manifest)
                            if action in tools_data:
                                tool_config = tools_data[action]
                                if tool_config.get("enabled", False):
                                    params = tool_config.get("params", {})
                                    if isinstance(params, str):
                                        try:
                                            params = json.loads(params)
                                        except:
                                            params = {}
                                    if isinstance(params, dict):
                                        injected_args.update(params)
                
                return await adapter.execute(injected_args)
