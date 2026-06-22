# backend/queue.py
"""Task queue wrapper around QueuedTask model.
Provides simple API to enqueue jobs, update status, record checkpoints and results.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlmodel import Session

from .models import QueuedTask, TaskStatus
from .database import engine

def enqueue(func_path: str, *args: Any, **kwargs: Any) -> QueuedTask:
    """Create a new queued task.

    Parameters
    ----------
    func_path: str
        Fully qualified import path to the callable (e.g. "backend.orchestrator.ExecutiveOrchestrator._run_research").
    *args, **kwargs:
        Arguments that will be passed to the callable when the worker executes it.
    """
    payload = {
        "func_path": func_path,
        "args": list(args),
        "kwargs": kwargs,
    }
    task = QueuedTask(
        id=str(uuid.uuid4()),
        status=TaskStatus.QUEUED,
        payload=payload,
    )
    with Session(engine) as session:
        session.add(task)
        session.commit()
        session.refresh(task)
    return task


def set_status(task_id: str, status: TaskStatus) -> None:
    """Update the status of a queued task."""
    with Session(engine) as session:
        task = session.get(QueuedTask, task_id)
        if task:
            task.status = status
            task.updated_at = datetime.now(timezone.utc)
            session.add(task)
            session.commit()


def record_checkpoint(task_id: str, data: Dict[str, Any]) -> None:
    """Store intermediate checkpoint data for a task."""
    with Session(engine) as session:
        task = session.get(QueuedTask, task_id)
        if task:
            task.checkpoint = data
            task.updated_at = datetime.now(timezone.utc)
            session.add(task)
            session.commit()


def record_result(task_id: str, result: Dict[str, Any], error: Optional[str] = None) -> None:
    """Record the final result (or error) of a task and set its terminal status."""
    with Session(engine) as session:
        task = session.get(QueuedTask, task_id)
        if task:
            task.result = result
            task.status = TaskStatus.FAILED if error else TaskStatus.COMPLETED
            if error:
                # Store the error message in the payload for visibility
                if isinstance(task.payload, dict):
                    task.payload["error"] = error
                else:
                    task.payload = {"error": error}
            task.updated_at = datetime.now(timezone.utc)
            session.add(task)
            session.commit()

