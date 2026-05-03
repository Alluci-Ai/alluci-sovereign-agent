from typing import Optional
from fastapi import APIRouter, Depends
from sqlmodel import Session, select, desc
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
):
    with Session(db_engine) as session:
        stmt = select(Run).order_by(desc(Run.created_at)).offset(offset).limit(limit)
        if status:
            stmt = stmt.where(Run.status == status)
        runs = session.exec(stmt).all()

        result = []
        for run in runs:
            task_stmt = select(TaskRecordModel).where(TaskRecordModel.run_id == run.id)
            tasks = session.exec(task_stmt).all()
            result.append({
                "id": run.id,
                "objective": run.objective,
                "status": run.status,
                "created_at": run.created_at,
                "task_count": len(tasks),
                "tasks": [
                    {"id": t.id, "dag_id": t.task_dag_id, "status": t.status}
                    for t in tasks
                ],
            })
        return result
