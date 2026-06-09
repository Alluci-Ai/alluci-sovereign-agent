# backend/tests/dummy_task.py
"""Simple dummy task for queue integration testing.
The function records a successful result into the queue.
"""
import asyncio
from ..queue import record_result

async def dummy(task_id: str) -> None:
    # Simulate some async work
    await asyncio.sleep(0.1)
    result = {"status": "success", "message": "dummy completed"}
    record_result(task_id, result)
