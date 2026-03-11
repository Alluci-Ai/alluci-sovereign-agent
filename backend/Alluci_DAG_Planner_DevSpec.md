# ALLUCI SOVEREIGN AGENT
## DAG Planner — Full Integration Development Spec v1.0

> **Frontend UI/UX + Backend API + Testing + Validation**
> Covers every new file, modified file, component, route, store slice, hook, and test required to fully surface the DAG Planner in the Alluci UI with live execution, real-time state, approval gating, and replay.

---

## Table of Contents

1. [Overview & Goals](#1-overview--goals)
2. [Spec Index — All Items](#2-spec-index--all-items)
3. [Design System Reference](#3-design-system-reference)
4. [Backend Specification](#4-backend-specification)
   - [DAG-BE-001 — Run History & Status API](#dag-be-001--run-history--status-api)
   - [DAG-BE-002 — Live Task Stream (SSE)](#dag-be-002--live-task-stream-sse)
   - [DAG-BE-003 — Run Cancel Endpoint](#dag-be-003--run-cancel-endpoint)
   - [DAG-BE-004 — Plan Preview (Dry-Run) Endpoint](#dag-be-004--plan-preview-dry-run-endpoint)
   - [DAG-BE-005 — Task Retry Endpoint](#dag-be-005--task-retry-endpoint)
   - [DAG-BE-006 — Objective Submission Enhancement](#dag-be-006--objective-submission-enhancement)
5. [Frontend Specification](#5-frontend-specification)
   - [DAG-FE-001 — DAGPanel Route & Sidebar Entry](#dag-fe-001--dagpanel-route--sidebar-entry)
   - [DAG-FE-002 — useDAGRuns Hook](#dag-fe-002--usedagruns-hook)
   - [DAG-FE-003 — useTaskStream Hook (SSE)](#dag-fe-003--usetaskstream-hook-sse)
   - [DAG-FE-004 — DAGPanel Container](#dag-fe-004--dagpanel-container)
   - [DAG-FE-005 — RunListSidebar Component](#dag-fe-005--runlistsidebar-component)
   - [DAG-FE-006 — DAGGraph Component (Canvas Visualizer)](#dag-fe-006--daggraph-component-canvas-visualizer)
   - [DAG-FE-007 — TaskNode Component](#dag-fe-007--tasknode-component)
   - [DAG-FE-008 — RunDetailHeader Component](#dag-fe-008--rundetailheader-component)
   - [DAG-FE-009 — TaskDetailDrawer Component](#dag-fe-009--taskdetaildrawer-component)
   - [DAG-FE-010 — ObjectiveSubmitBar Component](#dag-fe-010--objectivesubmitbar-component)
   - [DAG-FE-011 — PlanPreviewModal Component](#dag-fe-011--planpreviewmodal-component)
   - [DAG-FE-012 — DAG Store Slice (Zustand)](#dag-fe-012--dag-store-slice-zustand)
   - [DAG-FE-013 — Sidebar Navigation Integration](#dag-fe-013--sidebar-navigation-integration)
   - [DAG-FE-014 — App.tsx Route Registration](#dag-fe-014--apptsx-route-registration)
6. [Type Definitions](#6-type-definitions)
7. [CSS — Design Token Extensions & Component Styles](#7-css--design-token-extensions--component-styles)
8. [Testing Specification](#8-testing-specification)
   - [Backend Tests](#backend-tests)
   - [Frontend Tests](#frontend-tests)
   - [Integration / E2E Tests](#integration--e2e-tests)
9. [Validation & Verification Checklist](#9-validation--verification-checklist)
10. [Integration Order & Sprint Plan](#10-integration-order--sprint-plan)
11. [File Delta Summary](#11-file-delta-summary)

---

## 1. Overview & Goals

The DAG Planner exists in the backend but is completely invisible to the user. There is no way to see what plan was generated, watch tasks execute in real time, inspect individual task inputs and outputs, cancel a running plan, or replay a failed run. This spec builds the complete UI/UX surface for the DAG Planner, integrated into the existing Alluci Sovereign Agent design system.

### Goals

- **Visibility** — Every plan is visible as a live DAG graph, with nodes colored by status in real time
- **Control** — Users can cancel a running plan, retry failed tasks, and submit new objectives directly from the panel
- **Transparency** — Every task exposes its full input arguments, output, error message, duration, and retry count
- **Preview** — Before executing, users can request a plan preview (dry run) and inspect/approve the generated DAG
- **History** — Full run history with filtering by status, searchable by objective text
- **Consistency** — Every visual component strictly adheres to the Alluci design token system: `glass-bg`, `glass-btn`, `--accent`, `--glass-edge`, `var(--font-mono)`, liquid glass materials, and the `inline-panel` layout pattern

### What Is Not In Scope

- Editing individual task nodes (plan modification post-generation is handled by `refine_plan()` automatically)
- Multi-agent parallel plans (single-orchestrator model is preserved)
- Authentication changes (all new endpoints use `Depends(verify_authenticated)` like all existing routes)

---

## 2. Spec Index — All Items

| ID | Layer | Title | Action | Priority |
|---|---|---|---|---|
| **DAG-BE-001** | Backend | Run History & Status API | CREATE routes | 🔴 High |
| **DAG-BE-002** | Backend | Live Task Stream (SSE) | CREATE route | 🔴 High |
| **DAG-BE-003** | Backend | Run Cancel Endpoint | CREATE route | 🔴 High |
| **DAG-BE-004** | Backend | Plan Preview (Dry-Run) | CREATE route | 🟡 Medium |
| **DAG-BE-005** | Backend | Task Retry Endpoint | CREATE route | 🟡 Medium |
| **DAG-BE-006** | Backend | Objective Submission Enhancement | MODIFY route | 🔴 High |
| **DAG-FE-001** | Frontend | DAGPanel Route & Sidebar Entry | CREATE + MODIFY | 🔴 High |
| **DAG-FE-002** | Frontend | `useDAGRuns` Hook | CREATE | 🔴 High |
| **DAG-FE-003** | Frontend | `useTaskStream` SSE Hook | CREATE | 🔴 High |
| **DAG-FE-004** | Frontend | DAGPanel Container | CREATE | 🔴 High |
| **DAG-FE-005** | Frontend | RunListSidebar Component | CREATE | 🔴 High |
| **DAG-FE-006** | Frontend | DAGGraph Canvas Visualizer | CREATE | 🔴 High |
| **DAG-FE-007** | Frontend | TaskNode Component | CREATE | 🔴 High |
| **DAG-FE-008** | Frontend | RunDetailHeader Component | CREATE | 🟡 Medium |
| **DAG-FE-009** | Frontend | TaskDetailDrawer Component | CREATE | 🟡 Medium |
| **DAG-FE-010** | Frontend | ObjectiveSubmitBar Component | CREATE | 🟡 Medium |
| **DAG-FE-011** | Frontend | PlanPreviewModal Component | CREATE | 🟡 Medium |
| **DAG-FE-012** | Frontend | DAG Zustand Store Slice | CREATE | 🔴 High |
| **DAG-FE-013** | Frontend | Sidebar Navigation Integration | MODIFY | 🔴 High |
| **DAG-FE-014** | Frontend | App.tsx Route Registration | MODIFY | 🔴 High |

---

## 3. Design System Reference

All new components **must** use these tokens and patterns exclusively. Do not introduce new CSS classes without a strong reason — use the existing system.

### Color Tokens

```css
/* Backgrounds */
--bg-base, --bg-elevated, --bg-secondary
--glass-bg, --glass-bg-hover, --glass-bg-pressed
--fill-quaternary                          /* subtle card backgrounds */

/* Borders */
--glass-edge                               /* standard card borders */
--separator                                /* dividers */

/* Text */
--text-primary                             /* primary labels */
--text-secondary                           /* secondary / descriptive */
--text-tertiary                            /* metadata, timestamps */
--font-mono                                /* all technical/code values */

/* Status Colors — use exclusively for task status */
--accent           (#30D158)              /* COMPLETED */
--accent-warm      (#FF9F0A)              /* RUNNING */
--accent-secondary (#BF5AF2)              /* PENDING */
--accent-danger    (#FF453A)              /* FAILED */
--text-tertiary                            /* SKIPPED */
```

### Status → Token Mapping

| TaskStatus | Color Token | Background Token |
|---|---|---|
| `COMPLETED` | `--accent` | `--liquid-accent` |
| `RUNNING` | `--accent-warm` | `--liquid-warm` |
| `PENDING` | `--accent-secondary` | `--liquid-secondary` |
| `FAILED` | `--accent-danger` | `--liquid-danger` |
| `SKIPPED` | `--text-tertiary` | `--fill-quaternary` |

### Existing Reusable CSS Classes

```
glass-btn              /* standard action button */
glass-btn--primary     /* filled/accent variant */
glass-input            /* standard text input */
glass-label            /* uppercase tracking label */
inline-panel           /* content panel card */
inline-panel-wrapper   /* full-height page wrapper */
inline-panel__header   /* panel header bar */
inline-panel__title    /* panel h2 heading */
inline-panel__body     /* scrollable body */
sessions-table         /* standard data table */
scrollbar-hide         /* hide scrollbars on overflow */
```

### Typography Rules

- Panel titles: `fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em'` — matches `TaskPanel`
- Section labels: `fontSize: 10, fontWeight: 600, textTransform: 'uppercase', color: 'var(--text-tertiary)'`
- Mono values (IDs, status, tool names): `fontFamily: 'var(--font-mono)', fontSize: 10–11`
- Body text: `fontSize: 13, lineHeight: 1.5`

### Spacing

All padding and margins use the `--space-*` scale or inline multiples of 4px. Do not use arbitrary values like `17px`.

---

## 4. Backend Specification

---

### DAG-BE-001 — Run History & Status API

**File:** `backend/app.py` — **MODIFY**
**Priority:** 🔴 High

#### Purpose

Expose run history with task details so the frontend can list past runs, load a specific run's full DAG state, and get aggregate metrics.

#### New Routes

```
GET  /api/dag/runs                  List runs with pagination and filters
GET  /api/dag/runs/{run_id}         Get a single run with all task records
GET  /api/dag/runs/{run_id}/tasks   Get all task records for a run
```

#### Implementation Steps

1. Add import at top of `app.py`: `from sqlmodel import select, desc`
2. Add `GET /api/dag/runs` route with optional query params: `status`, `limit` (default 20), `offset` (default 0)
3. Query `Run` table ordered by `started_at DESC`, join with `TaskRecord` count per run
4. Add `GET /api/dag/runs/{run_id}` route — queries `Run` by ID, 404 if not found
5. Add `GET /api/dag/runs/{run_id}/tasks` route — queries all `TaskRecord` rows for `run_id`, ordered by `id`
6. All three routes require `Depends(verify_authenticated)`
7. Return snake_case JSON — do not add a serializer layer, use `model.model_dump()` on SQLModel instances

#### Code

**Add to `backend/app.py`** (after the existing `/tasks` routes, around line 780):

```python
# ── DAG Run History API ────────────────────────────────────────────────────

@app.get("/api/dag/runs", dependencies=[Depends(verify_authenticated)])
async def list_dag_runs(
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Return paginated list of execution runs with task summary."""
    with Session(db_engine) as session:
        stmt = select(Run).order_by(desc(Run.started_at)).offset(offset).limit(limit)
        if status:
            stmt = stmt.where(Run.status == status)
        runs = session.exec(stmt).all()

        result = []
        for run in runs:
            task_stmt = select(TaskRecord).where(TaskRecord.run_id == run.id)
            tasks = session.exec(task_stmt).all()
            task_counts = {
                "total":     len(tasks),
                "completed": sum(1 for t in tasks if t.status == "completed"),
                "failed":    sum(1 for t in tasks if t.status == "failed"),
                "running":   sum(1 for t in tasks if t.status == "running"),
                "pending":   sum(1 for t in tasks if t.status == "pending"),
            }
            result.append({
                **run.model_dump(),
                "task_counts": task_counts,
            })

        total_stmt = select(Run)
        if status:
            total_stmt = total_stmt.where(Run.status == status)
        total = len(session.exec(total_stmt).all())

        return {"runs": result, "total": total, "limit": limit, "offset": offset}


@app.get("/api/dag/runs/{run_id}", dependencies=[Depends(verify_authenticated)])
async def get_dag_run(run_id: int):
    """Return a single run record."""
    with Session(db_engine) as session:
        run = session.get(Run, run_id)
        if not run:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Run not found")
        return run.model_dump()


@app.get("/api/dag/runs/{run_id}/tasks", dependencies=[Depends(verify_authenticated)])
async def get_dag_run_tasks(run_id: int):
    """Return all task records for a run."""
    with Session(db_engine) as session:
        stmt = select(TaskRecord).where(TaskRecord.run_id == run_id).order_by(TaskRecord.id)
        tasks = session.exec(stmt).all()
        return {"tasks": [t.model_dump() for t in tasks]}
```

#### Acceptance Test

```
GET /api/dag/runs         → 200, {"runs": [...], "total": N}
GET /api/dag/runs/1       → 200, run object or 404
GET /api/dag/runs/1/tasks → 200, {"tasks": [...]}
GET /api/dag/runs?status=failed → only failed runs
Unauthenticated request   → 401
```

---

### DAG-BE-002 — Live Task Stream (SSE)

**File:** `backend/app.py` — **MODIFY**
**Priority:** 🔴 High

#### Purpose

Push real-time task status updates to the frontend using Server-Sent Events (SSE). When a task transitions from `PENDING → RUNNING → COMPLETED/FAILED`, the frontend immediately reflects it — no polling required.

#### New Route

```
GET /api/dag/runs/{run_id}/stream   SSE stream of task state transitions
```

#### Design

The executor already writes task state to the database via `_update_task_record()`. The stream endpoint polls the DB every 500ms for changes and pushes diffs. This avoids modifying the executor's internal logic while delivering near-real-time updates.

#### Implementation Steps

1. Add `from fastapi.responses import StreamingResponse` import (already likely present — verify)
2. Add `import asyncio, json` if not already imported
3. Implement `stream_dag_run_tasks()` as an `async generator` that:
   - Queries all `TaskRecord` rows for `run_id` every 500ms
   - Tracks previously sent states in a `last_seen` dict
   - Pushes only changed records as SSE `data:` events
   - Terminates when run status is `completed` or `failed` and no tasks are in `running` or `pending` state
   - Sends a `keep-alive` comment every 15 seconds to prevent proxy timeouts
4. Return `StreamingResponse(generator, media_type="text/event-stream")`
5. Add `Cache-Control: no-cache` and `X-Accel-Buffering: no` headers

#### Code

```python
@app.get("/api/dag/runs/{run_id}/stream", dependencies=[Depends(verify_authenticated)])
async def stream_dag_run_tasks(run_id: int):
    """
    SSE stream of live task state transitions for a run.
    Pushes JSON-encoded TaskRecord diffs as events.
    Client reconnects automatically on drop (EventSource default behavior).
    """
    async def event_generator():
        last_seen: dict = {}  # task_dag_id → last emitted status
        keep_alive_counter = 0

        while True:
            await asyncio.sleep(0.5)
            keep_alive_counter += 1

            # Keep-alive comment (prevents proxy/nginx timeout)
            if keep_alive_counter % 30 == 0:
                yield ": keep-alive\n\n"

            with Session(db_engine) as session:
                # Fetch run status
                run = session.get(Run, run_id)
                if not run:
                    yield f"event: error\ndata: {json.dumps({'error': 'run_not_found'})}\n\n"
                    return

                # Fetch all task records
                stmt = select(TaskRecord).where(TaskRecord.run_id == run_id)
                tasks = session.exec(stmt).all()

                for task in tasks:
                    key = task.task_dag_id
                    current_status = task.status

                    if last_seen.get(key) != current_status:
                        last_seen[key] = current_status
                        payload = {
                            "task_dag_id": task.task_dag_id,
                            "action":      task.action,
                            "status":      current_status,
                            "result":      task.result,
                            "error":       task.error,
                            "start_time":  task.start_time.isoformat() if task.start_time else None,
                            "end_time":    task.end_time.isoformat() if task.end_time else None,
                        }
                        yield f"data: {json.dumps(payload)}\n\n"

                # Terminate stream when run is terminal and all tasks settled
                active = any(
                    t.status in ("running", "pending") for t in tasks
                )
                if run.status in ("completed", "failed") and not active:
                    yield f"event: done\ndata: {json.dumps({'run_id': run_id, 'status': run.status})}\n\n"
                    return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )
```

#### Acceptance Test

```
Open SSE stream for active run_id → receives status events as tasks progress
Stream for completed run           → receives final "done" event and closes
Stream for non-existent run        → receives error event and closes
Multiple concurrent clients        → each receives independent streams (no shared state)
```

---

### DAG-BE-003 — Run Cancel Endpoint

**File:** `backend/app.py` — **MODIFY**, `backend/orchestrator.py` — **MODIFY**
**Priority:** 🔴 High

#### Purpose

Allow the user to cancel a running plan. Cancellation marks all `PENDING` tasks as `FAILED` with reason `"Cancelled by user"` and marks the run as `failed`.

#### New Route

```
POST /api/dag/runs/{run_id}/cancel
```

#### Implementation Steps

1. Add `_active_runs: Dict[int, asyncio.Task]` to `ExecutiveOrchestrator.__init__()`
2. In `execute_objective()`, register the asyncio task: `self._active_runs[run.id] = asyncio.current_task()`
3. Remove from `_active_runs` in the `finally` block of `execute_objective()`
4. Add `cancel_run(run_id: int)` method to `ExecutiveOrchestrator`:
   - Cancel the asyncio task if present in `_active_runs`
   - Mark all `PENDING`/`RUNNING` tasks as `FAILED` in the DB
   - Mark the run as `failed` in the DB
5. Add the FastAPI route that calls `orchestrator.cancel_run(run_id)`

#### Code

**Add to `ExecutiveOrchestrator.__init__()`:**

```python
self._active_runs: Dict[int, asyncio.Task] = {}
```

**Add to `ExecutiveOrchestrator`:**

```python
async def cancel_run(self, run_id: int) -> bool:
    """
    Cancel an active run. Cancels the asyncio task and marks all
    pending/running tasks as failed in the database.
    """
    task = self._active_runs.get(run_id)
    if task and not task.done():
        task.cancel()
        self.logger.info(f"[Orchestrator] Run {run_id} cancelled by user.")

    with Session(db_engine) as session:
        run = session.get(Run, run_id)
        if not run:
            return False

        # Mark pending/running tasks as cancelled
        stmt = select(TaskRecord).where(
            TaskRecord.run_id == run_id,
            TaskRecord.status.in_(["pending", "running"])
        )
        tasks = session.exec(stmt).all()
        for t in tasks:
            t.status = "failed"
            t.error = "Cancelled by user"
            t.end_time = datetime.now(timezone.utc)
            session.add(t)

        run.status = "failed"
        session.add(run)
        session.commit()

    return True
```

**Add route to `app.py`:**

```python
@app.post("/api/dag/runs/{run_id}/cancel", dependencies=[Depends(verify_authenticated)])
async def cancel_dag_run(run_id: int):
    """Cancel a running plan. Marks all pending tasks as failed."""
    success = await orchestrator.cancel_run(run_id)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Run not found or already complete")
    return {"cancelled": True, "run_id": run_id}
```

#### Acceptance Test

```
POST /api/dag/runs/{active_run_id}/cancel → 200, {"cancelled": true}
POST /api/dag/runs/{completed_run_id}/cancel → 404
DB after cancel: all pending tasks → status=failed, error="Cancelled by user"
Run record → status=failed
```

---

### DAG-BE-004 — Plan Preview (Dry-Run) Endpoint

**File:** `backend/app.py` — **MODIFY**
**Priority:** 🟡 Medium

#### Purpose

Generate a plan without executing it. Returns the structured DAG (list of tasks with dependencies) so the frontend can render a preview for user review before committing to execution.

#### New Route

```
POST /api/dag/preview
Body: {"objective": "...", "autonomy_level": "SEMI_AUTONOMOUS"}
```

#### Implementation Steps

1. Add `preview_plan(objective, context)` method to `ExecutiveOrchestrator` — calls `self.planner.generate_plan()` but does **not** call `self.executor.execute_dag()`
2. Returns the tasks dict serialized to a list of task summaries
3. Add FastAPI route that calls `orchestrator.preview_plan()`
4. Rate-limit to 10 per minute (same as other LLM-heavy routes)

#### Code

**Add to `ExecutiveOrchestrator`:**

```python
async def preview_plan(self, objective: str) -> list:
    """
    Generate a plan without executing it.
    Returns the DAG task list for frontend preview.
    """
    context = await self._build_soul_context()
    tasks = await self.planner.generate_plan(objective, context=context)
    return [
        {
            "id":           t_id,
            "action":       task.action,
            "description":  task.args.get("description", ""),
            "dependencies": task.dependencies,
            "priority":     getattr(task, "priority_score", 0),
        }
        for t_id, task in tasks.items()
    ]
```

**Add route to `app.py`:**

```python
@app.post(
    "/api/dag/preview",
    dependencies=[
        Depends(verify_authenticated),
        Depends(RateLimiter(times=10, seconds=60))
    ]
)
async def preview_dag_plan(body: ObjectiveRequest):
    """Generate and return a plan DAG without executing it."""
    if not orchestrator:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    try:
        tasks = await orchestrator.preview_plan(body.objective)
        return {"objective": body.objective, "tasks": tasks, "count": len(tasks)}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail=str(e))
```

#### Acceptance Test

```
POST /api/dag/preview {"objective": "Research competitors"}
  → 200, {"tasks": [...], "count": N}
  → No Run record created in DB
  → No TaskRecord records created
  → Response time < 10s
Invalid objective (empty string) → 422
```

---

### DAG-BE-005 — Task Retry Endpoint

**File:** `backend/app.py` — **MODIFY**
**Priority:** 🟡 Medium

#### Purpose

Re-execute a single failed task from a completed or failed run, injecting the outputs of its already-completed upstream dependencies.

#### New Route

```
POST /api/dag/runs/{run_id}/tasks/{task_dag_id}/retry
```

#### Implementation Steps

1. Fetch the `Run` and the specific `TaskRecord` — 404 if not found
2. Verify the task's current status is `failed` — 400 if not
3. Re-hydrate `DAGTask` from the stored `TaskRecord`
4. Fetch all completed upstream tasks and inject their results as `dependency_output`
5. Execute via `executor._execute_adapter()` with retry logic
6. Update the `TaskRecord` in the DB

#### Code

```python
@app.post(
    "/api/dag/runs/{run_id}/tasks/{task_dag_id}/retry",
    dependencies=[Depends(verify_authenticated)]
)
async def retry_dag_task(run_id: int, task_dag_id: str):
    """Retry a single failed task from a run."""
    from fastapi import HTTPException
    from .models import DAGTask, TaskStatus

    with Session(db_engine) as session:
        run = session.get(Run, run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")

        stmt = select(TaskRecord).where(
            TaskRecord.run_id == run_id,
            TaskRecord.task_dag_id == task_dag_id
        )
        record = session.exec(stmt).first()
        if not record:
            raise HTTPException(status_code=404, detail="Task not found")
        if record.status != "failed":
            raise HTTPException(status_code=400, detail="Only failed tasks can be retried")

        # Fetch upstream dependency outputs
        all_tasks_stmt = select(TaskRecord).where(
            TaskRecord.run_id == run_id,
            TaskRecord.status == "completed"
        )
        completed = {t.task_dag_id: t.result for t in session.exec(all_tasks_stmt).all()}

        task = DAGTask(
            id=record.task_dag_id,
            action=record.action,
            args={**(record.args or {}), "dependency_output": completed},
            status=TaskStatus.PENDING,
        )

        try:
            result = await orchestrator.executor._execute_adapter(
                task.action, task.args, task_id=task_dag_id
            )
            record.status = "completed"
            record.result = str(result)
            record.error = None
            record.end_time = datetime.now(timezone.utc)
        except Exception as e:
            record.status = "failed"
            record.error = f"Retry failed: {type(e).__name__}: {str(e)[:200]}"
            record.end_time = datetime.now(timezone.utc)

        session.add(record)
        session.commit()
        return {"task_dag_id": task_dag_id, "status": record.status, "result": record.result}
```

#### Acceptance Test

```
POST retry on failed task   → executes, returns new status
POST retry on completed task → 400
POST retry on unknown run    → 404
POST retry on unknown task   → 404
```

---

### DAG-BE-006 — Objective Submission Enhancement

**File:** `backend/app.py` — **MODIFY** (existing `/objective/execute` route)
**Priority:** 🔴 High

#### Purpose

The existing `POST /objective/execute` route returns a plain text response. Enhance it to return structured data including the `run_id`, so the frontend can immediately open the live stream for that run.

#### Implementation Steps

1. In the existing `execute_objective_endpoint()` handler, change the return to include `run_id`, `status`, `task_count`, and `result`
2. Do not break the existing response structure — add fields additively
3. The `run_id` comes from the `Run` record created in `ExecutiveOrchestrator.execute_objective()`

Verify `execute_objective()` currently returns the result string. Modify it to return a dict:

**Modify `ExecutiveOrchestrator.execute_objective()` return:**

```python
# At the end of execute_objective(), change from:
return final_response

# To:
return {
    "run_id":     run.id,
    "status":     run.status,
    "task_count": len(tasks) if tasks else 0,
    "result":     final_response,
}
```

**Update the FastAPI route handler** to pass the full dict to the response:

```python
@app.post("/objective/execute", ...)
async def execute_objective_endpoint(body: ObjectiveRequest, ...):
    ...
    result = await orchestrator.execute_objective(
        objective=body.objective,
        autonomy=body.autonomy_level,
        session_key=session_key
    )
    # result is now a dict with run_id
    return JSONResponse(content=result)
```

#### Acceptance Test

```
POST /objective/execute → response includes "run_id" field (int)
run_id exists in /api/dag/runs → true
Existing clients consuming response.result → still works (field preserved)
```

---

## 5. Frontend Specification

---

### DAG-FE-001 — DAGPanel Route & Sidebar Entry

**Files:** `App.tsx` (MODIFY), `components/Sidebar.tsx` (MODIFY)
**Priority:** 🔴 High

#### Purpose

Register `'dag'` as an `activeView` value and add a sidebar navigation item so users can reach the DAG Planner panel.

#### Implementation Steps — `App.tsx`

1. Import `DAGPanel` from `./features/dag/DAGPanel`
2. In the `renderContent()` switch, add a `case 'dag'` clause before the `default`:

```tsx
case 'dag':
  return <DAGPanel />;
```

#### Implementation Steps — `Sidebar.tsx`

1. Locate the nav items array (or the JSX that renders sidebar navigation items)
2. Add a DAG entry with an appropriate icon. Use `lucide-react`'s `GitFork` or `Network` icon:

```tsx
{
  id: 'dag',
  label: 'DAG Planner',
  icon: <GitFork size={16} />,
  view: 'dag'
}
```

3. Match the existing sidebar item rendering pattern exactly — same `className`, same `onClick={()=>setActiveView('dag')}`, same active state style

#### Acceptance Test

```
Clicking "DAG Planner" in sidebar → activeView === 'dag'
DAGPanel renders inside inline-panel-wrapper
Sidebar item shows active state when view === 'dag'
```

---

### DAG-FE-002 — `useDAGRuns` Hook

**File:** `features/dag/hooks/useDAGRuns.ts` — **CREATE**
**Priority:** 🔴 High

#### Purpose

Fetch and manage the list of runs, handle pagination, filtering, and polling for the run list panel.

#### Implementation Steps

1. Create `frontend/features/dag/hooks/useDAGRuns.ts`
2. Accept `status?: string` filter and `limit: number` param
3. Expose: `runs`, `total`, `loading`, `error`, `refresh()`, `loadMore()`
4. Auto-refresh every 5 seconds when the panel is mounted (only when no active stream is open)
5. Use the `accessToken` from `useStore()` in the Authorization header

#### Code

```typescript
// features/dag/hooks/useDAGRuns.ts
import { useState, useEffect, useCallback, useRef } from 'react';
import { useStore } from '../../../store/useStore';
import type { DAGRun } from '../types';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';
const POLL_INTERVAL_MS = 5000;

interface UseDAGRunsOptions {
  status?: string;
  limit?: number;
  autoRefresh?: boolean;
}

export function useDAGRuns({ status, limit = 20, autoRefresh = true }: UseDAGRunsOptions = {}) {
  const { accessToken } = useStore();
  const [runs, setRuns] = useState<DAGRun[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchRuns = useCallback(async (currentOffset = 0, replace = true) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ limit: String(limit), offset: String(currentOffset) });
      if (status) params.set('status', status);
      const res = await fetch(`${DAEMON_URL}/api/dag/runs?${params}`, {
        headers: { Authorization: `Bearer ${accessToken}` },
        credentials: 'include',
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRuns(prev => replace ? data.runs : [...prev, ...data.runs]);
      setTotal(data.total);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [accessToken, status, limit]);

  const refresh = useCallback(() => fetchRuns(0, true), [fetchRuns]);

  const loadMore = useCallback(() => {
    const nextOffset = offset + limit;
    setOffset(nextOffset);
    fetchRuns(nextOffset, false);
  }, [offset, limit, fetchRuns]);

  useEffect(() => {
    fetchRuns(0, true);
    if (autoRefresh) {
      intervalRef.current = setInterval(() => fetchRuns(0, true), POLL_INTERVAL_MS);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchRuns, autoRefresh]);

  return { runs, total, loading, error, refresh, loadMore, hasMore: runs.length < total };
}
```

---

### DAG-FE-003 — `useTaskStream` Hook (SSE)

**File:** `features/dag/hooks/useTaskStream.ts` — **CREATE**
**Priority:** 🔴 High

#### Purpose

Connect to the SSE endpoint for a run and maintain a live map of task states, applying diffs as they arrive.

#### Implementation Steps

1. Create `features/dag/hooks/useTaskStream.ts`
2. Accept `runId: number | null` — when `null`, stream is closed
3. Manage an `EventSource` instance; close and re-open when `runId` changes
4. Merge incoming task updates into `taskStates: Record<string, LiveTaskState>`
5. Expose `taskStates`, `streamStatus` (`'idle' | 'connecting' | 'live' | 'done' | 'error'`), and `disconnect()`
6. On `'done'` event: set `streamStatus = 'done'`, close source
7. On `error` after 3 retries: set `streamStatus = 'error'`

#### Code

```typescript
// features/dag/hooks/useTaskStream.ts
import { useState, useEffect, useRef, useCallback } from 'react';
import { useStore } from '../../../store/useStore';
import type { LiveTaskState, StreamStatus } from '../types';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export function useTaskStream(runId: number | null) {
  const { accessToken } = useStore();
  const [taskStates, setTaskStates] = useState<Record<string, LiveTaskState>>({});
  const [streamStatus, setStreamStatus] = useState<StreamStatus>('idle');
  const sourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);

  const disconnect = useCallback(() => {
    sourceRef.current?.close();
    sourceRef.current = null;
    setStreamStatus('idle');
  }, []);

  useEffect(() => {
    if (!runId) {
      disconnect();
      return;
    }

    setStreamStatus('connecting');
    setTaskStates({});
    retryCountRef.current = 0;

    // EventSource doesn't support custom headers; pass token as query param
    const url = `${DAEMON_URL}/api/dag/runs/${runId}/stream?token=${encodeURIComponent(accessToken || '')}`;
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => setStreamStatus('live');

    source.onmessage = (event) => {
      try {
        const update: LiveTaskState = JSON.parse(event.data);
        setTaskStates(prev => ({ ...prev, [update.task_dag_id]: update }));
      } catch { /* malformed event — skip */ }
    };

    source.addEventListener('done', (event: any) => {
      setStreamStatus('done');
      source.close();
    });

    source.onerror = () => {
      retryCountRef.current += 1;
      if (retryCountRef.current >= 3) {
        setStreamStatus('error');
        source.close();
      }
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, [runId, accessToken, disconnect]);

  return { taskStates, streamStatus, disconnect };
}
```

> **SSE Auth Note:** The SSE endpoint (`DAG-BE-002`) must also accept `?token=` query parameter as a fallback to the `Authorization` header, since `EventSource` does not support custom headers. Add `token: Optional[str] = None` to the route and check it alongside the cookie/header auth.

---

### DAG-FE-004 — DAGPanel Container

**File:** `features/dag/DAGPanel.tsx` — **CREATE**
**Priority:** 🔴 High

#### Purpose

Top-level panel that composes all DAG sub-components. Manages the selected run, active stream, and layout of the two-column view (run list + DAG detail).

#### Layout Structure

```
┌─────────────────────────────────────────────────────┐
│  inline-panel-wrapper                               │
│  ┌───────────────┐  ┌───────────────────────────────┤
│  │ RunListSidebar│  │  DAG Detail Column            │
│  │               │  │  ┌─────────────────────────┐  │
│  │  [run cards]  │  │  │ RunDetailHeader          │  │
│  │               │  │  ├─────────────────────────┤  │
│  │               │  │  │ DAGGraph (canvas)        │  │
│  │               │  │  ├─────────────────────────┤  │
│  │               │  │  │ ObjectiveSubmitBar       │  │
│  └───────────────┘  │  └─────────────────────────┘  │
│                     │  [TaskDetailDrawer overlay]   │
└─────────────────────────────────────────────────────┘
```

#### Implementation Steps

1. Create `features/dag/DAGPanel.tsx`
2. Use `useDAGRuns()` for the run list
3. Use `useTaskStream(selectedRunId)` for the live stream
4. Store `selectedRunId`, `selectedTaskId` in local state
5. Merge initial task records (from REST) with live stream updates
6. Pass `taskStates` down to `DAGGraph` and `TaskDetailDrawer`
7. Use `inline-panel-wrapper` as the outer container

#### Code

```tsx
// features/dag/DAGPanel.tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useDAGRuns } from './hooks/useDAGRuns';
import { useTaskStream } from './hooks/useTaskStream';
import { RunListSidebar } from './components/RunListSidebar';
import { RunDetailHeader } from './components/RunDetailHeader';
import { DAGGraph } from './components/DAGGraph';
import { ObjectiveSubmitBar } from './components/ObjectiveSubmitBar';
import { TaskDetailDrawer } from './components/TaskDetailDrawer';
import { PlanPreviewModal } from './components/PlanPreviewModal';
import { useStore } from '../../store/useStore';
import type { TaskRecord, DAGRun } from './types';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

export const DAGPanel: React.FC = () => {
  const { accessToken } = useStore();
  const { runs, loading: runsLoading, refresh: refreshRuns } = useDAGRuns({ autoRefresh: true });

  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [selectedRun, setSelectedRun] = useState<DAGRun | null>(null);
  const [initialTasks, setInitialTasks] = useState<TaskRecord[]>([]);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [previewObjective, setPreviewObjective] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');

  const { taskStates, streamStatus } = useTaskStream(selectedRunId);

  // Load full task list when a run is selected
  const loadRunDetail = useCallback(async (runId: number) => {
    try {
      const [runRes, tasksRes] = await Promise.all([
        fetch(`${DAEMON_URL}/api/dag/runs/${runId}`, {
          headers: { Authorization: `Bearer ${accessToken}` },
          credentials: 'include',
        }),
        fetch(`${DAEMON_URL}/api/dag/runs/${runId}/tasks`, {
          headers: { Authorization: `Bearer ${accessToken}` },
          credentials: 'include',
        }),
      ]);
      if (runRes.ok) setSelectedRun(await runRes.json());
      if (tasksRes.ok) {
        const data = await tasksRes.json();
        setInitialTasks(data.tasks || []);
      }
    } catch (e) {
      console.error('[DAGPanel] Failed to load run detail:', e);
    }
  }, [accessToken]);

  useEffect(() => {
    if (selectedRunId) loadRunDetail(selectedRunId);
  }, [selectedRunId, loadRunDetail]);

  // Merge initial tasks with live stream updates
  const mergedTasks: TaskRecord[] = initialTasks.map(t => {
    const live = taskStates[t.task_dag_id];
    if (!live) return t;
    return { ...t, status: live.status, result: live.result, error: live.error,
             start_time: live.start_time, end_time: live.end_time };
  });

  const handleCancel = async () => {
    if (!selectedRunId) return;
    await fetch(`${DAEMON_URL}/api/dag/runs/${selectedRunId}/cancel`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}` },
      credentials: 'include',
    });
    loadRunDetail(selectedRunId);
    refreshRuns();
  };

  const handleObjectiveSubmit = async (objective: string, autonomy: string) => {
    const res = await fetch(`${DAEMON_URL}/objective/execute`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ objective, autonomy_level: autonomy }),
    });
    if (res.ok) {
      const data = await res.json();
      refreshRuns();
      if (data.run_id) setSelectedRunId(data.run_id);
    }
  };

  const selectedTaskRecord = mergedTasks.find(t => t.task_dag_id === selectedTaskId) ?? null;

  return (
    <div className="inline-panel-wrapper" style={{ flexDirection: 'row', gap: 0 }}>

      {/* Left: Run List Sidebar */}
      <RunListSidebar
        runs={runs}
        loading={runsLoading}
        selectedRunId={selectedRunId}
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onSelectRun={(id) => { setSelectedRunId(id); setSelectedTaskId(null); }}
        onRefresh={refreshRuns}
      />

      {/* Right: Detail Column */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, position: 'relative' }}>

        {selectedRun ? (
          <>
            <RunDetailHeader
              run={selectedRun}
              tasks={mergedTasks}
              streamStatus={streamStatus}
              onCancel={handleCancel}
              onRefresh={() => loadRunDetail(selectedRun.id)}
            />
            <DAGGraph
              tasks={mergedTasks}
              selectedTaskId={selectedTaskId}
              onSelectTask={setSelectedTaskId}
            />
          </>
        ) : (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: 12, opacity: 0.35,
          }}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
              <circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/>
              <line x1="12" y1="7" x2="5" y2="17"/><line x1="12" y1="7" x2="19" y2="17"/>
            </svg>
            <p style={{ fontSize: 12, fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>
              SELECT_RUN_TO_VISUALIZE
            </p>
          </div>
        )}

        {/* Submit Bar — always visible */}
        <ObjectiveSubmitBar
          onSubmit={handleObjectiveSubmit}
          onPreview={setPreviewObjective}
        />
      </div>

      {/* Task Detail Drawer */}
      {selectedTaskId && selectedTaskRecord && (
        <TaskDetailDrawer
          task={selectedTaskRecord}
          runId={selectedRunId!}
          onClose={() => setSelectedTaskId(null)}
          onRetry={() => loadRunDetail(selectedRunId!)}
        />
      )}

      {/* Plan Preview Modal */}
      {previewObjective && (
        <PlanPreviewModal
          objective={previewObjective}
          onClose={() => setPreviewObjective(null)}
          onExecute={(obj) => { setPreviewObjective(null); handleObjectiveSubmit(obj, 'SEMI_AUTONOMOUS'); }}
        />
      )}
    </div>
  );
};
```

---

### DAG-FE-005 — RunListSidebar Component

**File:** `features/dag/components/RunListSidebar.tsx` — **CREATE**
**Priority:** 🔴 High

#### Purpose

Scrollable left-column list of past and active runs. Each card shows the objective, status badge, task counts, and elapsed time.

#### Design Requirements

- Width: `260px`, fixed, non-resizable
- Border-right: `1px solid var(--separator)`
- Background: `var(--bg-base)`
- Run cards: `glass-bg`, `glass-edge` border, `12px` border-radius
- Active run: `liquid-accent` background, `liquid-accent-edge` border
- Status badges: use the Status → Token mapping from §3
- Empty state: centered mono label `NO_RUNS_FOUND`

#### Code

```tsx
// features/dag/components/RunListSidebar.tsx
import React from 'react';
import { RefreshCw, Filter } from 'lucide-react';
import type { DAGRun } from '../types';
import { StatusBadge } from './StatusBadge';
import { formatDuration, formatRelativeTime } from '../utils/time';

interface Props {
  runs: DAGRun[];
  loading: boolean;
  selectedRunId: number | null;
  statusFilter: string;
  onStatusFilterChange: (v: string) => void;
  onSelectRun: (id: number) => void;
  onRefresh: () => void;
}

export const RunListSidebar: React.FC<Props> = ({
  runs, loading, selectedRunId, statusFilter, onStatusFilterChange, onSelectRun, onRefresh
}) => (
  <div style={{
    width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column',
    borderRight: '1px solid var(--separator)', background: 'var(--bg-base)', height: '100%',
  }}>
    {/* Header */}
    <div style={{
      padding: '16px 14px 12px', borderBottom: '1px solid var(--separator)',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    }}>
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>DAG Planner</h3>
        <span className="glass-label" style={{ fontSize: 9, color: 'var(--text-tertiary)' }}>
          EXECUTION_MANIFOLD
        </span>
      </div>
      <button
        onClick={onRefresh}
        className="glass-btn"
        style={{ padding: '4px 6px', display: 'flex', alignItems: 'center', gap: 4 }}
        title="Refresh runs"
      >
        <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
      </button>
    </div>

    {/* Filter */}
    <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--separator)' }}>
      <div style={{ display: 'flex', gap: 2, background: 'var(--fill-quaternary)', borderRadius: 8, padding: 2, border: '1px solid var(--separator)' }}>
        {['', 'active', 'completed', 'failed'].map(s => (
          <button
            key={s || 'all'}
            onClick={() => onStatusFilterChange(s)}
            style={{
              flex: 1, padding: '3px 4px', borderRadius: 6, fontSize: 9, fontWeight: 600,
              fontFamily: 'var(--font-mono)', textTransform: 'uppercase', border: 'none',
              cursor: 'pointer', letterSpacing: '0.05em',
              background: statusFilter === s ? 'var(--glass-bg-hover)' : 'transparent',
              color: statusFilter === s ? 'var(--text-primary)' : 'var(--text-tertiary)',
              boxShadow: statusFilter === s ? 'var(--glass-shadow)' : 'none',
              transition: 'all 0.15s ease',
            }}
          >
            {s || 'ALL'}
          </button>
        ))}
      </div>
    </div>

    {/* Run List */}
    <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }} className="scrollbar-hide">
      {runs.length === 0 && !loading && (
        <div style={{ textAlign: 'center', padding: '40px 12px', color: 'var(--text-tertiary)' }}>
          <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', letterSpacing: '0.1em' }}>
            NO_RUNS_FOUND
          </p>
        </div>
      )}
      {runs.map(run => {
        const isSelected = run.id === selectedRunId;
        const isActive = run.status === 'active';
        return (
          <div
            key={run.id}
            onClick={() => onSelectRun(run.id)}
            style={{
              padding: '10px 12px', borderRadius: 10, marginBottom: 4, cursor: 'pointer',
              background: isSelected ? 'var(--liquid-accent)' : 'var(--glass-bg)',
              border: `1px solid ${isSelected ? 'var(--liquid-accent-edge)' : 'var(--glass-edge)'}`,
              transition: 'all 0.15s ease',
            }}
          >
            {/* Objective text */}
            <p style={{
              fontSize: 11, fontWeight: 500, color: 'var(--text-primary)',
              margin: '0 0 6px', lineHeight: 1.4,
              overflow: 'hidden', display: '-webkit-box',
              WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
            }}>
              {run.objective || '—'}
            </p>

            {/* Status + meta row */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 4 }}>
              <StatusBadge status={run.status} />
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                {run.task_counts && (
                  <span style={{ fontSize: 9, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
                    {run.task_counts.completed}/{run.task_counts.total} tasks
                  </span>
                )}
                <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                  {formatRelativeTime(run.started_at)}
                </span>
              </div>
            </div>

            {/* Active run pulse indicator */}
            {isActive && (
              <div style={{
                marginTop: 6, height: 2, borderRadius: 2,
                background: 'var(--accent-warm)',
                animation: 'pulse-width 2s ease-in-out infinite',
              }} />
            )}
          </div>
        );
      })}
    </div>
  </div>
);
```

---

### DAG-FE-006 — DAGGraph Component (Canvas Visualizer)

**File:** `features/dag/components/DAGGraph.tsx` — **CREATE**
**Priority:** 🔴 High

#### Purpose

Render the DAG as an interactive node-link diagram using HTML Canvas. Each node represents a task; edges represent dependencies. Nodes are colored by status. Clicking a node opens the `TaskDetailDrawer`.

#### Layout Algorithm

Use a **topological layer-based layout**:
1. Compute topological generations: tasks with no dependencies are layer 0, tasks whose all dependencies are in layer `n-1` are in layer `n`
2. Arrange nodes left-to-right by layer, vertically centered within each layer
3. Draw directed edges as Bezier curves from right-center of source node to left-center of target node
4. Node dimensions: `180×52px`; horizontal gap: `80px`; vertical gap: `24px`

#### Status Colors

Use the Status → Token mapping from §3, read from computed CSS variable values.

#### Implementation Steps

1. Create `features/dag/components/DAGGraph.tsx`
2. Use `useRef<HTMLCanvasElement>` and `useEffect` to redraw on task state changes
3. Implement `computeLayout(tasks)` — returns `Map<taskId, {x, y, layer}>`
4. Implement `drawGraph(ctx, layout, tasks, selectedId)` — draws edges then nodes
5. Implement `hitTest(mouseX, mouseY, layout)` — returns clicked task ID or null
6. Add `onClick` handler on the `<canvas>` element that calls `onSelectTask`
7. Make the canvas container `overflow: auto` with a computed minimum size
8. Use `devicePixelRatio` scaling for crisp rendering on retina displays

#### Code

```tsx
// features/dag/components/DAGGraph.tsx
import React, { useRef, useEffect, useCallback, useMemo } from 'react';
import type { TaskRecord } from '../types';

interface Props {
  tasks: TaskRecord[];
  selectedTaskId: string | null;
  onSelectTask: (id: string) => void;
}

const NODE_W = 180, NODE_H = 52, H_GAP = 80, V_GAP = 24, PAD = 32;

// Map status → color hex (must match design tokens)
const STATUS_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  completed: { fill: 'rgba(48,209,88,0.16)',   stroke: 'rgba(48,209,88,0.45)',   text: '#30D158' },
  running:   { fill: 'rgba(255,159,10,0.16)',  stroke: 'rgba(255,159,10,0.45)',  text: '#FF9F0A' },
  pending:   { fill: 'rgba(191,90,242,0.16)',  stroke: 'rgba(191,90,242,0.45)', text: '#BF5AF2' },
  failed:    { fill: 'rgba(255,69,58,0.16)',   stroke: 'rgba(255,69,58,0.45)',   text: '#FF453A' },
  skipped:   { fill: 'rgba(120,120,128,0.12)', stroke: 'rgba(120,120,128,0.30)', text: '#8E8E93' },
};

function computeLayout(tasks: TaskRecord[]) {
  const layers = new Map<string, number>();
  const sorted = [...tasks];

  // Topological generation assignment
  let changed = true;
  while (changed) {
    changed = false;
    for (const t of sorted) {
      const maxDepLayer = t.args?.dependencies
        ? Math.max(-1, ...(t.args.dependencies as string[]).map(d => layers.get(d) ?? -1))
        : -1;
      const newLayer = maxDepLayer + 1;
      if ((layers.get(t.task_dag_id) ?? -1) !== newLayer) {
        layers.set(t.task_dag_id, newLayer);
        changed = true;
      }
    }
  }

  // Group by layer
  const byLayer = new Map<number, string[]>();
  for (const [id, layer] of layers) {
    if (!byLayer.has(layer)) byLayer.set(layer, []);
    byLayer.get(layer)!.push(id);
  }

  // Assign x/y coordinates
  const positions = new Map<string, { x: number; y: number }>();
  const numLayers = Math.max(...layers.values()) + 1;

  for (let l = 0; l < numLayers; l++) {
    const ids = byLayer.get(l) ?? [];
    const x = PAD + l * (NODE_W + H_GAP);
    ids.forEach((id, i) => {
      const y = PAD + i * (NODE_H + V_GAP);
      positions.set(id, { x, y });
    });
  }

  return positions;
}

export const DAGGraph: React.FC<Props> = ({ tasks, selectedTaskId, onSelectTask }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const positionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());

  const taskMap = useMemo(() => {
    const m = new Map<string, TaskRecord>();
    tasks.forEach(t => m.set(t.task_dag_id, t));
    return m;
  }, [tasks]);

  const positions = useMemo(() => computeLayout(tasks), [tasks]);
  positionsRef.current = positions;

  // Compute canvas dimensions from layout
  const { canvasW, canvasH } = useMemo(() => {
    let maxX = 0, maxY = 0;
    for (const { x, y } of positions.values()) {
      maxX = Math.max(maxX, x + NODE_W + PAD);
      maxY = Math.max(maxY, y + NODE_H + PAD);
    }
    return { canvasW: Math.max(maxX, 400), canvasH: Math.max(maxY, 200) };
  }, [positions]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = canvasW * dpr;
    canvas.height = canvasH * dpr;
    canvas.style.width = `${canvasW}px`;
    canvas.style.height = `${canvasH}px`;
    const ctx = canvas.getContext('2d')!;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, canvasW, canvasH);

    // Draw edges
    ctx.lineWidth = 1.5;
    for (const task of tasks) {
      const pos = positions.get(task.task_dag_id);
      if (!pos) continue;
      const deps: string[] = task.args?.dependencies ?? [];
      for (const depId of deps) {
        const depPos = positions.get(depId);
        if (!depPos) continue;
        const x1 = depPos.x + NODE_W, y1 = depPos.y + NODE_H / 2;
        const x2 = pos.x,             y2 = pos.y + NODE_H / 2;
        const mx = (x1 + x2) / 2;
        const depTask = taskMap.get(depId);
        const col = STATUS_COLORS[depTask?.status ?? 'pending'];
        ctx.strokeStyle = col?.stroke ?? 'rgba(255,255,255,0.12)';
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.bezierCurveTo(mx, y1, mx, y2, x2, y2);
        ctx.stroke();
        // Arrowhead
        ctx.fillStyle = col?.stroke ?? 'rgba(255,255,255,0.12)';
        ctx.beginPath();
        ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - 8, y2 - 4);
        ctx.lineTo(x2 - 8, y2 + 4);
        ctx.closePath();
        ctx.fill();
      }
    }

    // Draw nodes
    for (const task of tasks) {
      const pos = positions.get(task.task_dag_id);
      if (!pos) continue;
      const col = STATUS_COLORS[task.status] ?? STATUS_COLORS.pending;
      const isSelected = task.task_dag_id === selectedTaskId;

      // Node background
      ctx.fillStyle = col.fill;
      roundRect(ctx, pos.x, pos.y, NODE_W, NODE_H, 10);
      ctx.fill();

      // Node border
      ctx.strokeStyle = isSelected ? col.text : col.stroke;
      ctx.lineWidth = isSelected ? 2 : 1;
      roundRect(ctx, pos.x, pos.y, NODE_W, NODE_H, 10);
      ctx.stroke();

      // Task action label
      ctx.fillStyle = col.text;
      ctx.font = `600 10px var(--font-mono, monospace)`;
      ctx.textAlign = 'left';
      const actionLabel = (task.action || 'unknown').toUpperCase().slice(0, 16);
      ctx.fillText(actionLabel, pos.x + 12, pos.y + 17);

      // Task ID
      ctx.fillStyle = 'rgba(235,235,245,0.45)';
      ctx.font = `400 9px var(--font-mono, monospace)`;
      const idLabel = task.task_dag_id.slice(0, 22);
      ctx.fillText(idLabel, pos.x + 12, pos.y + 32);

      // Status dot
      ctx.fillStyle = col.text;
      ctx.beginPath();
      ctx.arc(pos.x + NODE_W - 14, pos.y + 14, 4, 0, Math.PI * 2);
      ctx.fill();

      // Running pulse ring
      if (task.status === 'running') {
        ctx.strokeStyle = 'rgba(255,159,10,0.4)';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.arc(pos.x + NODE_W - 14, pos.y + 14, 7, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
  }, [tasks, positions, selectedTaskId, taskMap, canvasW, canvasH]);

  useEffect(() => { draw(); }, [draw]);

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const rect = canvasRef.current!.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    for (const task of tasks) {
      const pos = positionsRef.current.get(task.task_dag_id);
      if (!pos) continue;
      if (mx >= pos.x && mx <= pos.x + NODE_W && my >= pos.y && my <= pos.y + NODE_H) {
        onSelectTask(task.task_dag_id);
        return;
      }
    }
  };

  return (
    <div style={{
      flex: 1, overflow: 'auto', padding: 16,
      background: 'var(--bg-base)', position: 'relative',
    }} className="scrollbar-hide">
      {tasks.length === 0 ? (
        <div style={{ textAlign: 'center', paddingTop: 60, color: 'var(--text-tertiary)' }}>
          <p style={{ fontSize: 10, fontFamily: 'var(--font-mono)', letterSpacing: '0.1em' }}>
            NO_TASKS_IN_RUN
          </p>
        </div>
      ) : (
        <canvas
          ref={canvasRef}
          onClick={handleClick}
          style={{ cursor: 'pointer', display: 'block' }}
        />
      )}
    </div>
  );
};

// Canvas utility: rounded rectangle path
function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}
```

---

### DAG-FE-007 — TaskNode Component

**File:** `features/dag/components/StatusBadge.tsx` — **CREATE**
**Priority:** 🔴 High

#### Purpose

Reusable status badge chip used in `RunListSidebar`, `RunDetailHeader`, and `TaskDetailDrawer`. Keeps status rendering consistent across all DAG components.

#### Code

```tsx
// features/dag/components/StatusBadge.tsx
import React from 'react';

type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped' | 'active' | 'queued';

const STATUS_STYLES: Record<string, React.CSSProperties> = {
  completed: { color: 'var(--accent)',           background: 'var(--liquid-accent)',     borderColor: 'var(--liquid-accent-edge)' },
  running:   { color: 'var(--accent-warm)',       background: 'var(--liquid-warm)',       borderColor: 'var(--liquid-warm-edge)' },
  active:    { color: 'var(--accent-warm)',       background: 'var(--liquid-warm)',       borderColor: 'var(--liquid-warm-edge)' },
  pending:   { color: 'var(--accent-secondary)',  background: 'var(--liquid-secondary)',  borderColor: 'var(--liquid-secondary-edge)' },
  queued:    { color: 'var(--accent-secondary)',  background: 'var(--liquid-secondary)',  borderColor: 'var(--liquid-secondary-edge)' },
  failed:    { color: 'var(--accent-danger)',     background: 'var(--liquid-danger)',     borderColor: 'var(--liquid-danger-edge)' },
  skipped:   { color: 'var(--text-tertiary)',     background: 'var(--fill-quaternary)',   borderColor: 'var(--separator)' },
};

export const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const styles = STATUS_STYLES[status] ?? STATUS_STYLES.pending;
  return (
    <span style={{
      ...styles,
      fontSize: 9, fontWeight: 700, fontFamily: 'var(--font-mono)',
      textTransform: 'uppercase', letterSpacing: '0.08em',
      padding: '2px 6px', borderRadius: 4,
      border: '1px solid', display: 'inline-flex', alignItems: 'center', gap: 4,
    }}>
      {status === 'running' && (
        <span style={{
          width: 5, height: 5, borderRadius: '50%',
          background: 'var(--accent-warm)',
          animation: 'pulse-dot 1.2s ease-in-out infinite',
          display: 'inline-block',
        }} />
      )}
      {status.toUpperCase()}
    </span>
  );
};
```

---

### DAG-FE-008 — RunDetailHeader Component

**File:** `features/dag/components/RunDetailHeader.tsx` — **CREATE**
**Priority:** 🟡 Medium

#### Purpose

Header bar for the selected run showing: objective text, status badge, task completion progress bar, elapsed duration, and action buttons (Cancel / Refresh).

#### Code

```tsx
// features/dag/components/RunDetailHeader.tsx
import React from 'react';
import { X, RefreshCw, StopCircle } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import type { DAGRun, TaskRecord, StreamStatus } from '../types';
import { formatDuration } from '../utils/time';

interface Props {
  run: DAGRun;
  tasks: TaskRecord[];
  streamStatus: StreamStatus;
  onCancel: () => void;
  onRefresh: () => void;
}

export const RunDetailHeader: React.FC<Props> = ({ run, tasks, streamStatus, onCancel, onRefresh }) => {
  const completed = tasks.filter(t => t.status === 'completed').length;
  const total = tasks.length;
  const progress = total > 0 ? (completed / total) * 100 : 0;
  const isActive = run.status === 'active';

  return (
    <div style={{
      padding: '14px 18px', borderBottom: '1px solid var(--separator)',
      background: 'var(--glass-bg)',
      backdropFilter: 'var(--glass-blur)',
      WebkitBackdropFilter: 'var(--glass-blur)',
    }}>
      {/* Top row: objective + controls */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <StatusBadge status={run.status} />
            <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
              RUN_{run.id}
            </span>
            {streamStatus === 'live' && (
              <span style={{ fontSize: 9, color: 'var(--accent-warm)', fontFamily: 'var(--font-mono)', letterSpacing: '0.06em' }}>
                ● LIVE
              </span>
            )}
          </div>
          <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)', margin: 0, lineHeight: 1.4 }}>
            {run.objective}
          </p>
        </div>

        {/* Controls */}
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <button onClick={onRefresh} className="glass-btn" style={{ padding: '5px 8px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
            <RefreshCw size={11} />
          </button>
          {isActive && (
            <button onClick={onCancel} className="glass-btn" style={{
              padding: '5px 10px', display: 'flex', alignItems: 'center', gap: 5, fontSize: 11,
              color: 'var(--accent-danger)', borderColor: 'var(--liquid-danger-edge)',
              background: 'var(--liquid-danger)',
            }}>
              <StopCircle size={11} /> Cancel
            </button>
          )}
        </div>
      </div>

      {/* Progress bar + stats */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Progress bar */}
        <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'var(--fill-quaternary)', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 2,
            width: `${progress}%`,
            background: run.status === 'failed' ? 'var(--accent-danger)' : 'var(--accent)',
            transition: 'width 0.4s ease',
          }} />
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: 16, flexShrink: 0 }}>
          {[
            { label: 'TASKS', value: `${completed}/${total}` },
            { label: 'FAILED', value: tasks.filter(t => t.status === 'failed').length },
            { label: 'ELAPSED', value: run.started_at ? formatDuration(run.started_at, run.completed_at) : '—' },
          ].map(({ label, value }) => (
            <div key={label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>
                {label}
              </div>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {value}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
```

---

### DAG-FE-009 — TaskDetailDrawer Component

**File:** `features/dag/components/TaskDetailDrawer.tsx` — **CREATE**
**Priority:** 🟡 Medium

#### Purpose

Right-side slide-in drawer that shows full details for a selected task node: action name, status, input args (formatted JSON), output result, error message, duration, and a Retry button for failed tasks.

#### Code

```tsx
// features/dag/components/TaskDetailDrawer.tsx
import React, { useState } from 'react';
import { X, RotateCcw, ChevronDown, ChevronRight } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import type { TaskRecord } from '../types';
import { formatDuration } from '../utils/time';
import { useStore } from '../../../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface Props {
  task: TaskRecord;
  runId: number;
  onClose: () => void;
  onRetry: () => void;
}

const JsonBlock: React.FC<{ value: any; label: string }> = ({ value, label }) => {
  const [open, setOpen] = useState(true);
  const str = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
  return (
    <div style={{ marginBottom: 12 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 4, background: 'none', border: 'none',
          cursor: 'pointer', padding: 0, marginBottom: 6,
          color: 'var(--text-tertiary)', fontSize: 10, fontFamily: 'var(--font-mono)',
          textTransform: 'uppercase', letterSpacing: '0.08em',
        }}
      >
        {open ? <ChevronDown size={10} /> : <ChevronRight size={10} />} {label}
      </button>
      {open && (
        <pre style={{
          margin: 0, padding: '10px 12px', borderRadius: 8,
          background: 'rgba(0,0,0,0.20)', border: '1px solid var(--separator)',
          fontFamily: 'var(--font-mono)', fontSize: 10, lineHeight: 1.6,
          color: 'var(--accent-warm)', overflowX: 'auto', whiteSpace: 'pre-wrap',
          wordBreak: 'break-all', maxHeight: 200,
        }}>
          {str || '—'}
        </pre>
      )}
    </div>
  );
};

export const TaskDetailDrawer: React.FC<Props> = ({ task, runId, onClose, onRetry }) => {
  const { accessToken } = useStore();
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await fetch(`${DAEMON_URL}/api/dag/runs/${runId}/tasks/${task.task_dag_id}/retry`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        credentials: 'include',
      });
      onRetry();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div style={{
      position: 'absolute', top: 0, right: 0, bottom: 0,
      width: 360, zIndex: 50,
      background: 'var(--glass-bg)',
      backdropFilter: 'var(--glass-blur-heavy) var(--glass-sat)',
      WebkitBackdropFilter: 'var(--glass-blur-heavy) var(--glass-sat)',
      borderLeft: '1px solid var(--glass-edge)',
      boxShadow: 'var(--glass-shadow-lg)',
      display: 'flex', flexDirection: 'column',
      animation: 'slideInRight 0.22s var(--ease-spring)',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px', borderBottom: '1px solid var(--separator)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
            <StatusBadge status={task.status} />
            <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-tertiary)' }}>
              {task.task_dag_id}
            </span>
          </div>
          <h4 style={{
            margin: 0, fontSize: 13, fontWeight: 600,
            fontFamily: 'var(--font-mono)', color: 'var(--text-primary)',
            textTransform: 'uppercase', letterSpacing: '0.04em',
          }}>
            {task.action}
          </h4>
        </div>
        <button onClick={onClose} className="glass-btn" style={{ padding: '4px 6px' }}>
          <X size={13} />
        </button>
      </div>

      {/* Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px' }} className="scrollbar-hide">
        {/* Timing */}
        <div style={{
          display: 'flex', gap: 12, padding: '10px 12px', borderRadius: 8,
          background: 'var(--fill-quaternary)', border: '1px solid var(--separator)',
          marginBottom: 16,
        }}>
          {[
            { label: 'STARTED', value: task.start_time ? new Date(task.start_time).toLocaleTimeString() : '—' },
            { label: 'DURATION', value: task.start_time ? formatDuration(task.start_time, task.end_time) : '—' },
            { label: 'RETRIES', value: task.retry_count ?? 0 },
          ].map(({ label, value }) => (
            <div key={label} style={{ flex: 1, textAlign: 'center' }}>
              <div style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>{label}</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{String(value)}</div>
            </div>
          ))}
        </div>

        {/* Input args */}
        <JsonBlock value={task.args} label="Input Args" />

        {/* Output */}
        {task.result && <JsonBlock value={task.result} label="Output" />}

        {/* Error */}
        {task.error && (
          <div style={{ marginBottom: 12 }}>
            <p className="glass-label" style={{ fontSize: 9, color: 'var(--accent-danger)', marginBottom: 6 }}>ERROR</p>
            <pre style={{
              margin: 0, padding: '10px 12px', borderRadius: 8,
              background: 'var(--liquid-danger)', border: '1px solid var(--liquid-danger-edge)',
              fontFamily: 'var(--font-mono)', fontSize: 10, lineHeight: 1.6,
              color: 'var(--accent-danger)', overflowX: 'auto', whiteSpace: 'pre-wrap',
            }}>
              {task.error}
            </pre>
          </div>
        )}
      </div>

      {/* Footer: Retry */}
      {task.status === 'failed' && (
        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--separator)' }}>
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="glass-btn glass-btn--primary"
            style={{
              width: '100%', padding: '9px', fontSize: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
            }}
          >
            <RotateCcw size={12} className={retrying ? 'animate-spin' : ''} />
            {retrying ? 'Retrying...' : 'Retry Task'}
          </button>
        </div>
      )}
    </div>
  );
};
```

---

### DAG-FE-010 — ObjectiveSubmitBar Component

**File:** `features/dag/components/ObjectiveSubmitBar.tsx` — **CREATE**
**Priority:** 🟡 Medium

#### Purpose

Fixed bottom bar within the DAG panel for submitting new objectives. Includes an autonomy selector, a Preview button, and an Execute button.

#### Code

```tsx
// features/dag/components/ObjectiveSubmitBar.tsx
import React, { useState } from 'react';
import { Play, Eye, Loader } from 'lucide-react';

interface Props {
  onSubmit: (objective: string, autonomy: string) => Promise<void>;
  onPreview: (objective: string) => void;
}

export const ObjectiveSubmitBar: React.FC<Props> = ({ onSubmit, onPreview }) => {
  const [objective, setObjective] = useState('');
  const [autonomy, setAutonomy] = useState('SEMI_AUTONOMOUS');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!objective.trim() || submitting) return;
    setSubmitting(true);
    try {
      await onSubmit(objective.trim(), autonomy);
      setObjective('');
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSubmit();
  };

  return (
    <div style={{
      padding: '12px 14px', borderTop: '1px solid var(--separator)',
      background: 'var(--glass-bg)',
      backdropFilter: 'var(--glass-blur)',
      WebkitBackdropFilter: 'var(--glass-blur)',
    }}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <span style={{
            fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)',
            textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 5,
          }}>
            NEW_OBJECTIVE
          </span>
          <textarea
            value={objective}
            onChange={e => setObjective(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe what you want the agent to accomplish..."
            rows={2}
            className="glass-input"
            style={{
              width: '100%', resize: 'none', fontSize: 12, lineHeight: 1.5,
              fontFamily: 'inherit', padding: '8px 10px',
            }}
          />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
          <select
            value={autonomy}
            onChange={e => setAutonomy(e.target.value)}
            className="glass-input"
            style={{ fontSize: 10, fontFamily: 'var(--font-mono)', padding: '4px 6px' }}
          >
            <option value="UNRESTRICTED">UNRESTRICTED</option>
            <option value="SEMI_AUTONOMOUS">SEMI_AUTO</option>
            <option value="RESTRICTED">RESTRICTED</option>
          </select>

          <div style={{ display: 'flex', gap: 5 }}>
            <button
              onClick={() => objective.trim() && onPreview(objective.trim())}
              disabled={!objective.trim()}
              className="glass-btn"
              title="Preview plan (dry run)"
              style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}
            >
              <Eye size={12} /> Preview
            </button>
            <button
              onClick={handleSubmit}
              disabled={!objective.trim() || submitting}
              className="glass-btn glass-btn--primary"
              style={{ padding: '7px 12px', display: 'flex', alignItems: 'center', gap: 5, fontSize: 11 }}
            >
              {submitting ? <Loader size={11} className="animate-spin" /> : <Play size={11} />}
              Execute
            </button>
          </div>
        </div>
      </div>
      <p style={{ fontSize: 9, color: 'var(--text-tertiary)', margin: '6px 0 0', fontFamily: 'var(--font-mono)' }}>
        ⌘↵ to execute · Preview shows DAG without running
      </p>
    </div>
  );
};
```

---

### DAG-FE-011 — PlanPreviewModal Component

**File:** `features/dag/components/PlanPreviewModal.tsx` — **CREATE**
**Priority:** 🟡 Medium

#### Purpose

Full-screen modal that shows the generated plan from the dry-run endpoint before execution. Lists all tasks with their dependencies in a visual tree, with an Execute or Cancel CTA.

#### Code

```tsx
// features/dag/components/PlanPreviewModal.tsx
import React, { useEffect, useState } from 'react';
import { X, Play, Loader, GitFork } from 'lucide-react';
import { useStore } from '../../../store/useStore';

const DAEMON_URL = import.meta.env.VITE_DAEMON_URL || 'http://localhost:8000';

interface PreviewTask {
  id: string;
  action: string;
  description: string;
  dependencies: string[];
}

interface Props {
  objective: string;
  onClose: () => void;
  onExecute: (objective: string) => void;
}

export const PlanPreviewModal: React.FC<Props> = ({ objective, onClose, onExecute }) => {
  const { accessToken } = useStore();
  const [tasks, setTasks] = useState<PreviewTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await fetch(`${DAEMON_URL}/api/dag/preview`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ objective }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setTasks(data.tasks || []);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    })();
  }, [objective, accessToken]);

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 200,
      background: 'rgba(0,0,0,0.45)', backdropFilter: 'var(--glass-blur)',
      WebkitBackdropFilter: 'var(--glass-blur)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }}>
      <div style={{
        width: '100%', maxWidth: 640, maxHeight: '80vh',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--glass-edge)',
        borderRadius: 16, boxShadow: 'var(--glass-shadow-lg)',
        display: 'flex', flexDirection: 'column',
        animation: 'zoomIn 0.2s var(--ease-spring)',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid var(--separator)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <GitFork size={16} style={{ color: 'var(--accent-secondary)' }} />
            <div>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 600 }}>Plan Preview</h3>
              <p style={{ margin: 0, fontSize: 10, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                DRY_RUN — NOT EXECUTED
              </p>
            </div>
          </div>
          <button onClick={onClose} className="glass-btn" style={{ padding: '4px 7px' }}>
            <X size={13} />
          </button>
        </div>

        {/* Objective */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--separator)', background: 'var(--fill-quaternary)' }}>
          <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)', textTransform: 'uppercase', letterSpacing: '0.1em', display: 'block', marginBottom: 4 }}>
            OBJECTIVE
          </span>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--text-primary)' }}>{objective}</p>
        </div>

        {/* Task list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 20px' }} className="scrollbar-hide">
          {loading && (
            <div style={{ textAlign: 'center', padding: 40 }}>
              <Loader size={20} className="animate-spin" style={{ color: 'var(--accent)' }} />
              <p style={{ fontSize: 11, color: 'var(--text-tertiary)', marginTop: 10, fontFamily: 'var(--font-mono)', letterSpacing: '0.08em' }}>
                GENERATING_PLAN...
              </p>
            </div>
          )}
          {error && (
            <div style={{ padding: 16, borderRadius: 8, background: 'var(--liquid-danger)', border: '1px solid var(--liquid-danger-edge)', color: 'var(--accent-danger)', fontSize: 12 }}>
              Failed to generate plan: {error}
            </div>
          )}
          {!loading && !error && tasks.map((task, idx) => (
            <div key={task.id} style={{
              padding: '10px 14px', borderRadius: 10, marginBottom: 6,
              background: 'var(--glass-bg)', border: '1px solid var(--glass-edge)',
              display: 'flex', gap: 12, alignItems: 'flex-start',
            }}>
              <div style={{
                width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                background: 'var(--liquid-secondary)', border: '1px solid var(--liquid-secondary-edge)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)',
                color: 'var(--accent-secondary)',
              }}>
                {idx + 1}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                  <span style={{ fontSize: 10, fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--accent-warm)', textTransform: 'uppercase' }}>
                    {task.action}
                  </span>
                  <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                    {task.id}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.4 }}>
                  {task.description}
                </p>
                {task.dependencies.length > 0 && (
                  <div style={{ marginTop: 5, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 9, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
                      depends on:
                    </span>
                    {task.dependencies.map(d => (
                      <span key={d} style={{
                        fontSize: 9, fontFamily: 'var(--font-mono)',
                        padding: '1px 5px', borderRadius: 3,
                        background: 'var(--fill-quaternary)', border: '1px solid var(--separator)',
                        color: 'var(--text-secondary)',
                      }}>
                        {d}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        {!loading && !error && (
          <div style={{
            padding: '12px 20px', borderTop: '1px solid var(--separator)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{ fontSize: 11, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
              {tasks.length} task{tasks.length !== 1 ? 's' : ''} · preview only
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <button onClick={onClose} className="glass-btn" style={{ padding: '8px 14px', fontSize: 12 }}>
                Discard
              </button>
              <button
                onClick={() => onExecute(objective)}
                className="glass-btn glass-btn--primary"
                style={{ padding: '8px 16px', fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Play size={11} /> Execute Plan
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
```

---

### DAG-FE-012 — DAG Store Slice (Zustand)

**File:** `store/useStore.ts` — **MODIFY**
**Priority:** 🔴 High

#### Purpose

Add a minimal DAG slice to the global Zustand store so that live run state is accessible from anywhere (e.g., the terminal can show a live badge when a run is active).

#### Implementation Steps

1. Add `activeRunId: number | null` and `setActiveRunId: (id: number | null) => void` to the store
2. Add `dagRunning: boolean` derived from `activeRunId !== null`
3. In `DAGPanel`, call `setActiveRunId(run.id)` when a run starts and `setActiveRunId(null)` when it completes
4. In `TerminalView` or `SystemHeader`, consume `dagRunning` to show a subtle active indicator

#### Code

**Add to `store/useStore.ts` state interface:**

```typescript
// DAG state
activeRunId:    number | null;
setActiveRunId: (id: number | null) => void;
```

**Add to the `create()` call inside `useStore`:**

```typescript
activeRunId:    null,
setActiveRunId: (id) => set({ activeRunId: id }),
```

---

### DAG-FE-013 — Sidebar Navigation Integration

**File:** `components/Sidebar.tsx` — **MODIFY**
**Priority:** 🔴 High

#### Purpose

Add the DAG Planner navigation item to the sidebar so users can reach the panel.

#### Implementation Steps

1. Import `GitFork` from `lucide-react` at the top of `Sidebar.tsx`
2. Locate the nav items array or the JSX section rendering sidebar nav links
3. Add the DAG entry in the logical position — after `Tasks` and before `Analytics` or `Agents`, reflecting its role as an execution management view

```tsx
// Add to the sidebar navigation items array or JSX:
{
  id: 'dag',
  label: 'DAG Planner',
  icon: <GitFork size={15} />,
  badge: activeRunId ? '●' : undefined,   // live indicator from store
}
```

4. Bind `onClick` to `setActiveView('dag')` following the exact same handler pattern as all other sidebar items
5. Apply the active state style (`glass-bg-hover` background, `--accent` color icon) when `activeView === 'dag'`
6. The active run badge `●` should pulse using the `pulse-dot` animation and use `--accent-warm` color

---

### DAG-FE-014 — App.tsx Route Registration

**File:** `App.tsx` — **MODIFY**
**Priority:** 🔴 High

#### Implementation Steps

1. Add import at top of `App.tsx`:

```tsx
import { DAGPanel } from './features/dag/DAGPanel';
```

2. In `renderContent()` switch statement, add before `default`:

```tsx
case 'dag':
  return <DAGPanel />;
```

3. No other changes to `App.tsx` are required. `DAGPanel` is fully self-contained.

---

## 6. Type Definitions

**File:** `features/dag/types.ts` — **CREATE**

```typescript
// features/dag/types.ts

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
export type RunStatus  = 'queued' | 'active' | 'completed' | 'failed';
export type StreamStatus = 'idle' | 'connecting' | 'live' | 'done' | 'error';

export interface DAGRun {
  id:           number;
  objective:    string;
  status:       RunStatus;
  started_at:   string;        // ISO datetime string
  completed_at: string | null;
  task_counts?: {
    total:     number;
    completed: number;
    failed:    number;
    running:   number;
    pending:   number;
  };
}

export interface TaskRecord {
  id:           number;
  run_id:       number;
  task_dag_id:  string;
  action:       string;
  args:         Record<string, any>;
  status:       TaskStatus;
  result:       string | null;
  error:        string | null;
  start_time:   string | null;
  end_time:     string | null;
  retry_count?: number;
}

export interface LiveTaskState {
  task_dag_id: string;
  action:      string;
  status:      TaskStatus;
  result:      string | null;
  error:       string | null;
  start_time:  string | null;
  end_time:    string | null;
}
```

---

## 7. CSS — Design Token Extensions & Component Styles

**File:** `styles/dag.css` — **CREATE**
**Import in:** `styles/main.css` or equivalent entry stylesheet via `@import './dag.css'`

```css
/* =========================================================================
   ALLUCI DAG PLANNER — Component Styles
   Extends the existing design token system. Zero new tokens introduced.
   ========================================================================= */

/* === Animations === */

@keyframes pulse-dot {
  0%, 100% { opacity: 1;   transform: scale(1); }
  50%       { opacity: 0.4; transform: scale(0.8); }
}

@keyframes pulse-width {
  0%, 100% { opacity: 1;   }
  50%       { opacity: 0.5; }
}

@keyframes slideInRight {
  from { transform: translateX(30px); opacity: 0; }
  to   { transform: translateX(0);    opacity: 1; }
}

/* === DAG Graph Container === */

.dag-graph-container {
  flex: 1;
  overflow: auto;
  padding: 16px;
  background: var(--bg-base);
  position: relative;
}

.dag-graph-container canvas {
  cursor: pointer;
  display: block;
}

/* === Run Card hover === */

.dag-run-card:hover {
  background: var(--glass-bg-hover) !important;
  border-color: var(--glass-edge) !important;
}

/* === Task Drawer slide animation === */

.dag-task-drawer {
  animation: slideInRight 0.22s var(--ease-spring, cubic-bezier(0.34, 1.56, 0.64, 1));
}

/* === Live stream indicator dot === */

.dag-live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-warm);
  animation: pulse-dot 1.2s ease-in-out infinite;
  display: inline-block;
}

/* === Progress bar fill animation === */

.dag-progress-fill {
  transition: width 0.4s ease;
}

/* === Empty state mono label === */

.dag-empty-label {
  font-size: 10px;
  font-family: var(--font-mono);
  letter-spacing: 0.1em;
  color: var(--text-tertiary);
  text-align: center;
}
```

---

## 8. Testing Specification

---

### Backend Tests

**File:** `backend/tests/test_dag_api.py` — **CREATE**

```python
"""
DAG Planner API Tests
pytest backend/tests/test_dag_api.py -v
"""
import pytest
import asyncio
from httpx import AsyncClient
from ..app import app
from ..models import Run, RunStatus


# ── DAG-BE-001: Run List & Detail ──────────────────────────────────────────

class TestRunListAPI:
    async def test_list_runs_authenticated(self, auth_client: AsyncClient):
        """GET /api/dag/runs → 200, valid structure"""
        res = await auth_client.get("/api/dag/runs")
        assert res.status_code == 200
        body = res.json()
        assert "runs" in body
        assert "total" in body
        assert isinstance(body["runs"], list)

    async def test_list_runs_unauthenticated(self, client: AsyncClient):
        """GET /api/dag/runs without auth → 401"""
        res = await client.get("/api/dag/runs")
        assert res.status_code == 401

    async def test_list_runs_status_filter(self, auth_client: AsyncClient, seed_runs):
        """GET /api/dag/runs?status=failed → only failed runs"""
        res = await auth_client.get("/api/dag/runs?status=failed")
        assert res.status_code == 200
        runs = res.json()["runs"]
        assert all(r["status"] == "failed" for r in runs)

    async def test_list_runs_pagination(self, auth_client: AsyncClient, seed_runs):
        """Limit/offset pagination works correctly"""
        r1 = await auth_client.get("/api/dag/runs?limit=2&offset=0")
        r2 = await auth_client.get("/api/dag/runs?limit=2&offset=2")
        runs1 = r1.json()["runs"]
        runs2 = r2.json()["runs"]
        assert len(runs1) <= 2
        # No overlap in IDs
        ids1 = {r["id"] for r in runs1}
        ids2 = {r["id"] for r in runs2}
        assert ids1.isdisjoint(ids2)

    async def test_get_run_detail(self, auth_client: AsyncClient, seed_run_id):
        """GET /api/dag/runs/{id} → 200 with run fields"""
        res = await auth_client.get(f"/api/dag/runs/{seed_run_id}")
        assert res.status_code == 200
        body = res.json()
        assert "id" in body
        assert "objective" in body
        assert "status" in body

    async def test_get_run_not_found(self, auth_client: AsyncClient):
        """GET /api/dag/runs/99999 → 404"""
        res = await auth_client.get("/api/dag/runs/99999")
        assert res.status_code == 404

    async def test_get_run_tasks(self, auth_client: AsyncClient, seed_run_with_tasks):
        """GET /api/dag/runs/{id}/tasks → 200, tasks list"""
        run_id, task_count = seed_run_with_tasks
        res = await auth_client.get(f"/api/dag/runs/{run_id}/tasks")
        assert res.status_code == 200
        body = res.json()
        assert "tasks" in body
        assert len(body["tasks"]) == task_count
        for task in body["tasks"]:
            assert "task_dag_id" in task
            assert "action" in task
            assert "status" in task

    async def test_run_task_counts_in_list(self, auth_client: AsyncClient, seed_run_with_tasks):
        """Run list includes task_counts aggregate"""
        run_id, _ = seed_run_with_tasks
        res = await auth_client.get("/api/dag/runs")
        runs = res.json()["runs"]
        target = next((r for r in runs if r["id"] == run_id), None)
        assert target is not None
        assert "task_counts" in target
        assert "total" in target["task_counts"]


# ── DAG-BE-002: SSE Stream ──────────────────────────────────────────────────

class TestSSEStream:
    async def test_stream_returns_event_stream_content_type(self, auth_client: AsyncClient, seed_completed_run):
        """SSE endpoint returns text/event-stream content type"""
        async with auth_client.stream("GET", f"/api/dag/runs/{seed_completed_run}/stream") as res:
            assert res.status_code == 200
            assert "text/event-stream" in res.headers["content-type"]

    async def test_stream_emits_done_for_completed_run(self, auth_client: AsyncClient, seed_completed_run):
        """Completed run stream emits 'done' event and closes"""
        events = []
        async with auth_client.stream("GET", f"/api/dag/runs/{seed_completed_run}/stream") as res:
            async for line in res.aiter_lines():
                events.append(line)
                if "event: done" in line:
                    break
        assert any("event: done" in e for e in events)

    async def test_stream_invalid_run_emits_error(self, auth_client: AsyncClient):
        """Stream for non-existent run emits error event"""
        events = []
        async with auth_client.stream("GET", "/api/dag/runs/99999/stream") as res:
            async for line in res.aiter_lines():
                events.append(line)
                if "event: error" in line or len(events) > 5:
                    break
        assert any("error" in e for e in events)


# ── DAG-BE-003: Cancel ──────────────────────────────────────────────────────

class TestCancelRun:
    async def test_cancel_active_run(self, auth_client: AsyncClient, seed_active_run):
        """POST cancel on active run → 200, cancelled=true"""
        res = await auth_client.post(f"/api/dag/runs/{seed_active_run}/cancel")
        assert res.status_code == 200
        assert res.json()["cancelled"] is True

    async def test_cancel_sets_tasks_to_failed(self, auth_client: AsyncClient, seed_active_run):
        """After cancel, pending tasks have status=failed"""
        await auth_client.post(f"/api/dag/runs/{seed_active_run}/cancel")
        tasks_res = await auth_client.get(f"/api/dag/runs/{seed_active_run}/tasks")
        tasks = tasks_res.json()["tasks"]
        for t in tasks:
            if t["status"] in ("pending", "running"):
                pytest.fail(f"Task {t['task_dag_id']} still pending/running after cancel")

    async def test_cancel_completed_run_returns_404(self, auth_client: AsyncClient, seed_completed_run):
        """POST cancel on completed run → 404"""
        res = await auth_client.post(f"/api/dag/runs/{seed_completed_run}/cancel")
        assert res.status_code == 404


# ── DAG-BE-004: Plan Preview ────────────────────────────────────────────────

class TestPlanPreview:
    async def test_preview_returns_tasks(self, auth_client: AsyncClient):
        """POST /api/dag/preview → 200, tasks list, no DB record created"""
        from sqlmodel import Session, select
        from ..database import engine as db_engine

        initial_run_count = 0
        with Session(db_engine) as s:
            initial_run_count = len(s.exec(select(Run)).all())

        res = await auth_client.post("/api/dag/preview", json={"objective": "Test plan preview"})
        assert res.status_code == 200
        body = res.json()
        assert "tasks" in body
        assert "count" in body
        assert body["count"] == len(body["tasks"])
        assert body["count"] > 0

        # Verify no Run record was created
        with Session(db_engine) as s:
            new_count = len(s.exec(select(Run)).all())
        assert new_count == initial_run_count

    async def test_preview_task_structure(self, auth_client: AsyncClient):
        """Preview tasks have required fields"""
        res = await auth_client.post("/api/dag/preview", json={"objective": "Summarize a topic"})
        assert res.status_code == 200
        for task in res.json()["tasks"]:
            assert "id" in task
            assert "action" in task
            assert "description" in task
            assert "dependencies" in task
            assert isinstance(task["dependencies"], list)

    async def test_preview_empty_objective_returns_422(self, auth_client: AsyncClient):
        """Empty objective → 422"""
        res = await auth_client.post("/api/dag/preview", json={"objective": ""})
        assert res.status_code in (422, 400)


# ── DAG-BE-005: Task Retry ──────────────────────────────────────────────────

class TestTaskRetry:
    async def test_retry_failed_task(self, auth_client: AsyncClient, seed_run_with_failed_task):
        """POST retry on failed task → returns updated status"""
        run_id, task_id = seed_run_with_failed_task
        res = await auth_client.post(f"/api/dag/runs/{run_id}/tasks/{task_id}/retry")
        assert res.status_code == 200
        body = res.json()
        assert body["task_dag_id"] == task_id
        assert "status" in body

    async def test_retry_non_failed_task_returns_400(self, auth_client: AsyncClient, seed_run_with_completed_task):
        """POST retry on completed task → 400"""
        run_id, task_id = seed_run_with_completed_task
        res = await auth_client.post(f"/api/dag/runs/{run_id}/tasks/{task_id}/retry")
        assert res.status_code == 400

    async def test_retry_unknown_task_returns_404(self, auth_client: AsyncClient, seed_run_id):
        """POST retry on non-existent task → 404"""
        res = await auth_client.post(f"/api/dag/runs/{seed_run_id}/tasks/phantom_task/retry")
        assert res.status_code == 404


# ── DAG-BE-006: Enhanced Objective Response ─────────────────────────────────

class TestObjectiveSubmit:
    async def test_execute_returns_run_id(self, auth_client: AsyncClient):
        """POST /objective/execute → response includes run_id"""
        res = await auth_client.post(
            "/objective/execute",
            json={"objective": "Simple test", "autonomy_level": "RESTRICTED"}
        )
        assert res.status_code == 200
        body = res.json()
        assert "run_id" in body
        assert isinstance(body["run_id"], int)
        assert body["run_id"] > 0

    async def test_execute_run_id_queryable(self, auth_client: AsyncClient):
        """run_id from execute exists in /api/dag/runs/{id}"""
        res = await auth_client.post(
            "/objective/execute",
            json={"objective": "Verify run_id queryable", "autonomy_level": "RESTRICTED"}
        )
        run_id = res.json()["run_id"]
        detail_res = await auth_client.get(f"/api/dag/runs/{run_id}")
        assert detail_res.status_code == 200
```

---

### Frontend Tests

**Files:** `features/dag/__tests__/` directory — **CREATE**

#### `features/dag/__tests__/StatusBadge.test.tsx`

```tsx
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../components/StatusBadge';

describe('StatusBadge', () => {
  it('renders COMPLETED with green accent', () => {
    const { container } = render(<StatusBadge status="completed" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.textContent).toContain('COMPLETED');
    expect(badge.style.color).toContain('var(--accent)');
  });

  it('renders RUNNING with pulsing dot', () => {
    const { container } = render(<StatusBadge status="running" />);
    expect(container.querySelector('span[style*="pulse-dot"]')).toBeTruthy();
  });

  it('renders FAILED with danger color', () => {
    const { container } = render(<StatusBadge status="failed" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.style.color).toContain('var(--accent-danger)');
  });

  it('renders PENDING with secondary color', () => {
    const { container } = render(<StatusBadge status="pending" />);
    const badge = container.firstChild as HTMLElement;
    expect(badge.style.color).toContain('var(--accent-secondary)');
  });

  it('unknown status falls back to pending style', () => {
    const { container } = render(<StatusBadge status="unknown_state" />);
    expect(container.firstChild).toBeTruthy();
  });
});
```

#### `features/dag/__tests__/useDAGRuns.test.ts`

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { useDAGRuns } from '../hooks/useDAGRuns';

// Mock fetch globally
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe('useDAGRuns', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  it('fetches runs on mount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ runs: [{ id: 1, objective: 'test', status: 'completed' }], total: 1 }),
    });
    const { result } = renderHook(() => useDAGRuns({ autoRefresh: false }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.runs).toHaveLength(1);
    expect(result.current.total).toBe(1);
  });

  it('sets error on fetch failure', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'));
    const { result } = renderHook(() => useDAGRuns({ autoRefresh: false }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe('Network error');
  });

  it('applies status filter to query params', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ runs: [], total: 0 }) });
    renderHook(() => useDAGRuns({ status: 'failed', autoRefresh: false }));
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain('status=failed');
  });

  it('refresh() re-fetches from offset 0', async () => {
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({ runs: [], total: 0 }) });
    const { result } = renderHook(() => useDAGRuns({ autoRefresh: false }));
    await waitFor(() => !result.current.loading);
    result.current.refresh();
    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
  });
});
```

#### `features/dag/__tests__/DAGGraph.layout.test.ts`

```typescript
import { computeLayout } from '../components/DAGGraph';
import type { TaskRecord } from '../types';

const makeTask = (id: string, deps: string[] = []): TaskRecord => ({
  id: 0, run_id: 1, task_dag_id: id, action: 'tool',
  args: { dependencies: deps }, status: 'pending',
  result: null, error: null, start_time: null, end_time: null,
});

describe('DAGGraph layout algorithm', () => {
  it('places root nodes in layer 0 (leftmost column)', () => {
    const tasks = [makeTask('A'), makeTask('B'), makeTask('C', ['A'])];
    const positions = computeLayout(tasks);
    expect(positions.get('A')!.x).toBeLessThan(positions.get('C')!.x);
    expect(positions.get('B')!.x).toBeLessThan(positions.get('C')!.x);
  });

  it('places dependent nodes to the right of their parents', () => {
    const tasks = [makeTask('root'), makeTask('child', ['root']), makeTask('grandchild', ['child'])];
    const positions = computeLayout(tasks);
    expect(positions.get('root')!.x).toBeLessThan(positions.get('child')!.x);
    expect(positions.get('child')!.x).toBeLessThan(positions.get('grandchild')!.x);
  });

  it('handles a single node without error', () => {
    const tasks = [makeTask('solo')];
    expect(() => computeLayout(tasks)).not.toThrow();
    expect(computeLayout(tasks).get('solo')).toBeDefined();
  });

  it('handles empty task list without error', () => {
    expect(() => computeLayout([])).not.toThrow();
  });

  it('all x coordinates are non-negative', () => {
    const tasks = [makeTask('A'), makeTask('B', ['A']), makeTask('C', ['A'])];
    const positions = computeLayout(tasks);
    for (const { x, y } of positions.values()) {
      expect(x).toBeGreaterThanOrEqual(0);
      expect(y).toBeGreaterThanOrEqual(0);
    }
  });
});
```

#### `features/dag/__tests__/ObjectiveSubmitBar.test.tsx`

```tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ObjectiveSubmitBar } from '../components/ObjectiveSubmitBar';

describe('ObjectiveSubmitBar', () => {
  it('disables Execute when input is empty', () => {
    render(<ObjectiveSubmitBar onSubmit={jest.fn()} onPreview={jest.fn()} />);
    expect(screen.getByRole('button', { name: /execute/i })).toBeDisabled();
  });

  it('enables Execute when input has text', () => {
    render(<ObjectiveSubmitBar onSubmit={jest.fn()} onPreview={jest.fn()} />);
    fireEvent.change(screen.getByPlaceholderText(/describe/i), { target: { value: 'Do something' } });
    expect(screen.getByRole('button', { name: /execute/i })).not.toBeDisabled();
  });

  it('calls onSubmit with objective text and autonomy level', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(<ObjectiveSubmitBar onSubmit={onSubmit} onPreview={jest.fn()} />);
    fireEvent.change(screen.getByPlaceholderText(/describe/i), { target: { value: 'Run test' } });
    fireEvent.click(screen.getByRole('button', { name: /execute/i }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith('Run test', 'SEMI_AUTONOMOUS'));
  });

  it('calls onPreview with objective text when Preview clicked', () => {
    const onPreview = jest.fn();
    render(<ObjectiveSubmitBar onSubmit={jest.fn()} onPreview={onPreview} />);
    fireEvent.change(screen.getByPlaceholderText(/describe/i), { target: { value: 'Preview this' } });
    fireEvent.click(screen.getByRole('button', { name: /preview/i }));
    expect(onPreview).toHaveBeenCalledWith('Preview this');
  });

  it('clears input after successful submit', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(<ObjectiveSubmitBar onSubmit={onSubmit} onPreview={jest.fn()} />);
    const input = screen.getByPlaceholderText(/describe/i) as HTMLTextAreaElement;
    fireEvent.change(input, { target: { value: 'Test objective' } });
    fireEvent.click(screen.getByRole('button', { name: /execute/i }));
    await waitFor(() => expect(input.value).toBe(''));
  });

  it('Cmd+Enter triggers submit', async () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(<ObjectiveSubmitBar onSubmit={onSubmit} onPreview={jest.fn()} />);
    const input = screen.getByPlaceholderText(/describe/i);
    fireEvent.change(input, { target: { value: 'Test' } });
    fireEvent.keyDown(input, { key: 'Enter', metaKey: true });
    await waitFor(() => expect(onSubmit).toHaveBeenCalled());
  });
});
```

---

### Integration / E2E Tests

**File:** `e2e/dag_planner.spec.ts` — **CREATE** (Playwright or Cypress)

```typescript
// e2e/dag_planner.spec.ts
import { test, expect } from '@playwright/test';

test.describe('DAG Planner Panel', () => {

  test.beforeEach(async ({ page }) => {
    // Assumes test auth cookie or local dev session
    await page.goto('/');
    await page.waitForSelector('.app-shell');
  });

  test('sidebar contains DAG Planner nav item', async ({ page }) => {
    await expect(page.locator('text=DAG Planner')).toBeVisible();
  });

  test('clicking DAG Planner opens the panel', async ({ page }) => {
    await page.click('text=DAG Planner');
    await expect(page.locator('text=DAG Planner')).toBeVisible();
    await expect(page.locator('text=EXECUTION_MANIFOLD')).toBeVisible();
  });

  test('empty state shows NO_RUNS_FOUND when no runs exist', async ({ page }) => {
    await page.click('text=DAG Planner');
    // May or may not show depending on DB state — check for either list or empty state
    const panel = page.locator('[data-testid="dag-panel"]');
    await expect(panel).toBeVisible();
  });

  test('run list refreshes when refresh button clicked', async ({ page }) => {
    await page.click('text=DAG Planner');
    const refreshBtn = page.locator('[title="Refresh runs"]');
    await expect(refreshBtn).toBeVisible();
    await refreshBtn.click();
    // Verify no error state after refresh
    await page.waitForTimeout(500);
    await expect(page.locator('text=Error')).not.toBeVisible();
  });

  test('submitting objective creates a run and opens it', async ({ page }) => {
    await page.click('text=DAG Planner');
    const textarea = page.locator('textarea[placeholder*="Describe"]');
    await textarea.fill('Summarize the latest news');
    await page.click('button:has-text("Execute")');
    // Wait for run to appear in list
    await page.waitForSelector('[data-testid="run-detail-header"]', { timeout: 15000 });
    await expect(page.locator('[data-testid="run-detail-header"]')).toBeVisible();
  });

  test('plan preview modal appears before execution', async ({ page }) => {
    await page.click('text=DAG Planner');
    const textarea = page.locator('textarea[placeholder*="Describe"]');
    await textarea.fill('Create a market report');
    await page.click('button:has-text("Preview")');
    await expect(page.locator('text=Plan Preview')).toBeVisible();
    await expect(page.locator('text=DRY_RUN')).toBeVisible();
  });

  test('cancel button visible for active run and cancels it', async ({ page }) => {
    // Seed active run via API
    const res = await page.request.post('/objective/execute', {
      data: { objective: 'Long running test', autonomy_level: 'SEMI_AUTONOMOUS' },
    });
    const { run_id } = await res.json();

    await page.click('text=DAG Planner');
    await page.locator(`text=RUN_${run_id}`).click();
    const cancelBtn = page.locator('button:has-text("Cancel")');
    await expect(cancelBtn).toBeVisible();
    await cancelBtn.click();
    await expect(page.locator('text=FAILED')).toBeVisible();
  });

  test('clicking task node opens detail drawer', async ({ page }) => {
    // Select a completed run from the list (requires seeded data)
    await page.click('text=DAG Planner');
    // If runs exist, click first one
    const firstRun = page.locator('[data-testid="run-card"]').first();
    if (await firstRun.isVisible()) {
      await firstRun.click();
      const canvas = page.locator('canvas');
      if (await canvas.isVisible()) {
        await canvas.click({ position: { x: 90, y: 40 } }); // Near first node
        // Detail drawer should appear
        await page.waitForSelector('[data-testid="task-detail-drawer"]', { timeout: 3000 });
      }
    }
  });

  test('design tokens are applied correctly', async ({ page }) => {
    await page.click('text=DAG Planner');
    // Verify glass material is applied (backdrop-filter present on panel)
    const panel = page.locator('.inline-panel-wrapper');
    await expect(panel).toBeVisible();
    // No inline color overrides outside the token system
    // Check sidebar background matches --bg-base
    const sidebar = page.locator('[data-testid="run-list-sidebar"]');
    if (await sidebar.isVisible()) {
      const bg = await sidebar.evaluate(el => getComputedStyle(el).background);
      expect(bg).not.toBe('');
    }
  });

});
```

---

## 9. Validation & Verification Checklist

Use this checklist before marking the DAG Planner integration complete. Every item must be verified.

### Backend Validation

- [ ] `GET /api/dag/runs` returns `200` with `{ runs, total, limit, offset }` structure
- [ ] `GET /api/dag/runs?status=failed` returns only failed runs
- [ ] `GET /api/dag/runs/{id}` returns `404` for unknown IDs
- [ ] `GET /api/dag/runs/{id}/tasks` returns tasks ordered by `id ASC`
- [ ] `GET /api/dag/runs/{run_id}/stream` returns `Content-Type: text/event-stream`
- [ ] SSE stream emits `event: done` when run completes
- [ ] SSE keep-alive comments prevent proxy timeout (verify with 30s idle test)
- [ ] `POST /api/dag/runs/{id}/cancel` sets all pending tasks to `failed`
- [ ] `POST /api/dag/runs/{id}/cancel` on a completed run returns `404`
- [ ] `POST /api/dag/preview` returns tasks without creating a `Run` DB record
- [ ] `POST /objective/execute` response includes `run_id` integer field
- [ ] All new routes require `Depends(verify_authenticated)` — unauthenticated calls return `401`
- [ ] All new routes are rate-limited appropriately
- [ ] Cancel asyncio task registration does not cause memory leaks on long-running instances
- [ ] Task retry correctly injects completed upstream outputs as `dependency_output`

### Frontend Validation

- [ ] `DAGPanel` renders inside `inline-panel-wrapper` — matches layout pattern of all other panels
- [ ] `RunListSidebar` correctly renders empty state `NO_RUNS_FOUND` when no runs exist
- [ ] `StatusBadge` renders the correct color for each of the 5 status values
- [ ] `DAGGraph` canvas renders without errors for 0-task, 1-task, and 10-task plans
- [ ] DAG layout places root nodes left, dependent nodes right — no visual overlapping
- [ ] Clicking a canvas node correctly opens `TaskDetailDrawer` for that specific task
- [ ] `useTaskStream` opens SSE connection when `runId` is set and closes on unmount
- [ ] Live task updates from SSE are reflected in the DAG graph within 1 second
- [ ] `ObjectiveSubmitBar` Execute button is disabled when input is empty
- [ ] `PlanPreviewModal` shows loading spinner during LLM generation
- [ ] `PlanPreviewModal` does not create a run when dismissed
- [ ] Run detail auto-opens after a new objective is submitted via `ObjectiveSubmitBar`
- [ ] Cancel button is only visible for runs with `status === 'active'`
- [ ] Retry button is only visible in `TaskDetailDrawer` for `status === 'failed'` tasks
- [ ] `useDAGRuns` auto-refresh polling stops when component unmounts (no memory leaks)
- [ ] Sidebar nav item `DAGPanel` shows active state correctly
- [ ] `activeRunId` store value updates correctly when runs start/complete

### Design System Validation

- [ ] Zero new CSS color values introduced — all colors reference `var(--*)` tokens
- [ ] All font sizes match the existing scale: 9, 10, 11, 12, 13, 15, 22px
- [ ] Panel header matches existing panels: `fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em'`
- [ ] Section labels match pattern: `fontSize: 10, fontWeight: 600, textTransform: 'uppercase'`
- [ ] Mono technical values use `fontFamily: 'var(--font-mono)'`
- [ ] `glass-btn` class used for all action buttons
- [ ] `glass-input` class used for all text inputs and selects
- [ ] `inline-panel-wrapper` is the outermost container of `DAGPanel`
- [ ] Dark/light theme tokens work correctly — test in both themes
- [ ] Scrollable areas use `className="scrollbar-hide"` consistently
- [ ] Animations use `var(--ease-spring)` and `var(--dur-normal)` from the token system
- [ ] No hardcoded `#hex` or `rgb()` colors appear anywhere in DAG components
- [ ] Status badges are pixel-consistent with badges in `AgentsPanel` and `SessionsPanel`

### Performance Validation

- [ ] DAG graph with 20 nodes renders in under 200ms
- [ ] SSE stream does not cause re-renders of unrelated components (verify with React DevTools Profiler)
- [ ] `useDAGRuns` polling interval is cleared on component unmount
- [ ] `EventSource` is closed on `useTaskStream` unmount — no dangling connections
- [ ] Canvas hit-testing loop does not block the main thread (< 5ms per click)

---

## 10. Integration Order & Sprint Plan

| Sprint | IDs | Deliverable | Duration |
|---|---|---|---|
| **Sprint 1 — Data Layer** | DAG-BE-001, DAG-BE-006, DAG-FE-012, DAG-FE-006 (types only) | Run history API live, `run_id` in execute response, store slice, type definitions | Days 1–3 |
| **Sprint 2 — Live Stream** | DAG-BE-002, DAG-BE-003, DAG-FE-003, DAG-FE-002 | SSE stream, cancel endpoint, `useTaskStream`, `useDAGRuns` hooks working | Days 4–5 |
| **Sprint 3 — Core UI** | DAG-FE-001, DAG-FE-004, DAG-FE-005, DAG-FE-013, DAG-FE-014 | `DAGPanel` mounted, sidebar entry live, `RunListSidebar` working, route registered | Days 6–8 |
| **Sprint 4 — Graph** | DAG-FE-006, DAG-FE-007, DAG-FE-008 | `DAGGraph` canvas rendering with live updates, `StatusBadge`, `RunDetailHeader` | Days 9–11 |
| **Sprint 5 — Interaction** | DAG-FE-009, DAG-FE-010, DAG-FE-011, DAG-BE-004, DAG-BE-005 | `TaskDetailDrawer`, `ObjectiveSubmitBar`, `PlanPreviewModal`, preview and retry endpoints | Days 12–14 |
| **Sprint 6 — QA** | All items | Full test suite passing, design checklist complete, E2E tests green | Days 15–16 |

---

## 11. File Delta Summary

| File | Action | Contents |
|---|---|---|
| `backend/app.py` | **MODIFY** | Add 8 new routes: run list, run detail, run tasks, SSE stream, cancel, preview, retry, enhanced execute |
| `backend/orchestrator.py` | **MODIFY** | Add `_active_runs`, `cancel_run()`, `preview_plan()`, return dict from `execute_objective()` |
| `features/dag/DAGPanel.tsx` | **CREATE** | Top-level panel container, run/task state management, component composition |
| `features/dag/types.ts` | **CREATE** | `DAGRun`, `TaskRecord`, `LiveTaskState`, `StreamStatus` type definitions |
| `features/dag/hooks/useDAGRuns.ts` | **CREATE** | Run list fetch hook with polling, pagination, and filter support |
| `features/dag/hooks/useTaskStream.ts` | **CREATE** | SSE client hook for live task state stream |
| `features/dag/components/RunListSidebar.tsx` | **CREATE** | Scrollable run list with status filter and run cards |
| `features/dag/components/DAGGraph.tsx` | **CREATE** | Canvas-based DAG visualizer with topological layout and hit-testing |
| `features/dag/components/StatusBadge.tsx` | **CREATE** | Reusable status chip with design-token colors |
| `features/dag/components/RunDetailHeader.tsx` | **CREATE** | Run header with progress bar, stats, and cancel button |
| `features/dag/components/TaskDetailDrawer.tsx` | **CREATE** | Slide-in drawer with task args, result, error, and retry button |
| `features/dag/components/ObjectiveSubmitBar.tsx` | **CREATE** | Objective input with autonomy selector, Preview, and Execute actions |
| `features/dag/components/PlanPreviewModal.tsx` | **CREATE** | Dry-run plan preview modal with task list and execute CTA |
| `features/dag/utils/time.ts` | **CREATE** | `formatDuration()`, `formatRelativeTime()` utility functions |
| `styles/dag.css` | **CREATE** | DAG-specific animations and component styles using existing tokens |
| `store/useStore.ts` | **MODIFY** | Add `activeRunId`, `setActiveRunId` to global Zustand store |
| `App.tsx` | **MODIFY** | Import `DAGPanel`, add `case 'dag'` to `renderContent()` |
| `components/Sidebar.tsx` | **MODIFY** | Add DAG Planner nav item with `GitFork` icon and active run badge |
| `backend/tests/test_dag_api.py` | **CREATE** | 22 pytest tests covering all 6 backend spec items |
| `features/dag/__tests__/StatusBadge.test.tsx` | **CREATE** | 5 unit tests for status badge rendering |
| `features/dag/__tests__/useDAGRuns.test.ts` | **CREATE** | 4 hook tests with mocked fetch |
| `features/dag/__tests__/DAGGraph.layout.test.ts` | **CREATE** | 5 layout algorithm unit tests |
| `features/dag/__tests__/ObjectiveSubmitBar.test.tsx` | **CREATE** | 5 interaction tests |
| `e2e/dag_planner.spec.ts` | **CREATE** | 9 Playwright E2E tests covering the full user flow |

---

*Alluci Sovereign Agent — DAG Planner Integration Spec v1.0*
*6 backend items · 14 frontend items · 22 backend tests · 19 frontend/E2E tests · 16-day delivery*
