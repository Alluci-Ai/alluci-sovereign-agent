"""
Cron Engine for the Polytope Sovereign OS.

Provides three schedule types:
  - interval: run every N minutes/hours/days
  - cron: standard 5-field cron expression
  - run_at: one-shot at a specific ISO datetime

Each job supports per-invocation model overrides, delivery routing
to channel adapters, and a run history log.

Reference: Sovereign Spec Sections 3.1–3.8
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
from sqlmodel import Session, select, col

logger = logging.getLogger("CronEngine")


class ScheduleType(str, Enum):
    INTERVAL = "interval"
    CRON = "cron"
    RUN_AT = "run_at"


class DeliveryMode(str, Enum):
    ANNOUNCE_SUMMARY = "announce-summary"
    POST_TRANSCRIPT = "post-transcript"
    NONE = "none"


class CronEngine:
    """
    Evaluates due jobs on a tick loop, executes them through the
    orchestrator, and records run history.
    """

    def __init__(self, db_engine, orchestrator=None, channel_registry=None, task_manager=None):
        self.db_engine = db_engine
        self.orchestrator = orchestrator
        self.channel_registry = channel_registry or {}
        self.task_manager = task_manager
        self._running = False
        self._tick_task: Optional[asyncio.Task] = None
        self._tick_interval = 60  # seconds

    # ── Lifecycle ─────────────────────────────────────────────────────────

    async def start(self):
        """Start the cron tick loop."""
        if self._running:
            return
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop())
        logger.info("[CronEngine] Started")

    async def stop(self):
        """Stop the cron tick loop."""
        self._running = False
        if self._tick_task:
            self._tick_task.cancel()
            try:
                await self._tick_task
            except asyncio.CancelledError:
                pass
        logger.info("[CronEngine] Stopped")

    async def _tick_loop(self):
        """Main loop: evaluate all enabled jobs each tick."""
        while self._running:
            try:
                await self._evaluate_jobs()
            except Exception as e:
                logger.error(f"[CronEngine] Tick error: {e}")
            await asyncio.sleep(self._tick_interval)

    # ── Job Evaluation ────────────────────────────────────────────────────

    async def _evaluate_jobs(self):
        """Check all enabled jobs and run any that are due."""
        from .models import CronJob

        with Session(self.db_engine) as session:
            stmt = select(CronJob).where(CronJob.enabled == True)  # noqa: E712
            jobs = session.exec(stmt).all()

        now = datetime.now(timezone.utc)

        for job in jobs:
            if self._is_due(job, now):
                await self._execute_job(job, now)

    def _is_due(self, job, now: datetime) -> bool:
        """Determine if a job should run at the current tick."""

        if job.schedule_type == ScheduleType.INTERVAL:
            if job.last_run_at is None:
                return True
            # schedule_value is expected to be minutes for interval
            try:
                interval_minutes = int(job.schedule_value)
            except (ValueError, TypeError):
                return False
            delta = timedelta(minutes=interval_minutes)
            return (now - job.last_run_at) >= delta

        elif job.schedule_type == ScheduleType.CRON:
            try:
                from croniter import croniter
                cron = croniter(job.schedule_value, job.last_run_at or now - timedelta(days=1))
                next_run = cron.get_next(datetime)
                if next_run.tzinfo is None:
                    next_run = next_run.replace(tzinfo=timezone.utc)
                return now >= next_run
            except ImportError:
                logger.warning("[CronEngine] croniter not installed, skipping cron-type jobs")
                return False
            except Exception as e:
                logger.error(f"[CronEngine] Cron parse error for job {job.id}: {e}")
                return False

        elif job.schedule_type == ScheduleType.RUN_AT:
            if job.last_run_at is not None:
                return False  # one-shot already fired
            try:
                target = datetime.fromisoformat(job.schedule_value)
                if target.tzinfo is None:
                    target = target.replace(tzinfo=timezone.utc)
                return now >= target
            except Exception:
                return False

        return False

    # ── Execution ─────────────────────────────────────────────────────────

    async def _execute_job(self, job, now: datetime):
        """Execute a single cron job and record the run."""
        from .models import CronRun

        logger.info(f"[CronEngine] Executing job: {job.name} (id={job.id})")
        started_at = datetime.now(timezone.utc)
        status = "ok"
        log_text = ""
        delivery_status = "none"

        try:
            # --- TASK INTEGRATION ---
            # Create a Task record so it appears in the Task Manager
            if self.task_manager:
                from .models import TaskUpdate, TaskPriority
                task_desc = f"[CRON] {job.name}: {job.payload or 'Execute scheduled task'}"
                # Map thinking level or some other attribute to priority if needed, but default to MEDIUM
                await self.task_manager.add_task(TaskUpdate(
                    description=task_desc,
                    completed=False,
                    priority=TaskPriority.MEDIUM
                ))

            if self.orchestrator:
                # Build the objective from the job's payload
                objective = f"[CRON JOB: {job.name}] {job.payload or 'Execute scheduled task'}"

                # Apply model overrides
                overrides = {}
                if job.model_override:
                    overrides["model"] = job.model_override
                if job.thinking_level:
                    overrides["thinking_level"] = job.thinking_level

                result = await self.orchestrator.execute_objective(
                    objective=objective,
                    autonomy="RESTRICTED",
                )
                log_text = str(result)[:4000]  # Cap log length
            else:
                log_text = "No orchestrator connected"
                status = "skipped"

        except Exception as e:
            status = "error"
            log_text = f"{type(e).__name__}: {e}"
            logger.error(f"[CronEngine] Job {job.id} failed: {e}")

        finished_at = datetime.now(timezone.utc)

        # Delivery routing
        if status == "ok" and job.delivery_mode and job.delivery_mode != DeliveryMode.NONE:
            delivery_status = await self._deliver(job, log_text)

        # Record run history
        run = CronRun(
            job_id=job.id,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            delivery_status=delivery_status,
            log_text=log_text,
        )

        with Session(self.db_engine) as session:
            session.add(run)
            # Update last_run_at on the job
            db_job = session.get(type(job), job.id)
            if db_job:
                db_job.last_run_at = now
                session.add(db_job)
            session.commit()

        logger.info(f"[CronEngine] Job {job.id} completed: {status}")

    async def _deliver(self, job, content: str) -> str:
        """Route job output to the configured channel adapter (Sovereign Spec §3.2)."""
        if not job.delivery_channel or not self.channel_registry:
            return "no_channel"

        adapter = self.channel_registry.get(job.delivery_channel)
        if not adapter:
            return "adapter_not_found"

        try:
            recipient = job.delivery_to or ""
            # Prepare extra routing context
            kwargs = {}
            if job.delivery_account:
                kwargs["account"] = job.delivery_account

            if job.delivery_mode == DeliveryMode.ANNOUNCE_SUMMARY:
                # Truncate for summary
                summary = content[:500] + ("..." if len(content) > 500 else "")
                await adapter.send(recipient, f"📋 Cron Job '{job.name}' completed:\n{summary}", **kwargs)
            elif job.delivery_mode == DeliveryMode.POST_TRANSCRIPT:
                await adapter.send(recipient, f"📜 Full transcript for '{job.name}':\n{content}", **kwargs)
            
            return "delivered"
        except Exception as e:
            logger.error(f"[CronEngine] Delivery failed for job {job.id}: {e}")
            return f"error: {e}"

    # ── CRUD Helpers (called from FastAPI routes) ─────────────────────────

    def list_jobs(self) -> List[Dict[str, Any]]:
        from .models import CronJob
        with Session(self.db_engine) as session:
            jobs = session.exec(select(CronJob)).all()
            return [self._job_to_dict(j) for j in jobs]

    def get_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        from .models import CronJob
        with Session(self.db_engine) as session:
            job = session.get(CronJob, job_id)
            return self._job_to_dict(job) if job else None

    def create_job(self, data: Dict[str, Any]) -> Dict[str, Any]:
        from .models import CronJob
        job = CronJob(**data)
        with Session(self.db_engine) as session:
            session.add(job)
            session.commit()
            session.refresh(job)
            return self._job_to_dict(job)

    def update_job(self, job_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        from .models import CronJob
        with Session(self.db_engine) as session:
            job = session.get(CronJob, job_id)
            if not job:
                return None
            for k, v in data.items():
                if hasattr(job, k):
                    setattr(job, k, v)
            session.add(job)
            session.commit()
            session.refresh(job)
            return self._job_to_dict(job)

    def delete_job(self, job_id: int) -> bool:
        from .models import CronJob
        with Session(self.db_engine) as session:
            job = session.get(CronJob, job_id)
            if not job:
                return False
            session.delete(job)
            session.commit()
            return True

    def clone_job(self, job_id: int) -> Optional[Dict[str, Any]]:
        from .models import CronJob
        with Session(self.db_engine) as session:
            original = session.get(CronJob, job_id)
            if not original:
                return None
            clone = CronJob(
                name=f"{original.name} (copy)",
                schedule_type=original.schedule_type,
                schedule_value=original.schedule_value,
                payload=original.payload,
                model_override=original.model_override,
                thinking_level=original.thinking_level,
                delivery_channel=original.delivery_channel,
                delivery_account=original.delivery_account,
                delivery_to=original.delivery_to,
                delivery_mode=original.delivery_mode,
                reset_context=original.reset_context,
                enabled=False,  # cloned jobs start disabled
            )
            session.add(clone)
            session.commit()
            session.refresh(clone)
            return self._job_to_dict(clone)

    def force_run(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Schedule an immediate run regardless of schedule."""
        from .models import CronJob
        with Session(self.db_engine) as session:
            job = session.get(CronJob, job_id)
            if not job:
                return None
        asyncio.create_task(self._execute_job(job, datetime.now(timezone.utc)))
        return {"status": "triggered", "job_id": job_id}

    def get_runs(
        self,
        job_id: Optional[int] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        from .models import CronRun
        with Session(self.db_engine) as session:
            stmt = select(CronRun).order_by(col(CronRun.started_at).desc())
            if job_id:
                stmt = stmt.where(CronRun.job_id == job_id)
            if status:
                stmt = stmt.where(CronRun.status == status)
            stmt = stmt.limit(limit)
            runs = session.exec(stmt).all()
            return [self._run_to_dict(r) for r in runs]

    # ── Serialization ─────────────────────────────────────────────────────

    @staticmethod
    def _job_to_dict(job) -> Dict[str, Any]:
        return {
            "id": job.id,
            "name": job.name,
            "schedule_type": job.schedule_type,
            "schedule_value": job.schedule_value,
            "payload": job.payload,
            "model_override": job.model_override,
            "thinking_level": job.thinking_level,
            "delivery_channel": job.delivery_channel,
            "delivery_account": job.delivery_account,
            "delivery_to": job.delivery_to,
            "delivery_mode": job.delivery_mode,
            "reset_context": job.reset_context,
            "enabled": job.enabled,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "last_run_at": job.last_run_at.isoformat() if job.last_run_at else None,
        }

    @staticmethod
    def _run_to_dict(run) -> Dict[str, Any]:
        return {
            "id": run.id,
            "job_id": run.job_id,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "status": run.status,
            "delivery_status": run.delivery_status,
            "log_text": run.log_text,
        }
