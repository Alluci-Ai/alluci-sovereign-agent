from typing import Optional
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, desc, col, or_
from ..database import engine as db_engine
from ..models import Run, TaskRecord as TaskRecordModel
from ..security.auth import verify_authenticated
# NOTE: CsrfProtect import removed — this router currently only contains GET endpoints.
# When adding mutation endpoints (POST/PUT/DELETE), import CsrfProtect and apply the
# singleton pattern: `csrf_protect: CsrfProtect = Depends()` + `await csrf_protect.validate_csrf(request)`

router = APIRouter(tags=["DAG & Pipeline Runs"])

@router.get("/dag/runs", dependencies=[Depends(verify_authenticated)])
async def list_dag_runs(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    agent_id: str = "executive",
    include_subagents: bool = True,
):
    with Session(db_engine) as session:
        stmt = select(Run)
        if agent_id != "all":
            if include_subagents:
                stmt = stmt.where(col(Run.agent_id).in_([agent_id, "rocco", "a32eb383"]))
            else:
                stmt = stmt.where(col(Run.agent_id) == agent_id)
                
        if status:
            stmt = stmt.where(col(Run.status) == status)
            
        stmt = stmt.order_by(desc(col(Run.created_at))).offset(offset).limit(limit)
        runs = session.exec(stmt).all()

        result = []
        for run in runs:
            task_stmt = select(TaskRecordModel).where(col(TaskRecordModel.run_id) == run.id)
            tasks = session.exec(task_stmt).all()
            result.append({
                "id": run.id,
                "objective": run.objective,
                "status": run.status,
                "created_at": run.created_at,
                "agent_id": run.agent_id,
                "task_count": len(tasks),
                "tasks": [
                    {"id": t.id, "dag_id": t.task_dag_id, "status": t.status}
                    for t in tasks
                ],
            })
        # Get total count for pagination
        count_stmt = select(Run)
        if agent_id != "all":
            if include_subagents:
                count_stmt = count_stmt.where(col(Run.agent_id).in_([agent_id, "rocco", "a32eb383"]))
            else:
                count_stmt = count_stmt.where(col(Run.agent_id) == agent_id)
        if status:
            count_stmt = count_stmt.where(col(Run.status) == status)
        total = len(session.exec(count_stmt).all())

        return {"runs": result, "total": total}

@router.get("/dag/runs/{run_id}", dependencies=[Depends(verify_authenticated)])
async def get_dag_run(run_id: int):
    with Session(db_engine) as session:
        run = session.get(Run, run_id)
        if not run:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Run not found")
        task_stmt = select(TaskRecordModel).where(col(TaskRecordModel.run_id) == run.id)
        tasks = session.exec(task_stmt).all()
        return {
            "id": run.id,
            "objective": run.objective,
            "status": run.status,
            "created_at": run.created_at,
            "agent_id": run.agent_id,
            "task_count": len(tasks),
            "tasks": [
                {"id": t.id, "dag_id": t.task_dag_id, "status": t.status}
                for t in tasks
            ]
        }

@router.get("/dag/runs/{run_id}/tasks", dependencies=[Depends(verify_authenticated)])
async def list_dag_run_tasks(run_id: int):
    with Session(db_engine) as session:
        task_stmt = select(TaskRecordModel).where(col(TaskRecordModel.run_id) == run_id)
        tasks = session.exec(task_stmt).all()
        return {
            "tasks": [
                {
                    "id": t.id,
                    "task_dag_id": t.task_dag_id,
                    "action": t.action,
                    "assignee": getattr(t, "assignee", "rocco") or "rocco",
                    "status": t.status,
                    "dependencies": getattr(t, "dependencies", []),
                    "args": t.args or {},
                    "result": t.result,
                    "error": t.error,
                    "start_time": getattr(t, "start_time", t.updated_at),
                    "end_time": t.end_time
                }
                for t in tasks
            ]
        }
