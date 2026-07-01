
import json
import uuid
from datetime import datetime, timezone
from ..logging_config import get_logger
from datetime import date
from typing import Dict, Any, Optional
from ..security.auth import verify_authenticated
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from sqlmodel import Session, select, col
from ..database import engine as db_engine
from ..models import SessionConfig, AgentRecord
from fastapi_csrf_protect import CsrfProtect
from .. import services

try:
    from ..models import HeartbeatOrderRecord
except ImportError:
    HeartbeatOrderRecord = None  # type: ignore

logger = get_logger("SessionsRouter")

router = APIRouter(tags=["Sessions & Agents"])

@router.get("/session", dependencies=[Depends(verify_authenticated)])
async def get_current_session():
    """Returns the current user context (soul manifest + bridge connections) for frontend hydration."""
    try:
        from .. import services
        soul = services.orchestrator.base_manifest if hasattr(services, "orchestrator") and services.orchestrator else None
        # We return an empty connections array so the frontend uses INITIAL_CONNECTIONS
        # and then relies on ChannelHealthDashboard to fetch /api/v1/channels/status.
        connections = []
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

# ─── Agent Constellation CRUD ───────────────
@router.get("/agents", dependencies=[Depends(verify_authenticated)])
async def list_agents():
    """Returns all AgentRecord entries with live DB telemetry."""
    from sqlalchemy import func
    from ..models import AgentSkillBinding, AgentChannelSubscription
    
    with Session(db_engine) as session:
        agents = session.exec(select(AgentRecord)).all()
        
        result = []
        for a in agents:
            # SQL queries for telemetry counts
            active_skills = session.exec(
                select(func.count(col(AgentSkillBinding.id))).where(AgentSkillBinding.agent_id == a.id)
            ).one()
            
            channels_query = session.exec(
                select(AgentChannelSubscription).where(AgentChannelSubscription.agent_id == a.id)
            ).all()
            
            if a.id == "core":
                channels = sum(
                    1 for sub in channels_query 
                    if getattr(services.channel_registry.get(sub.channel_id), "is_connected", False)
                )
            else:
                channels = len(channels_query)
            
            result.append({
                "id": a.id,
                "name": a.name,
                "model": a.model,
                "status": a.status,
                "description": a.description,
                "fallback_chain": a.fallback_chain,
                "engine_manifest": json.loads(a.engine_manifest or "{}"),
                "active_skills": active_skills,
                "channels": channels,
                "heartbeat_orders": json.loads(a.heartbeat_orders or "[]"),
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

    return {"agents": result}


@router.get("/agents/{agent_id}", dependencies=[Depends(verify_authenticated)])
async def get_agent(agent_id: str):
    """Return a single agent by ID."""
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Get telemetry stats
    from sqlalchemy import func
    from ..models import AgentSkillBinding, AgentChannelSubscription
    with Session(db_engine) as session:
        active_skills = session.exec(
            select(func.count(col(AgentSkillBinding.id))).where(AgentSkillBinding.agent_id == agent.id)
        ).one()
        channels_query = session.exec(
            select(AgentChannelSubscription).where(AgentChannelSubscription.agent_id == agent.id)
        ).all()
        
        if agent.id == "core":
            channels = sum(
                1 for sub in channels_query 
                if getattr(services.channel_registry.get(sub.channel_id), "is_connected", False)
            )
        else:
            channels = len(channels_query)
        
    return {
        "agent": {
            "id": agent.id,
            "name": agent.name,
            "model": agent.model,
            "status": agent.status,
            "description": agent.description,
            "fallback_chain": agent.fallback_chain,
            "system_prompt": agent.system_prompt,
            "engine_manifest": json.loads(agent.engine_manifest or "{}"),
            "active_skills": active_skills,
            "channels": channels,
            "heartbeat_orders": json.loads(agent.heartbeat_orders or "[]"),
            "soul_manifest_override": json.loads(
                agent.soul_manifest_override or "{}"
            ),
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": (
                agent.updated_at.isoformat() if agent.updated_at else None
            ),
        }
    }


@router.post(
    "/agents",
    dependencies=[
        Depends(verify_authenticated),
    ],
)
async def create_agent(request: Request, payload: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Create a new agent record."""
    agent = AgentRecord(
        id=str(uuid.uuid4())[:8],
        name=payload.get("name", "New Agent"),
        description=payload.get("description"),
        model=payload.get("model", "gpt-4o"),
        fallback_chain=payload.get("fallback_chain", "gemini-flash,claude-haiku"),
        pii_override_enabled=payload.get("pii_override_enabled", False),
        status=payload.get("status", "DRAFT"),
        system_prompt=payload.get("system_prompt"),
        heartbeat_orders=json.dumps(payload.get("heartbeat_orders", [])),
        soul_manifest_override=json.dumps(
            payload.get("soul_manifest_override", {})
        ),
        created_at=datetime.now(timezone.utc),
    )
    with Session(db_engine) as session:
        session.add(agent)
        session.commit()
        session.refresh(agent)
    return {"agent": {"id": agent.id, "name": agent.name, "status": agent.status}}


@router.put(
    "/agents/{agent_id}",
    dependencies=[
        Depends(verify_authenticated),
    ],
)
async def update_agent(request: Request, agent_id: str, payload: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Update an agent record — including heartbeat_orders."""
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        for field_name in ("name", "status", "description", "system_prompt", "pii_override_enabled"):
            if field_name in payload:
                setattr(agent, field_name, payload[field_name])

        # Load existing manifest
        try:
            manifest = json.loads(agent.engine_manifest) if agent.engine_manifest else {}
        except:
            manifest = {}
            
        if "llm" not in manifest:
            manifest["llm"] = []

        # If frontend sent a new engine matrix
        if "engine_manifest" in payload:
            manifest = payload["engine_manifest"]
            if "llm" not in manifest:
                manifest["llm"] = []
                
        # Primary Engine Handling
        if "model" in payload:
            agent.model = payload["model"]
            # Auto-inject into matrix
            if agent.model not in manifest["llm"]:
                manifest["llm"].append(agent.model)
                
        # Fallback Chain Handling
        if "fallback_chain" in payload:
            agent.fallback_chain = payload["fallback_chain"]
            # Auto-inject fallbacks into matrix
            if agent.fallback_chain:
                fallbacks = [m.strip() for m in agent.fallback_chain.split(",") if m.strip()]
                for f_model in fallbacks:
                    if f_model not in manifest["llm"]:
                        manifest["llm"].append(f_model)

        # Pruning Logic: If engine matrix is explicitly updated, and Primary Engine is no longer allowed
        if "engine_manifest" in payload and manifest["llm"]:
            if agent.model not in manifest["llm"]:
                agent.model = manifest["llm"][0]  # Safely degrade to highest priority authorized model

        agent.engine_manifest = json.dumps(manifest)

        if "heartbeat_orders" in payload:
            orders = payload["heartbeat_orders"]
            agent.heartbeat_orders = json.dumps(
                orders if isinstance(orders, list) else []
            )

        if "soul_manifest_override" in payload:
            agent.soul_manifest_override = json.dumps(
                payload["soul_manifest_override"]
            )

        agent.updated_at = datetime.now(timezone.utc)
        session.add(agent)
        session.commit()

    return {"status": "SUCCESS", "agent_id": agent_id}


@router.post(
    "/agents/delegate",
    dependencies=[
        Depends(verify_authenticated),
    ],
)
async def delegate_to_agent(
    request: Request,
    agent_id: str = Body(...), task: str = Body(...),
    csrf_protect: CsrfProtect = Depends()
):
    await csrf_protect.validate_csrf(request)
    """Delegate a task to a named agent, injecting agent context."""
    if not services.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")

    # Inject agent identity into the objective so the orchestrator and
    # planner know which agent persona is handling this task.
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)

    agent_tag = f"[Agent:{agent_id}]"
    if agent and agent.system_prompt:
        objective = (
            f"{agent_tag} Acting as '{agent.name}' ({agent.system_prompt[:200]}). "
            f"Task: {task}"
        )
    else:
        objective = f"{agent_tag} {task}"

    return await services.orchestrator.execute_objective(
        objective=objective, autonomy="RESTRICTED"
    )


@router.delete(
    "/agents/{agent_id}",
    dependencies=[
        Depends(verify_authenticated),
    ],
)
async def delete_agent(request: Request, agent_id: str, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Delete an agent record."""
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        session.delete(agent)
        session.commit()
    return {"status": "DELETED"}


@router.get(
    "/agents/{agent_id}/heartbeat/history",
    dependencies=[Depends(verify_authenticated)],
)
async def get_agent_heartbeat_history(agent_id: str, limit: int = 20):
    """Recent heartbeat execution history for a specific agent."""
    if HeartbeatOrderRecord is None:
        raise HTTPException(status_code=501, detail="HeartbeatOrderRecord not yet migrated")
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
        ],
    }


@router.get("/heartbeat/history", dependencies=[Depends(verify_authenticated)])
async def get_root_heartbeat_history(limit: int = 30):
    """Recent heartbeat execution history for the root agent."""
    if HeartbeatOrderRecord is None:
        raise HTTPException(status_code=501, detail="HeartbeatOrderRecord not yet migrated")
    with Session(db_engine) as session:
        records = session.exec(
            select(HeartbeatOrderRecord)
            .where(HeartbeatOrderRecord.agent_id == None)  # noqa: E711
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
