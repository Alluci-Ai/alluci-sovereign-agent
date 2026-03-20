
import logging
from ..logging_config import get_logger
import json, uuid
from datetime import date, datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from sqlmodel import Session, select, col
from ..security.auth import verify_authenticated
from ..database import engine as db_engine
from ..models import SessionConfig, AgentRecord, HeartbeatOrderRecord
from fastapi_csrf_protect import CsrfProtect
from .. import services

logger = get_logger("SessionsRouter")

router = APIRouter(tags=["Sessions & Agents"])

@router.get("/session", dependencies=[Depends(verify_authenticated)])
async def get_current_session():
    """Returns the current user context (soul manifest + bridge connections) for frontend hydration."""
    try:
        from .. import services
        soul = services.orchestrator.base_manifest if services.orchestrator else None
        connections = services.orchestrator.bridge_manager.get_connections() if (services.orchestrator and services.orchestrator.bridge_manager) else []
        return {
            "status": "SUCCESS",
            "soul": soul,
            "connections": connections
        }
    except Exception as e:
        logger.error(f"Failed to get session: {e}")
        raise HTTPException(status_code=500, detail="Internal session error")

@router.get("/sessions", dependencies=[Depends(verify_authenticated)])
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

@router.get("/sessions/{session_key}/config", dependencies=[Depends(verify_authenticated)])
async def get_session_config(session_key: str):
    """Get per-session configuration overrides."""
    with Session(db_engine) as session:
        stmt = select(SessionConfig).where(SessionConfig.session_key == session_key)
        config = session.exec(stmt).first()
        if not config:
            return {"session_key": session_key, "overrides": {}}
        return config

# ── Agent CRUD Endpoints ──────────────────────────────────────────────────────

@router.get("/agents", dependencies=[Depends(verify_authenticated)])
async def get_agents():
    """Returns all AgentRecord entries from the database."""
    with Session(db_engine) as session:
        agents = session.exec(select(AgentRecord)).all()

    if not agents:
        # Seed with default root agent on first call
        return {
            "agents": [
                {
                    "id": "root",
                    "name": "Sovereign Root",
                    "model": "gpt-4o",
                    "status": "ACTIVE",
                    "description": "Primary sovereign agent",
                    "heartbeat_orders": "[]",
                }
            ]
        }
    return {
        "agents": [
            {
                "id": a.id,
                "name": a.name,
                "model": a.model,
                "status": a.status,
                "description": a.description,
                "fallback_chain": a.fallback_chain,
                "heartbeat_orders": json.loads(a.heartbeat_orders or "[]"),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in agents
        ]
    }


@router.get("/agents/{agent_id}", dependencies=[Depends(verify_authenticated)])
async def get_agent(agent_id: str):
    """Get a single agent by ID."""
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "model": agent.model,
            "status": agent.status,
            "description": agent.description,
            "fallback_chain": agent.fallback_chain,
            "system_prompt": agent.system_prompt,
            "heartbeat_orders": json.loads(agent.heartbeat_orders or "[]"),
            "soul_manifest_override": json.loads(agent.soul_manifest_override or "{}"),
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
        }
    }


@router.post("/agents", dependencies=[Depends(verify_authenticated), Depends(CsrfProtect().validate_csrf)])
async def create_agent(payload: Dict[str, Any] = Body(...)):
    """Create a new agent record."""
    agent_id = str(uuid.uuid4())[:8]
    agent = AgentRecord(
        id=agent_id,
        name=payload.get("name", "New Agent"),
        description=payload.get("description"),
        model=payload.get("model", "gpt-4o"),
        fallback_chain=payload.get("fallback", "gemini-flash,claude-haiku"),
        status=payload.get("status", "DRAFT"),
        system_prompt=payload.get("system_prompt"),
        heartbeat_orders=json.dumps(payload.get("heartbeat_orders", [])),
        created_at=datetime.now(timezone.utc),
    )
    with Session(db_engine) as session:
        session.add(agent)
        session.commit()
        session.refresh(agent)

    return {"agent": {"id": agent.id, "name": agent.name, "status": agent.status}}


@router.put(
    "/agents/{agent_id}",
    dependencies=[Depends(verify_authenticated), Depends(CsrfProtect().validate_csrf)],
)
async def update_agent(agent_id: str, payload: Dict[str, Any] = Body(...)):
    """Update an agent record including heartbeat_orders."""
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        if "name" in payload:
            agent.name = payload["name"]
        if "model" in payload:
            agent.model = payload["model"]
        if "status" in payload:
            agent.status = payload["status"]
        if "description" in payload:
            agent.description = payload["description"]
        if "system_prompt" in payload:
            agent.system_prompt = payload["system_prompt"]
        if "heartbeat_orders" in payload:
            orders = payload["heartbeat_orders"]
            agent.heartbeat_orders = json.dumps(orders if isinstance(orders, list) else [])
        if "soul_manifest_override" in payload:
            agent.soul_manifest_override = json.dumps(payload["soul_manifest_override"])
        if "fallback" in payload:
            agent.fallback_chain = payload["fallback"]

        agent.updated_at = datetime.now(timezone.utc)
        session.add(agent)
        session.commit()

    return {"status": "SUCCESS", "agent_id": agent_id}


@router.delete(
    "/agents/{agent_id}",
    dependencies=[Depends(verify_authenticated), Depends(CsrfProtect().validate_csrf)],
)
async def delete_agent(agent_id: str):
    """Delete an agent record."""
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        session.delete(agent)
        session.commit()
    return {"status": "DELETED"}


@router.get("/agents/{agent_id}/heartbeat/history", dependencies=[Depends(verify_authenticated)])
async def get_agent_heartbeat_history(agent_id: str, limit: int = 20):
    """Get recent heartbeat order execution history for an agent."""
    from .. import services
    if not services.orchestrator or not services.orchestrator.heartbeat:
        raise HTTPException(status_code=503, detail="Heartbeat daemon not ready")

    with Session(db_engine) as session:
        records = session.exec(
            select(HeartbeatOrderRecord)
            .where(HeartbeatOrderRecord.agent_id == agent_id)
            .order_by(col(HeartbeatOrderRecord.fired_at).desc())
            .limit(limit)
        ).all()

    return {
        "agent_id": agent_id,
        "history": [
            {
                "order_id": r.order_id,
                "fired_at": r.fired_at,
                "probe_type": r.probe_type,
                "action_type": r.action_type,
                "outcome": r.outcome,
                "detail": r.detail,
                "signal_stored": r.signal_stored,
            }
            for r in records
        ]
    }


@router.get("/heartbeat/history", dependencies=[Depends(verify_authenticated)])
async def get_root_heartbeat_history(limit: int = 30):
    """Get recent root-agent heartbeat order execution history."""
    with Session(db_engine) as session:
        records = session.exec(
            select(HeartbeatOrderRecord)
            .where(HeartbeatOrderRecord.agent_id == None)
            .order_by(col(HeartbeatOrderRecord.fired_at).desc())
            .limit(limit)
        ).all()

    return {
        "history": [
            {
                "order_id": r.order_id,
                "fired_at": r.fired_at,
                "probe_type": r.probe_type,
                "action_type": r.action_type,
                "outcome": r.outcome,
                "detail": r.detail,
            }
            for r in records
        ]
    }

@router.post("/agents/delegate", dependencies=[Depends(verify_authenticated), Depends(CsrfProtect().validate_csrf)])
async def delegate_to_agent(agent_id: str = Body(...), task: str = Body(...)):
    """Delegates a task to a virtual agent in the constellation."""
    if not services.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    return await services.orchestrator.multi_agent_delegate(agent_id, task)
