
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
    providers["llm"].append({"id": "openai", "name": "OpenAI", "provider": "openai", "connected": has_openai})
    
    has_anthropic = bool(llm_keys.get("anthropic") or getattr(settings, "ANTHROPIC_API_KEY", None))
    providers["llm"].append({"id": "anthropic", "name": "Anthropic", "provider": "anthropic", "connected": has_anthropic})
    
    has_google = bool(llm_keys.get("googleCloud") or getattr(settings, "GEMINI_API_KEY", None))
    providers["llm"].append({"id": "googleCloud", "name": "Google Cloud", "provider": "googleCloud", "connected": has_google})
    
    has_groq = bool(llm_keys.get("groq") or getattr(settings, "GROQ_API_KEY", None))
    providers["llm"].append({"id": "groq", "name": "Groq", "provider": "groq", "connected": has_groq})

    has_deepseek = bool(llm_keys.get("deepseek") or getattr(settings, "DEEPSEEK_API_KEY", None))
    providers["llm"].append({"id": "deepseek", "name": "DeepSeek", "provider": "deepseek", "connected": has_deepseek})
    
    has_moonshot = bool(llm_keys.get("kimi"))
    providers["llm"].append({"id": "kimi", "name": "Moonshot", "provider": "kimi", "connected": has_moonshot})

    has_openrouter = bool(llm_keys.get("openrouter"))
    providers["llm"].append({"id": "openrouter", "name": "OpenRouter", "provider": "openrouter", "connected": has_openrouter})

    has_lmstudio = bool(llm_keys.get("lmStudio"))
    providers["llm"].append({"id": "lmStudio", "name": "LM Studio", "provider": "lmStudio", "connected": has_lmstudio})
    
    has_together = bool(llm_keys.get("together"))
    providers["llm"].append({"id": "together", "name": "Together AI", "provider": "together", "connected": has_together})
    
    has_cohere = bool(llm_keys.get("cohere"))
    providers["llm"].append({"id": "cohere", "name": "Cohere", "provider": "cohere", "connected": has_cohere})
    
    has_aws = bool(llm_keys.get("aws"))
    providers["llm"].append({"id": "aws", "name": "AWS Bedrock", "provider": "aws", "connected": has_aws})

    # 3. Video
    has_runway = bool(video_keys.get("runway"))
    providers["video"].append({"id": "runway", "name": "RunwayML", "provider": "runway", "connected": has_runway})
    
    has_luma = bool(video_keys.get("luma"))
    providers["video"].append({"id": "luma", "name": "Luma", "provider": "luma", "connected": has_luma})
    
    has_veo = bool(video_keys.get("veo"))
    providers["video"].append({"id": "veo", "name": "Google Veo", "provider": "veo", "connected": has_veo})
    
    has_genie = bool(video_keys.get("genie"))
    providers["video"].append({"id": "genie", "name": "Google Genie", "provider": "genie", "connected": has_genie})
    
    has_heygen = bool(video_keys.get("heygen"))
    providers["video"].append({"id": "heygen", "name": "HeyGen", "provider": "heygen", "connected": has_heygen})
    
    has_seedance_video = bool(video_keys.get("seedanceVideo"))
    providers["video"].append({"id": "seedanceVideo", "name": "Seedance", "provider": "seedanceVideo", "connected": has_seedance_video})
    
    has_livepeer = bool(video_keys.get("livepeer"))
    providers["video"].append({"id": "livepeer", "name": "Livepeer", "provider": "livepeer", "connected": has_livepeer})

    # 4. Image
    has_midjourney = bool(image_keys.get("midjourney"))
    providers["image"].append({"id": "midjourney", "name": "Midjourney", "provider": "midjourney", "connected": has_midjourney})
    
    has_falAI = bool(image_keys.get("falAI"))
    providers["image"].append({"id": "falAI", "name": "FalAI", "provider": "falAI", "connected": has_falAI})
    
    has_seedance = bool(image_keys.get("seedance"))
    providers["image"].append({"id": "seedance", "name": "Seedance", "provider": "seedance", "connected": has_seedance})
    
    has_googleNanoBanana = bool(image_keys.get("googleNanoBanana"))
    providers["image"].append({"id": "googleNanoBanana", "name": "GoogleNanoBanana", "provider": "googleNanoBanana", "connected": has_googleNanoBanana})
    
    has_openAIDallE = bool(image_keys.get("openAIDallE"))
    providers["image"].append({"id": "openAIDallE", "name": "OpenAIDallE", "provider": "openAIDallE", "connected": has_openAIDallE})
    
    has_adobeFirefly = bool(image_keys.get("adobeFirefly"))
    providers["image"].append({"id": "adobeFirefly", "name": "AdobeFirefly", "provider": "adobeFirefly", "connected": has_adobeFirefly})
    
    # 5. Audio
    has_elevenlabs = bool(audio_keys.get("elevenLabs"))
    providers["audio"].append({"id": "elevenLabs", "name": "ElevenLabs", "provider": "elevenLabs", "connected": has_elevenlabs})
    
    has_elevenlabsAgents = bool(audio_keys.get("elevenLabsAgents"))
    providers["audio"].append({"id": "elevenLabsAgents", "name": "ElevenLabsAgents", "provider": "elevenLabsAgents", "connected": has_elevenlabsAgents})
    
    has_retellAI = bool(audio_keys.get("retellAI"))
    providers["audio"].append({"id": "retellAI", "name": "RetellAI", "provider": "retellAI", "connected": has_retellAI})
    
    has_openAIRealtime = bool(audio_keys.get("openAIRealtime"))
    providers["audio"].append({"id": "openAIRealtime", "name": "OpenAIRealtime", "provider": "openAIRealtime", "connected": has_openAIRealtime})
    
    has_inworldAI = bool(audio_keys.get("inworldAI"))
    providers["audio"].append({"id": "inworldAI", "name": "InworldAI", "provider": "inworldAI", "connected": has_inworldAI})
    
    providers["audio"].append({"id": "localWhisper", "name": "Whisper (Local)", "provider": "local", "connected": True})
    
    # 6. Music
    has_elevenLabsMusic = bool(music_keys.get("elevenLabsMusic"))
    providers["music"].append({"id": "elevenLabsMusic", "name": "ElevenLabsMusic", "provider": "elevenLabsMusic", "connected": has_elevenLabsMusic})
    
    has_suno = bool(music_keys.get("suno"))
    providers["music"].append({"id": "suno", "name": "Suno", "provider": "suno", "connected": has_suno})
    
    has_soundverse = bool(music_keys.get("soundverse"))
    providers["music"].append({"id": "soundverse", "name": "Soundverse", "provider": "soundverse", "connected": has_soundverse})
    
    has_googleLyria = bool(music_keys.get("googleLyria"))
    providers["music"].append({"id": "googleLyria", "name": "GoogleLyria", "provider": "googleLyria", "connected": has_googleLyria})
    
    has_stableAudio = bool(music_keys.get("stableAudio"))
    providers["music"].append({"id": "stableAudio", "name": "StableAudio", "provider": "stableAudio", "connected": has_stableAudio})
    
    has_udio = bool(music_keys.get("udio"))
    providers["music"].append({"id": "udio", "name": "Udio", "provider": "udio", "connected": has_udio})
    
    return providers


@router.get("/status", dependencies=[Depends(verify_authenticated)])
@router.get("/system/status", dependencies=[Depends(verify_authenticated)])
async def get_system_status():
    """High-level system status and resource metrics."""
    import psutil
    from ..inference.mlx_engine import MLXEngine
    engine = MLXEngine()
    
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    
    return {
        "status": "active",
        "engine_status": "INITIALIZING" if engine.is_loading else "NOMINAL",
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
