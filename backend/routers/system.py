
from ..logging_config import get_logger
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select, text
from ..config import settings
from ..database import engine as db_engine
from ..models import AuditEntry
from ..security.auth import verify_authenticated
from .. import services
from ..routers.models import scan_local_models
from fastapi_csrf_protect import CsrfProtect

logger = get_logger("SystemRouter")

router = APIRouter(tags=["System Status"])

@router.get("/health")
async def health():
    """Public Kubernetes-style liveness probe."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@router.get("/system/health", dependencies=[Depends(verify_authenticated)])
async def get_detailed_health():
    """Runs diagnostic checks across primary modules for the Health dashboard."""
    import time
    from ..metrics import metrics
    
    # 1. Database
    db_status = "healthy"
    try:
        with Session(db_engine) as session:
            session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
 
    # 2. Vault Security
    vault_status = "healthy" if services.vault else "warning"
 
    # 3. Model Router
    router_status = "unhealthy"
    if services.router:
        router_status = "warning"  # configured but providers might not be verified
 
    # 4. Local Inference
    local_inference_status = "healthy" if services.local_inference else "unhealthy"
 
    # 5. Bridges
    active_bridges = list(services.vault.get_active_vaults()) if services.vault else []
 
    # 6. Cron Engine Tasks
    cron_status = "healthy" if services.task_manager else "unhealthy"
 
    return {
        "database": db_status,
        "vault": vault_status,
        "model_router": router_status,
        "local_inference": local_inference_status,
        "bridges": len(active_bridges),
        "cron_engine": cron_status,
        "uptime": time.time() - metrics.start_time,
    }

@router.get("/ready")
async def readiness_check():
    """
    Public readiness check for Kubernetes health.
    """
    checks = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "unstable",
        "orchestrator": "online" if services.orchestrator else "starting",
        "ace": "online" if services.ace else "offline",
    }
    try:
        with Session(db_engine) as session:
            session.execute(text("SELECT 1"))
        checks["database"] = "stable"
    except Exception as e:
        logger.error(f"[ HEALTH ]: Database integrity check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unresponsive")

    if services.redis_client:
        try:
            await services.redis_client.ping()
            checks["redis"] = "stable"
        except Exception as e:
            logger.error(f"[ HEALTH ]: Redis ping failed: {e}")
            checks["redis"] = "failing"
    else:
        checks["redis"] = "inactive"

    return {"status": "ready", "checks": checks}

@router.get("/system/ready", dependencies=[Depends(verify_authenticated)])
async def api_readiness_check():
    """Protected readiness check."""
    return await readiness_check()

@router.get("/system/providers", dependencies=[Depends(verify_authenticated)])
async def get_system_providers():
    """
    Scans the system (config, vault, etc.) for active, authenticated LLM/Audio/Video providers
    and returns a structured list for the Engine Matrix.
    """
    vault_keys = {}
    if getattr(services, "vault", None):
        keys = await services.vault.retrieve_secret("alluci_api_keys") or {}
        vault_keys = keys if isinstance(keys, dict) else {}

    llm_keys = vault_keys.get("llm", {})
    audio_keys = vault_keys.get("audio", {})
    video_keys = vault_keys.get("video", {})
    image_keys = vault_keys.get("image", {})
    music_keys = vault_keys.get("music", {})

    providers = {
        "llm": [],
        "video": [],
        "image": [],
        "audio": [],
        "music": []
    }
    
    # 1. Local LLM Scan
    local_llms = await scan_local_models()
    for local in local_llms:
        providers["llm"].append({
            "id": local["id"], 
            "name": local["name"], 
            "provider": "local", 
            "connected": True
        })
        
    # 2. Cloud LLMs
    has_openai = bool(llm_keys.get("openai") or getattr(settings, "OPENAI_API_KEY", None))
    providers["llm"].extend([
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "connected": has_openai},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openai", "connected": has_openai}
    ])
    
    has_google = bool(llm_keys.get("googleCloud") or getattr(settings, "GEMINI_API_KEY", None))
    providers["llm"].extend([
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "google", "connected": has_google},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "provider": "google", "connected": has_google}
    ])
    
    has_anthropic = bool(llm_keys.get("anthropic") or getattr(settings, "ANTHROPIC_API_KEY", None))
    providers["llm"].extend([
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "anthropic", "connected": has_anthropic},
        {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku", "provider": "anthropic", "connected": has_anthropic},
        {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus", "provider": "anthropic", "connected": has_anthropic}
    ])
    
    has_groq = bool(llm_keys.get("groq") or getattr(settings, "GROQ_API_KEY", None))
    providers["llm"].append({"id": "llama3-70b-8192", "name": "Groq LLaMA 3", "provider": "groq", "connected": has_groq})

    has_deepseek = bool(llm_keys.get("deepseek") or getattr(settings, "DEEPSEEK_API_KEY", None))
    providers["llm"].append({"id": "deepseek-coder", "name": "DeepSeek Coder", "provider": "deepseek", "connected": has_deepseek})
    
    # 3. Video
    providers["video"].append({"id": "google/veo", "name": "Google Veo", "provider": "google", "connected": has_google})
    has_runway = bool(video_keys.get("runway"))
    providers["video"].append({"id": "runway-gen2", "name": "RunwayML Gen-2", "provider": "runway", "connected": has_runway})
    
    # 4. Image
    has_midjourney = bool(image_keys.get("midjourney"))
    providers["image"].append({"id": "midjourney/v6", "name": "Midjourney v6", "provider": "midjourney", "connected": has_midjourney})
    providers["image"].append({"id": "dall-e-3", "name": "DALL-E 3", "provider": "openai", "connected": has_openai})
    
    # 5. Audio
    has_elevenlabs = bool(audio_keys.get("elevenLabs"))
    providers["audio"].append({"id": "elevenlabs", "name": "ElevenLabs", "provider": "elevenlabs", "connected": has_elevenlabs})
    providers["audio"].append({"id": "whisper-v3", "name": "Whisper v3 (Local)", "provider": "local", "connected": True})
    
    # 6. Music
    has_suno = bool(music_keys.get("suno"))
    has_udio = bool(music_keys.get("udio"))
    providers["music"].append({"id": "suno-v3", "name": "Suno v3", "provider": "suno", "connected": has_suno})
    providers["music"].append({"id": "udio", "name": "Udio", "provider": "udio", "connected": has_udio})
    
    return providers


@router.get("/status", dependencies=[Depends(verify_authenticated)])
@router.get("/system/status", dependencies=[Depends(verify_authenticated)])
async def get_system_status():
    """High-level system status and resource metrics."""
    import psutil
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    
    return {
        "status": "active",
        "environment": settings.APP_ENV,
        "resources": {
            "cpu": f"{cpu}%",
            "memory": f"{mem}%",
        },
        "services": {
            "ace": "online" if services.ace else "offline",
            "vault": "mounted" if services.vault else "unmounted",
            "orchestrator": "ready" if services.orchestrator else "init"
        }
    }

@router.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Prometheus-compatible metrics endpoint."""
    from prometheus_client import generate_latest, REGISTRY, CONTENT_TYPE_LATEST
    return PlainTextResponse(
        content=generate_latest(REGISTRY).decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST
    )

@router.get("/audit/ledger", dependencies=[Depends(verify_authenticated)])
async def get_audit_ledger(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    from ..security.audit_ledger import read_audit_log
    return await read_audit_log(limit=limit, offset=offset, status=status)

@router.post("/audit/entry", dependencies=[Depends(verify_authenticated)])
async def add_audit_entry(
    request: Request,
    entry: AuditEntry,
    csrf_protect: CsrfProtect = Depends(),
):
    if settings.APP_ENV != "testing":
        await csrf_protect.validate_csrf(request)
    from ..security.audit_ledger import sync_audit_entry
    return await sync_audit_entry(entry)


@router.get("/system/pcl/status", dependencies=[Depends(verify_authenticated)])
async def get_pcl_status():
    """Retrieve detailed PCL engine status, recent opportunities, and cycles."""
    if not services.pcl:
        raise HTTPException(status_code=503, detail="PCL engine not initialized")
    return await services.pcl.get_status()


@router.post("/system/pcl/cycle", dependencies=[Depends(verify_authenticated)])
async def trigger_pcl_cycle(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
):
    """Manually trigger a PCL cognitive cycle immediately."""
    await csrf_protect.validate_csrf(request)
    if not services.pcl:
        raise HTTPException(status_code=503, detail="PCL engine not initialized")
    return await services.pcl.run_cycle()


@router.get("/system/pcl/opportunities", dependencies=[Depends(verify_authenticated)])
async def get_pcl_opportunities(limit: int = 50, actioned: Optional[bool] = None):
    """Retrieve historical PCL opportunities from the database."""
    from sqlmodel import col
    from ..models import PCLOpportunity
    with Session(db_engine) as session:
        query = select(PCLOpportunity)
        if actioned is not None:
            query = query.where(PCLOpportunity.actioned == actioned)
        query = query.order_by(col(PCLOpportunity.detected_at).desc()).limit(limit)
        return session.exec(query).all()
@router.get("/system/recovery-phrase", dependencies=[Depends(verify_authenticated)])
async def get_recovery_phrase(request: Request, csrf_protect: CsrfProtect = Depends()):
    """
    Returns the BIP-39 recovery phrase for the current master key.
    Requires active session and CSRF validation for high-security read.
    """
    # CSRF check for sensitive read
    if settings.APP_ENV != "testing":
        await csrf_protect.validate_csrf(request)

    from ..security.recovery import MasterKeyRecovery
    recovery = MasterKeyRecovery()
    
    # We use the current settings master key to generate the phrase
    phrase = recovery.generate_recovery_phrase(settings.POLYTOPE_MASTER_KEY)
    
    return {
        "status": "SUCCESS",
        "phrase": phrase,
        "instructions": "Store these 24 words in a secure, physical location. They can recover your Sovereign Agent if the master key is lost."
    }
