
import logging
from ..logging_config import get_logger
from datetime import date
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlmodel import Session, select
from ..security.auth import verify_authenticated
from ..database import engine as db_engine
from ..models import SessionConfig
from .. import services

logger = get_logger("SessionsRouter")

router = APIRouter(tags=["Sessions & Agents"])

@router.get("/api/sessions", dependencies=[Depends(verify_authenticated)])
async def list_sessions(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all active and historical sessions."""
    if not services.usage_tracker:
        raise HTTPException(status_code=503, detail="Usage tracker not ready")
    s_date = date.fromisoformat(start) if start else None
    e_date = date.fromisoformat(end) if end else None
    return services.usage_tracker.get_sessions(start=s_date, end=e_date, limit=limit)

@router.get("/api/sessions/{session_key}/config", dependencies=[Depends(verify_authenticated)])
async def get_session_config(session_key: str):
    """Get per-session configuration overrides."""
    with Session(db_engine) as session:
        stmt = select(SessionConfig).where(SessionConfig.session_key == session_key)
        config = session.exec(stmt).first()
        if not config:
            return {"session_key": session_key, "overrides": {}}
        return config

@router.get("/api/agents", dependencies=[Depends(verify_authenticated)])
async def get_agents():
    """Returns the agent constellation configuration."""
    return {
        "agents": [
            { "id": "root", "name": "Sovereign Root", "model": "gpt-4o", "status": "READY", "active_skills": 12, "channels": 4 },
            { "id": "researcher", "name": "Deep Researcher", "model": "gemini-1.5-pro", "status": "IDLE", "active_skills": 4, "channels": 0 },
            { "id": "coder", "name": "Polyglot Coder", "model": "gpt-4o", "status": "IDLE", "active_skills": 8, "channels": 0 }
        ]
    }

@router.post("/api/agents/delegate", dependencies=[Depends(verify_authenticated)])
async def delegate_to_agent(agent_id: str = Body(...), task: str = Body(...)):
    """Delegates a task to a virtual agent in the constellation."""
    if not services.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    return await services.orchestrator.multi_agent_delegate(agent_id, task)
