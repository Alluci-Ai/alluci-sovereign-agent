# backend/worker.py
"""Simple polling worker for queued tasks.
Runs in a loop, picks queued tasks, marks them RUNNING, executes the target
callable, and records the result.
"""
import importlib
import time
import asyncio
import inspect
from typing import Any
from sqlmodel import select

from .queue import set_status, record_result, TaskStatus
from .models import QueuedTask
from .database import get_session


def _execute_callable(func_path: str, args: list[Any], task_id: str) -> None:
    """Import and execute the target callable.

    The callable can be an async function or a regular function. It receives the
    positional ``args`` defined during ``enqueue`` followed by the ``task_id`` so
    that it can report progress via the queue API.
    """
    module_path, attr_name = func_path.rsplit(".", 1)
    module = importlib.import_module(module_path)
    func = getattr(module, attr_name)
    if inspect.iscoroutinefunction(func):
        asyncio.run(func(*args, task_id))
    else:
        func(*args, task_id)


def poll_once() -> None:
    """Fetch a single queued task and process it.

    This function is convenient for unit tests – it processes at most one task
    and then returns, allowing the test to control the loop.
    """
    with get_session() as session:
        stmt = select(QueuedTask).where(QueuedTask.status == TaskStatus.QUEUED).limit(1)
        task = session.exec(stmt).first()
        if not task:
            return
        # Mark as running
        set_status(task.id, TaskStatus.RUNNING)
        try:
            payload = task.payload or {}
            func_path = payload.get("func_path")
            if not isinstance(func_path, str):
                raise ValueError("Invalid or missing func_path in task payload")
            args = payload.get("args", [])
            _execute_callable(func_path, args, task.id)
        except Exception as e:  # pragma: no cover – defensive
            record_result(task.id, {"status": "failed", "error": str(e)}, error=str(e))


def run_worker(poll_interval: float = 1.0) -> None:
    """Continuously poll for queued tasks.

    Intended for production use. The function blocks forever; run it via
    ``python -m backend.worker``.
    """
    while True:
        poll_once()
        time.sleep(poll_interval)


if __name__ == "__main__":  # pragma: no cover
    run_worker()
