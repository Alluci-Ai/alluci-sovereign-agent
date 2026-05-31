
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from ..models import TaskUpdate
from ..security.auth import verify_authenticated
from fastapi_csrf_protect import CsrfProtect
from .. import services

router = APIRouter(tags=["Task Management"])

@router.get("/tasks", dependencies=[Depends(verify_authenticated)])
async def get_tasks(status: str = "all", priority: Optional[str] = None, timeline: Optional[str] = None, agent_id: str = "executive"):
    if not services.task_manager:
        raise HTTPException(status_code=503, detail="Task manager not ready")
    return await services.task_manager.get_tasks(status, priority, timeline, agent_id)

@router.post("/tasks", dependencies=[Depends(verify_authenticated)])
async def add_task(request: Request, task: TaskUpdate, agent_id: str = "executive", csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.task_manager:
        raise HTTPException(status_code=503, detail="Task manager not ready")
    return await services.task_manager.add_task(task, agent_id)

@router.put("/tasks/{index}", dependencies=[Depends(verify_authenticated)])
async def update_task(request: Request, index: int, task: TaskUpdate, agent_id: str = "executive", csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.task_manager:
        raise HTTPException(status_code=503, detail="Task manager not ready")
    result = await services.task_manager.update_task(index, task, agent_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result

@router.delete("/tasks/{index}", dependencies=[Depends(verify_authenticated)])
async def delete_task(request: Request, index: int, agent_id: str = "executive", csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.task_manager:
        raise HTTPException(status_code=503, detail="Task manager not ready")
    if not await services.task_manager.delete_task(index, agent_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted"}
