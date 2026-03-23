
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from, Request
..security.auth import verify_authenticated
from ..models import GoalRecord
from fastapi_csrf_protect import CsrfProtect
from .. import services

router = APIRouter(prefix="/goals", tags=["Sovereign Goals"])

@router.get("/", response_model=List[GoalRecord], dependencies=[Depends(verify_authenticated)])
async def list_goals(status: Optional[str] = Query(None)):
    """List all goals, optionally filtered by status."""
    if not services.goal_engine:
        raise HTTPException(status_code=503, detail="Goals engine not ready")
    return await services.goal_engine.list_goals(status=status)

@router.post("/", dependencies=[Depends(verify_authenticated)])
async def create_goal(
    title: str = Body(...), 
    description: str = Body(...), 
    priority: str = Body("MEDIUM")
):
    """Create a new long-term goal."""
    if not services.goal_engine:
        raise HTTPException(status_code=503, detail="Goals engine not ready")
    goal_id = await services.goal_engine.create_goal(title, description, priority)
    return {"id": goal_id, "status": "CREATED"}

@router.get("/{goal_id}", response_model=GoalRecord, dependencies=[Depends(verify_authenticated)])
async def get_goal(goal_id: int):
    """Get details of a specific goal."""
    if not services.goal_engine:
        raise HTTPException(status_code=503, detail="Goals engine not ready")
    goal = await services.goal_engine.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal

@router.patch("/{goal_id}", dependencies=[Depends(verify_authenticated)])
async def update_goal(
    goal_id: int, 
    status: Optional[str] = Body(None), 
    progress: Optional[float] = Body(None)
):
    """Update goal status or progress."""
    if not services.goal_engine:
        raise HTTPException(status_code=503, detail="Goals engine not ready")
    success = await services.goal_engine.update_goal(goal_id, status=status, progress=progress)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"status": "UPDATED"}

@router.delete("/{goal_id}", dependencies=[Depends(verify_authenticated)])
async def delete_goal(goal_id: int):
    """Delete a goal."""
    if not services.goal_engine:
        raise HTTPException(status_code=503, detail="Goals engine not ready")
    success = await services.goal_engine.delete_goal(goal_id)
    if not success:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"status": "DELETED"}
