
import os
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



PROVIDER_MAP = {
    "gpt-4o": "openai",
    "gpt-4o-mini": "openai",
    "gemini-1.5-pro": "googleCloud",
    "gemini-1.5-flash": "googleCloud",
    "claude-3-5-sonnet-20241022": "anthropic",
    "claude-3-haiku-20240307": "anthropic",
    "claude-3-opus-20240229": "anthropic",
    "llama3-70b-8192": "groq",
    "deepseek-coder": "deepseek",
    "Alluci Polytope 31B-it-4bit": "local"
}

def _get_provider_for_model(model_id: str) -> str:
    return PROVIDER_MAP.get(model_id, model_id)

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
            manifest_val = payload["engine_manifest"]
            if isinstance(manifest_val, str):
                try:
                    manifest = json.loads(manifest_val)
                except:
                    manifest = {}
            else:
                manifest = manifest_val
                
            if "llm" not in manifest:
                manifest["llm"] = []
                
        # Primary Engine Handling
        if "model" in payload:
            agent.model = payload["model"]
            provider = _get_provider_for_model(agent.model)
            if provider not in manifest["llm"]:
                manifest["llm"].append(provider)
                
        # Fallback Chain Handling
        if "fallback_chain" in payload:
            agent.fallback_chain = payload["fallback_chain"]
            if agent.fallback_chain:
                fallbacks = [m.strip() for m in agent.fallback_chain.split(",") if m.strip()]
                for f_model in fallbacks:
                    f_prov = _get_provider_for_model(f_model)
                    if f_prov not in manifest["llm"]:
                        manifest["llm"].append(f_prov)

        # Graceful Degradation replaces the need for hard pruning here, 
        # but we ensure we don't accidentally overwrite agent.model with a provider ID.


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

WORKSPACE_DIR = os.path.abspath("backend/workspace")

@router.get("/agents/{agent_id}/tools", dependencies=[Depends(verify_authenticated)])
async def get_agent_tools(agent_id: str):
    """Get all tools with their agent-specific overrides."""
    if not services.skill_manager:
        return {"tools": []}
    global_skills = await services.skill_manager.list_skills()
    
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)
        
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    agent_tools = {}
    if hasattr(agent, "tools_manifest") and agent.tools_manifest:
        try:
            agent_tools = json.loads(agent.tools_manifest)
        except Exception:
            pass
            
    tools = []
    for skill in global_skills:
        skill_id = skill.get("id")
        if not skill_id:
            continue
        skill_name = skill.get("name", skill_id)
        skill_desc = skill.get("description", "")
        
        agent_override = agent_tools.get(skill_id, {})
        enabled = agent_override.get("enabled", False)
        params = agent_override.get("params", "{\n  \n}")
        
        tools.append({
            "id": skill_id,
            "name": skill_name,
            "description": skill_desc,
            "enabled": enabled,
            "params": params
        })
        
    return {"tools": tools}


@router.put("/agents/{agent_id}/tools", dependencies=[Depends(verify_authenticated)])
async def update_agent_tools(request: Request, agent_id: str, payload: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Update agent-specific tool bindings and parameter overrides."""
    tools_payload = payload.get("tools", [])
    
    tools_manifest = {}
    for t in tools_payload:
        if t.get("enabled"):
            tools_manifest[t.get("id")] = {
                "enabled": True,
                "params": t.get("params", "{}")
            }
            
    with Session(db_engine) as session:
        agent = session.get(AgentRecord, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
            
        agent.tools_manifest = json.dumps(tools_manifest)
        session.add(agent)
        session.commit()
        
    return {"status": "SUCCESS"}


@router.get("/agents/{agent_id}/files", dependencies=[Depends(verify_authenticated)])
async def list_agent_files(agent_id: str):
    agent_dir = os.path.join(WORKSPACE_DIR, agent_id)
    if not os.path.exists(agent_dir):
        return {"files": []}
    files = []
    for f in os.listdir(agent_dir):
        if os.path.isfile(os.path.join(agent_dir, f)):
            files.append(f)
    return {"files": files}


@router.get("/agents/{agent_id}/files/{filename:path}", dependencies=[Depends(verify_authenticated)])
async def get_agent_file(agent_id: str, filename: str):
    agent_dir = os.path.join(WORKSPACE_DIR, agent_id)
    file_path = os.path.abspath(os.path.join(agent_dir, filename))
    if not file_path.startswith(agent_dir):
        raise HTTPException(status_code=403, detail="Path traversal forbidden")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"content": content}


@router.put("/agents/{agent_id}/files/{filename:path}", dependencies=[Depends(verify_authenticated)])
async def save_agent_file(request: Request, agent_id: str, filename: str, payload: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    agent_dir = os.path.join(WORKSPACE_DIR, agent_id)
    os.makedirs(agent_dir, exist_ok=True)
    file_path = os.path.abspath(os.path.join(agent_dir, filename))
    if not file_path.startswith(agent_dir):
        raise HTTPException(status_code=403, detail="Path traversal forbidden")
    
    content = payload.get("content", "")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"status": "SUCCESS"}
