
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from ..models import TaskRecord as TaskRecordModel, TaskUpdate
from ..security.auth import verify_authenticated
from .. import services

router = APIRouter(tags=["Task Management"])

@router.get("/tasks", dependencies=[Depends(verify_authenticated)])
async def get_tasks(status: str = "all", priority: str = None, timeline: str = None):
    if not services.task_manager:
        raise HTTPException(status_code=503, detail="Task manager not ready")
    return await services.task_manager.get_tasks(status, priority, timeline)

@router.post("/tasks", dependencies=[Depends(verify_authenticated)])
async def add_task(task: TaskUpdate):
    if not services.task_manager:
        raise HTTPException(status_code=503, detail="Task manager not ready")
    return await services.task_manager.add_task(task)

@router.put("/tasks/{index}", dependencies=[Depends(verify_authenticated)])
async def update_task(index: int, task: TaskUpdate):
    if not services.task_manager:
        raise HTTPException(status_code=503, detail="Task manager not ready")
    result = await services.task_manager.update_task(index, task)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result

@router.delete("/tasks/{index}", dependencies=[Depends(verify_authenticated)])
async def delete_task(index: int):
    if not services.task_manager:
        raise HTTPException(status_code=503, detail="Task manager not ready")
    if not await services.task_manager.delete_task(index):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted"}
