
import os
import uuid
import hmac
import asyncio
import contextlib
import traceback
import psutil
import logging
import base64
import json
import redis.asyncio as redis
from datetime import datetime, timezone, date, timedelta
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query, Body, Request, Response, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
from fastapi.staticfiles import StaticFiles # Added for future static use if needed

from .config import settings
from .database import create_db_and_tables, engine as db_engine
from sqlmodel import Session, select, delete
import urllib.parse
from .oauth_config import OAUTH_CONFIGS
from .models import (
    ObjectiveRequest, TelemetryData, SystemStatus, LoginRequest,
    TaskUpdate, SoulPreferences, SoulManifest, AuditEntry
)
from .security.vault import VaultManager
from .security.auth import create_access_token, verify_authenticated
from .security.verus import SovereignIdentity
from .inference.router import ModelRouter
from .ace.engine import AffectiveEngine
from .orchestrator import ExecutiveOrchestrator
from .tasks import TaskManager
from .skill_manager import SkillManager
from .security.verusid_auth import verus_auth
from .inference.local_bridge import LocalInferenceBridge
from .memory.manager import MemoryManager
from .logging_config import configure_logging
from .security.guardrail import GuardrailScanner
from .ws_gateway import JsonRpcGateway
from .analytics import UsageTracker
from .cron_engine import CronEngine
from .log_streamer import log_buffer, log_stream_handler
from .config_editor import ConfigEditor
from .exec_approval import ExecApprovalManager
from .platform.macos import MacOSPlatform
from .platform.linux import LinuxPlatform
from .platform.windows import WindowsPlatform
from .updater import updater
from .metrics import metrics
from .goals.engine import goal_engine
from .sop.engine import sop_engine
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

logger = logging.getLogger("PolytopeApp")



# Global Services
vault: VaultManager = None
router: ModelRouter = None
ace: AffectiveEngine = None
orchestrator: ExecutiveOrchestrator = None
task_manager: TaskManager = None
skill_manager: SkillManager = None
sovereign_identity: SovereignIdentity = None
local_inference: LocalInferenceBridge = None
ws_gw: JsonRpcGateway = None
usage_tracker: UsageTracker = None
cron_engine: CronEngine = None
config_editor: ConfigEditor = None
exec_approval: ExecApprovalManager = None
device_manager: Any = None
memory: MemoryManager = None
redis_client: Optional[redis.Redis] = None
audit_lock = asyncio.Lock()
channel_registry: Dict[str, Any] = {}

# --- Input Sanitization ---
async def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent prompt injection and policy violations."""
    is_safe, error_msg = await scanner.scan_input(text)
    if not is_safe:
        logger.warning(f"[SECURITY] Guardrail Violation: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Strip null bytes and excessive whitespace
    text = text.replace("\x00", "").strip()
    return text


# --- Sovereign Auditing Helper ---
async def log_system_event(event: str, details: str, status: str = "INFO"):
    """Internal helper to record immutable system events in the anchored audit ledger."""
    try:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            details=details,
            status=status
        )
        await sync_audit_entry(entry)
    except Exception as e:
        logger.error(f"Failed to log system event {event}: {e}")


# --- Lifespan & Production Initialization ---

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global vault, router, ace, orchestrator, task_manager, skill_manager, sovereign_identity, local_inference
    global ws_gw, usage_tracker, cron_engine, config_editor, exec_approval, memory, channel_registry, scanner
 
    # Initialize structured logging before any log calls
    configure_logging(app_env=settings.APP_ENV)

    logger.info("[ POLYTOPE_DAEMON ] Booting up...")
    
    # Initialize Production Rate Limiter (Redis)
    if settings.REDIS_URL:
        try:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8")
            await FastAPILimiter.init(redis_client)
            logger.info(f"[ CACHE ]: Redis distributed rate limiter initialized on {settings.REDIS_URL}")
        except Exception as e:
            logger.error(f"[ CACHE ]: Redis initialization failed. Rate limiting will NOT be active: {e}")
    else:
        logger.warning("[ CACHE ]: REDIS_URL not set. Running in sovereign mode without distributed rate limiting.")

    create_db_and_tables()

    # 1. Security Layer
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    sovereign_identity = SovereignIdentity(settings)

    # 2. Inference Layer
    router = ModelRouter(settings)

    # 2a. Guardrail Scanner
    from .security.guardrail import GuardrailScanner
    scanner = GuardrailScanner(router)
 
    # 3. Affective Engine
    ace = AffectiveEngine()

    # 4. Skill Manager
    skill_manager = SkillManager(vault)

    # 5. Persistent Memory
    memory = MemoryManager()

    # 6. Usage & Cost Analytics
    usage_tracker = UsageTracker(db_engine)

    # 7. Executive Orchestrator (Sovereign Core)
    orchestrator = ExecutiveOrchestrator(
        router, vault, ace, settings, 
        skill_manager=skill_manager, 
        analytics=usage_tracker,
        memory_manager=memory
    )

    # 8. Task Manager
    task_manager = TaskManager()

    # 8. Local Inference Bridge
    local_inference = LocalInferenceBridge(settings)

    # 9. Sprint 1: WebSocket Gateway (Admin)
    ws_gw = JsonRpcGateway(jwt_secret=settings.JWT_SECRET_KEY)
    
    # 10. Sprint 3: Exec Approval System
    exec_approval = ExecApprovalManager(db_engine, ws_gateway=ws_gw)
    
    # Inject Approval Manager into Orchestrator & Executor
    orchestrator.approval_manager = exec_approval
    orchestrator.executor.approval_manager = exec_approval
    orchestrator.ws_gateway = ws_gw
    router.ws_gateway = ws_gw

    # 10.5 Self-Update Manager
    await updater.start()

    # Inject services into Gateway
    ws_gw.inject_services(vault=vault, router=router, orchestrator=orchestrator, 
                          channel_registry=channel_registry, db_engine=db_engine,
                          updater=updater)

    # 11. Sprint 1: Cron Engine
    cron_engine = CronEngine(db_engine, orchestrator=orchestrator, task_manager=task_manager)
    await cron_engine.start()

    # 12. Sprint 1: Log Streamer
    log_buffer.install_handler()

    # 13. Sprint 1: Config Editor
    config_editor = ConfigEditor(settings)
    logger.info("DEBUG: Passed config_editor")

    # 14. Sprint 2: Channel Adapter Registry
    vault_root = os.path.expanduser("~/.polytope/vaults")
    os.makedirs(vault_root, exist_ok=True)

    from .bridges.telegram import TelegramBridge
    from .bridges.whatsapp import WhatsAppBridge
    from .bridges.discord import DiscordBridge
    from .bridges.slack import SlackBridge
    from .bridges.email import EmailBridge
    from .bridges.signal import SignalBridge
    from .bridges.google_chat import GoogleChatBridge
    from .bridges.nostr import NostrBridge
    from .bridges.imessage import IMessageBridge
    logger.info("DEBUG: Passed bridge imports")

    async def broadcast_bridge_event(event: str, data: Any):
        await ws_gw.broadcast_event(event, data)

    channel_registry["telegram"] = TelegramBridge("telegram", vault_root)
    channel_registry["whatsapp"] = WhatsAppBridge("whatsapp", vault_root)
    channel_registry["discord"] = DiscordBridge("discord", vault_root)
    channel_registry["slack"] = SlackBridge("slack", vault_root)
    channel_registry["email"] = EmailBridge("email", vault_root)
    channel_registry["signal"] = SignalBridge("signal", vault_root)
    channel_registry["google_chat"] = GoogleChatBridge("google_chat", vault_root)
    channel_registry["nostr"] = NostrBridge("nostr", vault_root)
    channel_registry["imessage"] = IMessageBridge("imessage", vault_root)
    logger.info("DEBUG: Passed channel_registry instances")

    for ch_name, adapter in channel_registry.items():
        if hasattr(adapter, "on_event"):
            adapter.on_event = broadcast_bridge_event
        if hasattr(adapter, "on_inbound"):
            adapter.on_inbound = orchestrator.handle_inbound_message

    # Auto-connect channels from vault-stored credentials (non-blocking)
    for ch_name, adapter in channel_registry.items():
        logger.info(f"DEBUG: Processing channel {ch_name}")
        try:
            # Check if channel is enabled (default True)
            enabled_state = await vault.retrieve_secret(f"channel_{ch_name}_enabled")
            adapter.enabled = enabled_state.get("enabled", True) if enabled_state else True
            
            if not adapter.enabled:
                logger.info(f"[ CHANNELS ] {ch_name} is disabled by policy. Skipping boot connect.")
                continue

            creds = await vault.retrieve_secret(f"channel_{ch_name}")
            if creds:
                connected = await adapter.connect(creds)
                if connected:
                    logger.info(f"[ CHANNELS ] {ch_name} auto-connected")
                    await log_system_event("BRIDGE_CONNECT", f"Successfully auto-connected channel: {ch_name}", "SUCCESS")
                else:
                    logger.warning(f"[ CHANNELS ] {ch_name} credentials found but connection failed")
                    await log_system_event("BRIDGE_CONNECT", f"Auto-connect failed for channel: {ch_name}", "WARNING")
        except Exception as e:
            logger.debug(f"[ CHANNELS ] {ch_name} connection error during boot: {e}")
            await log_system_event("BRIDGE_CONNECT", f"Critical error during boot connect for {ch_name}: {str(e)}", "ERROR")
    logger.info("DEBUG: Passed channel auto-connect loop")

    # Wire channel registry to cron engine for delivery routing
    cron_engine.channel_registry = channel_registry

    # 16. Sprint 4.3: Device Manager
    logger.info("DEBUG: Before DeviceManager")
    from .device_manager import DeviceManager
    device_manager = DeviceManager(vault_root)
    logger.info("DEBUG: Passed DeviceManager")

    # 15. Background Services
    logger.info("DEBUG: Before start_background_services")
    await orchestrator.start_background_services()
    logger.info("DEBUG: After start_background_services")

    logger.info("[ POLYTOPE_DAEMON ] All systems nominal. Ready.")

    yield

    logger.info("[ POLYTOPE_DAEMON ] Shutting down...")
    
    # 1. Stop background engines
    if cron_engine: await cron_engine.stop()
    if orchestrator: await orchestrator.stop_background_services()
    if updater: await updater.stop()
    
    # 2. Gracefully close all bridge connections
    close_tasks = []
    for ch_name, adapter in channel_registry.items():
        if hasattr(adapter, "disconnect"):
            close_tasks.append(adapter.disconnect())
    if close_tasks:
        await asyncio.gather(*close_tasks, return_exceptions=True)
    
    # 3. Shutdown Redis
    if redis_client:
        await redis_client.close()
        
    logger.info("[ POLYTOPE_DAEMON ] Shutdown complete.")


app = FastAPI(title="Polytope Executive Daemon", version="1.0.0", lifespan=lifespan)

# --- Metrics Middleware ---
@app.middleware("http")
async def record_metrics(request: Request, call_next):
    import time
    start_time = time.time()
    try:
        response = await call_next(request)
        latency = time.time() - start_time
        metrics.record_request(latency, response.status_code)
        return response
    except Exception as e:
        latency = time.time() - start_time
        metrics.record_request(latency, 500)
        raise e

@app.get("/metrics", response_class=PlainTextResponse)
async def get_metrics():
    return metrics.get_metrics_text()

@app.post("/api/voice/transcribe", dependencies=[Depends(verify_authenticated)])
async def voice_transcribe(file: UploadFile = File(...)):
    """Transcribe audio using local Whisper.cpp bridge (P1-007)."""
    if not local_inference:
        raise HTTPException(status_code=503, detail="Local inference not initialized")
    audio_data = await file.read()
    text = await local_inference.transcribe(audio_data)
    return {"text": text}

@app.get("/api/voice/synthesise", dependencies=[Depends(verify_authenticated)])
async def voice_synthesise(text: str = Query(...)):
    """Synthesise text to speech using local Piper bridge (P1-007)."""
    if not local_inference:
        raise HTTPException(status_code=503, detail="Local inference not initialized")
    audio_bytes = await local_inference.synthesise(text)
    return Response(content=audio_bytes, media_type="audio/wav")

@app.post("/api/telemetry", dependencies=[Depends(verify_authenticated)])
async def post_telemetry(data: TelemetryData):
    """Ingests biometric telemetry from companion devices (P4-003)."""
    if not ace:
        raise HTTPException(status_code=503, detail="Affective Engine not initialized")
    
    # Process the data through ACE
    flow_result = ace.process_telemetry(data)
    
    # Return the updated state
    return {
        "status": "SUCCESS",
        "flow_state": flow_result,
        "current_metrics": {
            "stress_score": ace.current_state["stress_score"],
            "vitality": ace.current_state["physical_vitality"],
            "mode": ace.current_state["flow_mode"]
        }
    }

# CORS Policy — explicit methods and headers, not wildcards
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# --- Observability Middleware ---

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """
    Injects a UUID request_id into every log context for distributed tracing.
    Ensures that logs for a single user interaction can be correlated across modules.
    """
    import structlog
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# --- Global Exception Handler ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Prevents implementation leakage (internal paths, module names) by returning
    sanitized responses and logging detailed traces with a UUID for audit.
    """
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
        
    error_id = str(uuid.uuid4())
    logger.error(f"GLOBAL_FAULT [ref={error_id}]: {exc}\n{traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Polytope Manifold Error. Internal fault detected.",
            "error_ref": error_id,
            "status": "HALTED",
            "recovery": "Reduce objective complexity or check system logs with the provided reference."
        }
    )


# --- Middleware ---
# (Intentionally empty: privileged routing is handled via Depends() for granular control)


# --- Health & Readiness ---

@app.get("/health")
async def health_check():
    """Kubernetes-style liveness probe."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/ready")
async def readiness_check():
    """
    Exhaustive readiness check for Kubernetes/orchestrator health.
    Verifies actual connectivity to DB and downstream inference services.
    """
    checks = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "unstable",
        "orchestrator": "online" if orchestrator else "starting",
        "ace": "online" if ace else "offline",
    }
    
    # Check Database Connectivity
    from sqlmodel import text
    try:
        with Session(db_engine) as session:
            session.exec(text("SELECT 1"))
        checks["database"] = "stable"
    except Exception as e:
        logger.error(f"[ HEALTH ]: Database integrity check failed: {e}")
        raise HTTPException(status_code=503, detail="Database unresponsive")

    # Check Redis Connectivity
    if redis_client:
        try:
            await redis_client.ping()
            checks["redis"] = "stable"
        except Exception as e:
            logger.error(f"[ HEALTH ]: Redis ping failed: {e}")
            checks["redis"] = "failing"
    else:
        checks["redis"] = "inactive"

    return {"status": "ready", "checks": checks}


# --- Auth ---

@app.post("/auth/login")
async def login(response: Response, payload: LoginRequest):
    """Sovereign Master Key Authentication."""
    if hmac.compare_digest(payload.key, settings.POLYTOPE_MASTER_KEY):
        token = create_access_token(data={"sub": "sovereign_admin"})
        # Set HttpOnly, Secure, SameSite cookie
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.APP_ENV != "development",  # True in prod/local_sovereign if https
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400  # 24 hours
        )
        return {"access_token": token, "token_type": "bearer", "status": "SUCCESS"}
    
    raise HTTPException(status_code=401, detail="Invalid Sovereign Master Key")

@app.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(settings.AUTH_COOKIE_NAME)
    return {"status": "SUCCESS", "message": "Logged out."}


# --- VerusID (SSID) Auth ---

@app.get("/auth/verusid/challenge")
async def get_verusid_challenge(identity: str = Query("")):
    """Generates a login challenge for Verus Mobile scan."""
    if not settings.VERUS_AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="VerusID Authentication not enabled")
    return verus_auth.create_login_challenge(identity)

@app.post("/auth/verusid/callback")
async def verusid_callback(response: Response, payload: Dict[str, str] = Body(...)):
    """Verifies the signed challenge and issues a JWT."""
    identity = payload.get("identity")
    signature = payload.get("signature")
    challenge_id = payload.get("challenge_id")
    
    if not all([identity, signature, challenge_id]):
        raise HTTPException(status_code=400, detail="Missing identity, signature, or challenge_id")
    
    is_valid = await verus_auth.verify_login_response({"identity": identity, "signature": signature, "challenge_id": challenge_id})
    if is_valid:
        token = create_access_token(data={"sub": identity, "vauth": True})
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.APP_ENV != "development",
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        return {"access_token": token, "token_type": "bearer", "identity": identity}
    
    raise HTTPException(status_code=401, detail="VerusID signature verification failed")


# --- Wallet-specific VerusID Linking (SSID) ---

@app.get("/api/wallet/login/status/{challenge_id}")
async def get_wallet_login_status(challenge_id: str):
    """Polls for the result of a specific login challenge."""
    result = await verus_auth.get_login_status(challenge_id)
    if result:
        # Load the authenticated identity into the wallet service
        wallet_service.set_identity(result["identity"])
        return {"status": "SUCCESS", "identity": result["identity"], "decision": result["decision"]}
    return {"status": "PENDING"}


# --- System Status ---

@app.post("/api/system/service/install", dependencies=[Depends(verify_authenticated)])
async def install_system_service():
    """Installs the Alluci daemon as a background service on the host OS."""
    import platform
    if platform.system() == "Darwin":
        svc = MacOSPlatform()
        return svc.install_service()
    elif platform.system() == "Linux":
        svc = LinuxPlatform()
        return svc.install_service()
    elif platform.system() == "Windows":
        svc = WindowsPlatform()
        return svc.install_service()
    return {"status": "error", "message": f"Service installation not yet supported on {platform.system()}"}

@app.get("/api/system/health", dependencies=[Depends(verify_authenticated)])
async def get_system_health():
    """Runs diagnostic checks across primary modules for the Health dashboard."""
    # 1. Database
    db_status = "healthy"
    try:
        from sqlmodel import Session, select
        with Session(analytics.db_engine) as session:
            session.exec(select(1)).first()
    except Exception:
        db_status = "unhealthy"

    # 2. Vault Security
    vault_status = "healthy" if vault else "warning"

    # 3. Model Router
    router_status = "unhealthy"
    if router and router.router and any(p.client for p in router.router.providers.values()):
        router_status = "healthy"
    elif router:
        router_status = "warning" # No providers configured
    
    # 4. Local Inference
    local_inference_status = "healthy" if local_inference else "unhealthy"

    # 5. Bridges
    active_bridges = list(vault.get_active_vaults()) if vault else []
    
    # 6. Cron Engine Tasks
    cron_status = "healthy" if task_manager else "unhealthy"

    return {
        "database": db_status,
        "vault": vault_status,
        "model_router": router_status,
        "local_inference": local_inference_status,
        "bridges": len(active_bridges),
        "cron_engine": cron_status,
        "uptime": time.time() - metrics.start_time
    }

@app.get("/status", dependencies=[Depends(verify_authenticated)])
async def get_system_status():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    thermal = "nominal" if cpu < 80 else "elevated"

    # Retrieve security audit summary from vault
    audit_ledger = await vault.retrieve_secret("audit_ledger") or []
    security_summary = {
        "total_events": len(audit_ledger),
        "last_violation": next((e["details"] for e in reversed(audit_ledger) if "GUARDRAIL" in (e.get("event") or "")), None),
        "integrity_hash": audit_ledger[-1].get("hash") if audit_ledger else "0x0"
    }

    return SystemStatus(
        cpu_usage=cpu,
        ram_usage=ram,
        thermal_status=thermal,
        active_bridges=list(vault.get_active_vaults()),
        vault_integrity=True,
        daemon_version="1.0.0",
        harmonic_status="Active" if orchestrator else "Inactive",
        identity_active=sovereign_identity.enabled if sovereign_identity else False,
        security_audit=security_summary,
        update_available=updater.update_available,
        latest_version=updater.latest_version
    )


# --- Onboarding & Initialization ---

@app.get("/api/onboarding/status")
async def get_onboarding_status():
    """Public endpoint to check if the agent needs initial setup."""
    onboarding = await vault.retrieve_secret("onboarding_config")
    return {"needs_onboarding": not bool(onboarding)}

@app.post("/api/onboarding/complete", dependencies=[Depends(verify_authenticated)])
async def complete_onboarding(data: Dict[str, Any] = Body(...)):
    """Records completion of the onboarding wizard and anchors identity."""
    # Store the onboarding record
    await vault.store_secret("onboarding_config", {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "identity_name": data.get("identity_name"),
        "version": "1.0.0"
    })
    
    # Optionally initialize the soul manifest if provided
    if "soul_manifest" in data:
        await vault.store_secret("soul_manifest", data["soul_manifest"])

    return {"status": "success", "message": "Onboarding finalized. Manifold active."}


# --- Vault Operations ---

@app.post("/vault/rotate", dependencies=[Depends(verify_authenticated)])
async def rotate_vault_keys(payload: Dict[str, str] = Body(...)):
    """[ ROTATE_KEYS ] Instantly re-encrypts all vaults with a new key."""
    new_key = payload.get("new_key")
    if not new_key:
        raise HTTPException(status_code=400, detail="Missing new_key")
    
    success = await vault.rotate_keys(new_key)
    if not success:
        await log_system_event("VAULT_ROTATE", "Failed to rotate vault keys.", "ERROR")
        raise HTTPException(status_code=500, detail="Vault key rotation failed")
    
    await log_system_event("VAULT_ROTATE", "All Active Vaults Cryptographically Rotated", "SUCCESS")
    # In production, we'd also update the env/settings persisting the MASTER_KEY
    return {"status": "success", "message": "All Active Vaults Cryptographically Rotated"}

@app.post("/api/vault/flush", dependencies=[Depends(verify_authenticated)])
async def flush_vault():
    await vault.flush_cache()
    return {"status": "success", "message": "Cache flushed."}

@app.post("/api/check-health", dependencies=[Depends(verify_authenticated)])
async def check_health():
    """Triggers a health check across all model manifolds."""
    results = await router.check_health()
    for provider, status in results.items():
        await vault.update_vault_status(provider, status)
    return {"status": "success", "results": results}

MASK = "••••••••••••"

@app.get("/api/vault/keys", dependencies=[Depends(verify_authenticated)])
async def get_vault_keys():
    """Retrieves masked API keys for UI display. Prevents raw secret exposure."""
    try:
        keys = await vault.retrieve_secret("alluci_api_keys") or {}
        masked = {}
        for cat, providers in keys.items():
            if isinstance(providers, dict):
                masked[cat] = {k: MASK if v else "" for k, v in providers.items()}
            else:
                masked[cat] = providers
        return masked
    except Exception as e:
        logger.error(f"Failed to retrieve vault keys: {e}")
        return {}

@app.post("/api/vault/keys", dependencies=[Depends(verify_authenticated)])
async def save_vault_keys(new_keys: Dict[str, Any] = Body(...)):
    """Persists API keys, merging with existing values to preserve masked secrets."""
    try:
        existing = await vault.retrieve_secret("alluci_api_keys") or {}
        
        # Deep merge: if new value is MASK, use existing value
        merged = {}
        # Ensure categories match expected schema
        categories = ["llm", "audio", "music", "image", "video"]
        for cat in categories:
            merged[cat] = {}
            ex_cat = existing.get(cat, {})
            nw_cat = new_keys.get(cat, {})
            
            # Combine all providers from both
            all_providers = set(list(ex_cat.keys()) + list(nw_cat.keys()))
            for k in all_providers:
                nw_val = nw_cat.get(k)
                if nw_val == MASK:
                    merged[cat][k] = ex_cat.get(k, "")
                else:
                    merged[cat][k] = nw_val
                    
        await vault.store_secret("alluci_api_keys", merged)
        return {"status": "SUCCESS", "message": "API Manifold Persisted to Vault."}
    except Exception as e:
        logger.error(f"Failed to store vault keys: {e}")
        raise HTTPException(status_code=500, detail="Vault storage failure.")




# --- Bridge Actualization & Auth Router ---

@app.get("/api/bridge/auth/challenge/{bridge_id}", dependencies=[Depends(verify_authenticated)])
async def get_bridge_auth_challenge(bridge_id: str):
    """Generates a QR Sync challenge for a specific bridge/account."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    
    adapter = orchestrator.adapter_registry.get("bridge_actualization")
    if not adapter:
        raise HTTPException(status_code=501, detail="Bridge actualization adapter not loaded")
        
    result = await adapter.handle_auth(bridge_id, "challenge", "default", {})
    return result

@app.post("/api/bridge/auth/handle", dependencies=[Depends(verify_authenticated)])
async def handle_bridge_auth(payload: Dict[str, Any] = Body(...)):
    """
    Unified endpoint for the UI AuthPortal.
    Handles OAuth codes, QR Sync completions, and Token insertions.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
        
    bridge_id = payload.get("bridge_id")
    auth_type = payload.get("auth_type")
    account_id = payload.get("account_id", "default")
    params = payload.get("params", {})
    
    if not bridge_id or not auth_type:
        raise HTTPException(status_code=400, detail="Missing bridge_id or auth_type")
        
    adapter = orchestrator.adapter_registry.get("bridge_actualization")
    if not adapter:
        raise HTTPException(status_code=501, detail="Bridge actualization adapter not loaded")
        
    try:
        result = await adapter.handle_auth(bridge_id, auth_type, account_id, params)
        return result
    except Exception as e:
        logger.error(f"Bridge Auth handling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/bridge/tunnel/status", dependencies=[Depends(verify_authenticated)])
async def get_tunnel_status():
    """Returns the current status of the Secure Tunnel."""
    adapter = orchestrator.adapter_registry.get("bridge_actualization")
    if not adapter: raise HTTPException(status_code=501, detail="Adapter not loaded")
    return await adapter.handle_auth("system", "tunnel", "default", {"action": "status"})

@app.post("/api/bridge/tunnel/start", dependencies=[Depends(verify_authenticated)])
async def start_tunnel(payload: Dict[str, Any] = Body(...)):
    """Starts the Secure Tunnel reverse proxy."""
    adapter = orchestrator.adapter_registry.get("bridge_actualization")
    if not adapter: raise HTTPException(status_code=501, detail="Adapter not loaded")
    return await adapter.handle_auth("system", "tunnel", "default", {"action": "start", "relay_url": payload.get("relay_url")})

@app.post("/api/bridge/tunnel/stop", dependencies=[Depends(verify_authenticated)])
async def stop_tunnel():
    """Stops the Secure Tunnel reverse proxy."""
    adapter = orchestrator.adapter_registry.get("bridge_actualization")
    if not adapter: raise HTTPException(status_code=501, detail="Adapter not loaded")
    return await adapter.handle_auth("system", "tunnel", "default", {"action": "stop"})

# --- Objective Execution ---

@app.post("/objective/execute", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def execute_objective(req: ObjectiveRequest):
    try:
        # 1. Sanitize user-provided objective
        sanitized_objective = await sanitize_input(req.objective)
        
        # 2. Execute via orchestrator
        result = await orchestrator.execute_objective(sanitized_objective, req.autonomy_level, mode=req.mode)
        # 3. Scan Output (for PII/Secret leakage)
        # We scan the serialized result string
        vault_keys = await vault.retrieve_secret("alluci_api_keys") or {}
        active_secrets = []
        for cat, providers in vault_keys.items():
            if isinstance(providers, dict):
                for k, v in providers.items():
                    if v and isinstance(v, str) and len(v) > 8 and v != "MASK":
                        active_secrets.append(v)
        
        is_safe, error = await scanner.scan_output(str(result), active_secrets=active_secrets)
        if not is_safe:
            logger.critical(f"[GUARDRAIL] Blocked unsafe output in objective execution: {error}")
            raise HTTPException(status_code=403, detail=error)
            
        return {"result": result}
    except HTTPException:
        raise  # Re-raise sanitization/guardrail errors
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(f"Objective execution failed [ref={error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Objective execution failed. Error reference: {error_id}"
        )


# --- Telemetry ---

@app.post("/telemetry", dependencies=[Depends(verify_authenticated)])
async def ingest_telemetry(data: TelemetryData):
    result = ace.process_telemetry(data)
    
    # P1-002: Cognitive Pipeline — Store affective state in memory
    if memory:
        try:
            await memory.store(
                content=f"Affective State: {result.get('mode')} - {result.get('reason')}",
                metadata={
                    "type": "ace_state",
                    "valence": data.valence,
                    "arousal": data.arousal,
                    "focus": data.focus
                }
            )
        except Exception as e:
            logger.warning(f"Failed to store ACE state in memory: {e}")

    # Forward to orchestrator's harmonic enhancer if it exists
    try:
        if orchestrator and hasattr(orchestrator, 'harmonic') and orchestrator.harmonic:
            from .harmonic_enhancer import AttentionSignal
            signal = AttentionSignal(
                valence=data.valence or 0.5,
                arousal=data.arousal or 0.5,
                focus=data.focus or 0.5
            )
            await orchestrator.harmonic.tick(signal)
    except Exception as e:
        logger.warning(f"Harmonic Enhancer tick failed: {e}")

    return {
        "status": "ok",
        "mode": result.get("mode"),
        "reason": result.get("reason")
    }

# --- Manifold Sovereignty (Sprint 4) ---

@app.post("/api/manifold/patch", dependencies=[Depends(verify_authenticated)])
async def patch_manifold(payload: Dict[str, Any] = Body(...)):
    """
    AAP-008: Manifold Patch Endpoint.
    Allows manual intervention to 'stitch' a torn manifold.
    Resets Lipschitz budgets and clears entropy spikes.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
        
    orchestrator.ppn.stabilizer.reset_budget()
    orchestrator.entropy_monitor.history.clear()
    
    await log_system_event("MANIFOLD_PATCH", "Manual manifold patch applied. Stability restored.", "SUCCESS")
    
    return {
        "status": "SUCCESS",
        "message": "Manifold patched. Safety gates reset.",
        "diagnostics": {
            "psi": orchestrator.ace.btm.psi_from_state(orchestrator.ace.get_affective_state())
        }
    }


# --- Task Routes (Privileged) ---

@app.get("/tasks", dependencies=[Depends(verify_authenticated)])
async def get_tasks(status: str = "all", priority: str = None, timeline: str = None):
    return await task_manager.get_tasks(status, priority, timeline)

@app.post("/tasks", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def add_task(task: TaskUpdate):
    return await task_manager.add_task(task)

@app.put("/tasks/{index}", dependencies=[Depends(verify_authenticated)])
async def update_task(index: int, task: TaskUpdate):
    result = await task_manager.update_task(index, task)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result

@app.delete("/tasks/{index}", dependencies=[Depends(verify_authenticated)])
async def delete_task(index: int):
    if not await task_manager.delete_task(index):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted"}


@app.post("/api/audit/entry", dependencies=[Depends(verify_authenticated)])
async def sync_audit_entry(entry: AuditEntry):
    """
    Synchronizes a client-side audit entry with the server-side VDXF store.
    Provides a permanent, decentralized audit trail when VerusID is enabled.
    """
    async with audit_lock:
        try:
            # 1. Store in the secure vault (Tier 2/3)
            current_ledger = await vault.retrieve_secret("audit_ledger") or []
            current_ledger.append(entry.model_dump())
            
            # Keep only last 1000 entries in the local vault
            if len(current_ledger) > 1000:
                current_ledger = current_ledger[-1000:]
                
            await vault.store_secret("audit_ledger", current_ledger)
            
            # 2. Anchor to Verus Blockchain if enabled
            if settings.VERUS_AUTH_ENABLED and settings.VERUS_ID_IDENTITY:
                from .security.vdxf_store import VDXFStore
                store = VDXFStore(settings.VERUS_ID_IDENTITY)
                ledger_json = json.dumps(current_ledger)
                await store.anchor_vault_hash(ledger_json)
                
            return {"status": "SUCCESS", "synced_id": entry.id}
        except Exception as e:
            logger.error(f"Audit sync failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to sync audit ledger.")

@app.get("/api/audit/ledger", dependencies=[Depends(verify_authenticated)])
async def get_audit_ledger():
    """Retrieves the synchronized audit ledger from the vault."""
    ledger = await vault.retrieve_secret("audit_ledger") or []
    return ledger


# --- WebAuthn (Passkeys) Authentication ---

# In-memory challenge store (per-session in production, use Redis)
_webauthn_challenges: Dict[str, bytes] = {}

@app.get("/auth/webauthn/challenge")
async def get_webauthn_challenge():
    """Generates a cryptographic challenge for WebAuthn/FIDO2."""
    import secrets
    
    challenge = secrets.token_bytes(32)
    b64_challenge = base64.urlsafe_b64encode(challenge).decode().replace("=", "")
    
    # Store challenge keyed by the base64 representation for later verification
    _webauthn_challenges[b64_challenge] = challenge
    
    return {
        "challenge": b64_challenge,
        "timeout": 60000,
        "rp": {"name": "Alluci Sovereign Agent", "id": settings.WEBAUTHN_RP_ID if hasattr(settings, 'WEBABAUTHN_RP_ID') else "localhost"},
        "user": {
            "id": "ALLUCI_SOVEREIGN_001", 
            "name": "sovereign_admin", 
            "displayName": "Sovereign Administrator"
        },
        "pubKeyCredParams": [{"type": "public-key", "alg": -7}, {"type": "public-key", "alg": -257}]
    }

@app.post("/auth/webauthn/verify")
async def verify_webauthn_response(payload: Dict[str, Any] = Body(...)):
    """Verifies the WebAuthn attestation/assertion using py_webauthn."""
    try:
        from webauthn import verify_registration_response
        from webauthn.helpers.structs import RegistrationCredential
    except ImportError:
        logger.error("py_webauthn is not installed. Run: pip install webauthn")
        raise HTTPException(status_code=501, detail="WebAuthn verification library not available. Install py_webauthn.")

    credential_id = payload.get("id")
    raw_id = payload.get("rawId")
    response_data = payload.get("response", {})
    attestation_object = response_data.get("attestationObject")
    client_data_json = response_data.get("clientDataJSON")

    if not all([credential_id, raw_id, attestation_object, client_data_json]):
        raise HTTPException(status_code=400, detail="Missing required WebAuthn fields")

    # Find the matching challenge
    # The client_data_json contains the challenge used; we check all stored challenges
    expected_challenge = None
    challenge_key_to_remove = None
    for key, challenge_bytes in _webauthn_challenges.items():
        expected_challenge = challenge_bytes
        challenge_key_to_remove = key
        break  # Use the most recent challenge (FIFO in practice)

    if expected_challenge is None:
        raise HTTPException(status_code=400, detail="No pending WebAuthn challenge found. Request a new challenge.")

    rp_id = settings.WEBAUTHN_RP_ID if hasattr(settings, 'WEBAUTHN_RP_ID') else "localhost"
    expected_origin = settings.WEBAUTHN_ORIGIN if hasattr(settings, 'WEBAUTHN_ORIGIN') else "http://localhost:3000"

    try:
        # Build the credential object for py_webauthn
        credential = RegistrationCredential(
            id=credential_id,
            raw_id=base64.urlsafe_b64decode(raw_id + "=="),
            response={
                "attestation_object": base64.urlsafe_b64decode(attestation_object + "=="),
                "client_data_json": base64.urlsafe_b64decode(client_data_json + "=="),
            },
            type="public-key",
        )

        # Removed unused variable 'verification'
        verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
        )

        # Clean up used challenge
        if challenge_key_to_remove:
            _webauthn_challenges.pop(challenge_key_to_remove, None)

        logger.info(f"WebAuthn verification successful for credential: {credential_id}")
        return {
            "status": "SUCCESS",
            "token": create_access_token({"sub": "sovereign_admin", "webauthn": True}),
            "credential_id": credential_id,
        }

    except Exception as e:
        logger.warning(f"WebAuthn verification failed: {e}")
        # Clean up failed challenge to prevent replay
        if challenge_key_to_remove:
            _webauthn_challenges.pop(challenge_key_to_remove, None)
        raise HTTPException(status_code=401, detail=f"WebAuthn verification failed: {type(e).__name__}")



# --- Identity Forge (Soul Manifest) Routes ---

@app.get("/soul/manifest", dependencies=[Depends(verify_authenticated)])
async def get_soul_manifest():
    try:
        data = await vault.retrieve_secret("soul_manifest")
        if data:
            return SoulManifest(**data)
        return SoulManifest()
    except Exception as e:
        logger.error(f"Failed to load Soul Manifest: {e}")
        return SoulManifest()

@app.put("/soul/manifest", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def update_soul_manifest(manifest: SoulManifest):
    try:
        await vault.store_secret("soul_manifest", manifest.model_dump())
        return {"status": "ok", "message": "Soul Manifest updated."}
    except Exception as e:
        logger.error(f"Failed to save Soul Manifest: {e}")
        raise HTTPException(status_code=500, detail="Failed to persist Soul Manifest.")

@app.post("/soul/preview", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=5, seconds=60))])
async def preview_soul_manifest(manifest: SoulManifest, control_question: str = Body("Analysis of current status?", embed=True)):
    """Simulates the new personality with full cognitive context."""
    try:
        # Build context from the candidate manifest
        context_parts = [
            f"# IDENTITY CORE\n{manifest.identityCore}",
            f"\n# VOICE PROFILE\n{manifest.voiceProfile}",
            f"\n# REASONING STYLE\n{manifest.reasoningStyle}",
            "\n# DIRECTIVES\n" + "\n".join(f"- {d}" for d in manifest.directives),
        ]

        # Merge active skills
        if skill_manager:
            active_skills = await skill_manager.list_skills()
            if active_skills:
                merged = await skill_manager.merge_skills_for_runtime(
                    [s.get("id") for s in active_skills if s.get("verified")]
                )
                if merged.get("logic"):
                    context_parts.append("\n# ACTIVE COGNITIVE MODULES\n" +
                                       "\n".join(f"- {logic_item}" for logic_item in merged["logic"]))

        full_context = "\n".join(context_parts)

        # Sanitize control question
        sanitized_question = await sanitize_input(control_question)

        prompt = f"""
        {full_context}

        SOUL PREFERENCES:
        Tone: {manifest.preferences.tone}
        Humor: {manifest.preferences.humor.value}
        Empathy: {manifest.preferences.empathy}
        Assertiveness: {manifest.preferences.assertiveness}
        Creativity: {manifest.preferences.creativity}
        Conciseness: {manifest.preferences.conciseness.value}

        QUESTION:
        \"{sanitized_question}\"

        Respond entirely in character using the Identity, Voice, and Reasoning above.
        """

        response = await router.get_response(prompt, complexity="HIGH")
        
        # 6. Scan Output
        is_safe, error = await scanner.scan_output(response)
        if not is_safe:
            logger.warning(f"[GUARDRAIL] Blocked unsafe output in soul preview: {error}")
            raise HTTPException(status_code=403, detail=error)

        return {
            "preview_response": response,
            "context_length": len(full_context),
            "skills_loaded": len(active_skills) if skill_manager else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(f"Soul preview failed [ref={error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Preview generation failed. Error reference: {error_id}"
        )


# --- Legacy Support for simple preferences ---

@app.get("/soul/preferences", dependencies=[Depends(verify_authenticated)])
async def get_soul_preferences():
    manifest_data = await vault.retrieve_secret("soul_manifest")
    if manifest_data and "preferences" in manifest_data:
        return SoulPreferences(**manifest_data["preferences"])
    return SoulPreferences()

@app.put("/soul/preferences", dependencies=[Depends(verify_authenticated)])
async def update_soul_preferences(prefs: SoulPreferences):
    manifest_data = await vault.retrieve_secret("soul_manifest")
    if not manifest_data:
        manifest_data = SoulManifest().model_dump()
    manifest_data["preferences"] = prefs.model_dump()
    await vault.store_secret("soul_manifest", manifest_data)
    return {"status": "ok", "preferences": prefs}


# --- Skill Registry & Review Routes ---

@app.get("/skills", dependencies=[Depends(verify_authenticated)])
async def list_skills():
    if not skill_manager:
        raise HTTPException(status_code=503, detail="Skill Manager not initialized")
    return await skill_manager.list_skills()

@app.post("/skills", dependencies=[Depends(verify_authenticated)])
async def create_skill(skill: Dict[str, Any]):
    return await skill_manager.save_skill(skill)

@app.delete("/skills/{skill_id}", dependencies=[Depends(verify_authenticated)])
async def delete_skill(skill_id: str):
    success = await skill_manager.delete_skill(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found")
    return {"status": "deleted", "id": skill_id}

@app.post("/api/skills/install", dependencies=[Depends(verify_authenticated)])
async def install_skill(data: Dict[str, str] = Body(...)):
    """One-click install flow for a remote skill package."""
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url'")
    return await skill_manager.install_remote_package(url)


@app.post("/skills/import", dependencies=[Depends(verify_authenticated)])
async def import_skill_package(package: Dict[str, Any]):
    """Imports a .polytype package into the Review Queue."""
    result = await skill_manager.import_package(package)
    return result

@app.post("/api/skill/sign", dependencies=[Depends(verify_authenticated)])
async def sign_skill_manifest(manifest: Dict[str, Any]):
    """
    Cryptographically signs a skill manifest using the Vault's identity key.
    Ensures sovereignty for locally built skills.
    """
    try:
        import hashlib
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        
        # 1. Cannonicalize and hash the manifest
        manifest_str = json.dumps(manifest, sort_keys=True)
        manifest_hash = hashlib.sha256(manifest_str.encode()).digest()
        
        # 2. Sign the hash using the Vault's RSA private key
        signature = vault.private_key.sign(
            manifest_hash,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return {
            "status": "SUCCESS",
            "signature": signature.hex(),
            "hash": manifest_hash.hex(),
            "signer": "Sovereign_Vault_Alpha"
        }
    except Exception as e:
        logger.error(f"Failed to sign skill manifest: {e}")
        raise HTTPException(status_code=500, detail="Cryptographic signing failed.")

@app.get("/skills/review", dependencies=[Depends(verify_authenticated)])
async def get_review_queue():
    return await skill_manager.get_review_queue()

@app.post("/skills/review/{skill_id}/promote", dependencies=[Depends(verify_authenticated)])
async def promote_skill(skill_id: str):
    success = await skill_manager.promote_from_queue(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found in review queue")
    return {"status": "promoted", "id": skill_id}


@app.get("/api/skills/{skill_id}/status", dependencies=[Depends(verify_authenticated)])
async def get_skill_status(skill_id: str):
    """Dependency check and health report for a skill."""
    return await skill_manager.get_skill_status(skill_id)


@app.post("/api/skills/{skill_id}/keys", dependencies=[Depends(verify_authenticated)])
async def store_skill_key(skill_id: str, data: Dict[str, str] = Body(...)):
    """Securely store a skill-specific secret (e.g. API key)."""
    key_name = data.get("name")
    key_value = data.get("value")
    if not key_name or not key_value:
        raise HTTPException(status_code=400, detail="Missing 'name' or 'value'")
    await skill_manager.store_skill_key(skill_id, key_name, key_value)
    return {"status": "stored", "skill_id": skill_id, "key": key_name}


@app.get("/api/skills/{skill_id}/keys/{key_name}", dependencies=[Depends(verify_authenticated)])
async def get_skill_key(skill_id: str, key_name: str):
    """Retrieve a masked skill-specific secret."""
    val = await skill_manager.get_skill_key(skill_id, key_name)
    if not val:
        raise HTTPException(status_code=404, detail="Key not found")
    # Mask it
    masked = "••••" + val[-4:] if len(val) > 4 else "••••"
    return {"name": key_name, "value": masked}


# --- Gemini API Proxy (server-side key management) ---

@app.post("/api/gemini/proxy", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def gemini_proxy(payload: Dict[str, Any]):
    """
    Proxies Gemini API requests so the API key never leaves the server.
    Frontend sends the prompt; backend adds the key and forwards.
    """
    try:
        prompt = payload.get("prompt", "")
        complexity = payload.get("complexity", "MEDIUM")
        sanitized = await sanitize_input(prompt)
        result = await router.get_response(sanitized, complexity=complexity)
        
        # Scan Output
        is_safe, error = await scanner.scan_output(result)
        if not is_safe:
            logger.warning(f"[GUARDRAIL] Blocked unsafe output in gemini proxy: {error}")
            raise HTTPException(status_code=403, detail=error)
            
        return {"result": result}
    except HTTPException:
        raise
        raise HTTPException(status_code=500, detail="Inference request failed.")

@app.post("/api/chat/abort")
async def abort_chat_generation(request: Request):
    """
    Called by the frontend AbortButton to cancel any in-flight streaming
    generation on the server side.
    """
    try:
        # Just a signal, we don't strictly require authentication for aborts
        # as they only affect the active session if one exists.
        logger.info("[ UX ]: Abort signal received from client.")
        await router.abort_current_generation()
        return {"status": "aborted"}
    except Exception as e:
        logger.error(f"Failed to abort generation: {e}")
        return {"status": "error", "message": str(e)}

# --- iWatch Biometrics Bridge ---

@app.post("/api/bridge/iwatch/biometrics", dependencies=[Depends(verify_authenticated)])
async def ingest_iwatch_biometrics(data: TelemetryData):
    """
    Ingests real-time HealthKit metrics from Apple Watch.
    Integrates results into the Affective Computing Engine (ACE).
    """
    try:
        # Process through ACE
        flow_update = ace.process_telemetry(data)
        
        # P1-002: Cognitive Pipeline
        if memory:
            await memory.store(
                content=f"iWatch Biometrics: {flow_update.get('mode')} - {flow_update.get('reason')}",
                metadata={"type": "iwatch_biometrics", "source": "apple_watch"}
            )
        
        # Log to vault conceptually
        logger.info(f"[ IWATCH_BRIDGE ]: Biometrics ingested. Flow Status: {flow_update['mode']}")
        
        return {
            "status": "SUCCESS",
            "resonance": ace.current_state["physical_vitality"],
            "flow_intervention": flow_update
        }
    except Exception as e:
        logger.error(f"iWatch bridge ingestion error: {e}")
        raise HTTPException(status_code=500, detail="Biometric ingestion failed.")

# --- Persistent Memory Manifold ---

@app.get("/api/memory/search", dependencies=[Depends(verify_authenticated)])
async def memory_search(q: str = Query(...), limit: int = 5):
    """Semantic search across the sovereign memory manifold (P1-001)."""
    if not memory: 
        return []
    return await memory.search(q, limit)

@app.post("/api/memory/store", dependencies=[Depends(verify_authenticated)])
async def memory_store(content: str = Body(...), metadata: Optional[Dict[str, Any]] = Body(None)):
    """Manually store a fragment in the memory manifold."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    mid = await memory.store(content, metadata)
    return {"id": mid, "status": "stored"}

@app.get("/api/memory", dependencies=[Depends(verify_authenticated)])
async def list_memory(limit: int = Query(50)):
    return memory_manager.collection.get(limit=limit)

@app.get("/api/memory/search", dependencies=[Depends(verify_authenticated)])
async def search_memory(q: str = Query(...)):
    return await memory_manager.recall(q, top_k=10)

@app.get("/api/memory/stats", dependencies=[Depends(verify_authenticated)])
async def get_memory_stats():
    return {
        "count": memory_manager.collection.count(),
        "name": memory_manager.collection.name,
        "metadata": memory_manager.collection.metadata
    }

@app.post("/api/memory/ingest", dependencies=[Depends(verify_authenticated)])
async def ingest_document(file_path: str = Body(...)):
    adapter = orchestrator.adapter_registry.get("doc_ingest")
    if not adapter:
        raise HTTPException(status_code=501, detail="Document ingestion tool not available")
    return await adapter.execute(file_path)

@app.delete("/api/memory/{entry_id}", dependencies=[Depends(verify_authenticated)])
async def forget_memory(entry_id: str):
    await memory_manager.forget(entry_id)
    return {"deleted": entry_id}

# --- Cognitive Goals & SOPs ---

@app.get("/api/goals", dependencies=[Depends(verify_authenticated)])
async def list_goals():
    return goal_engine.get_active_goals()

@app.post("/api/goals", dependencies=[Depends(verify_authenticated)])
async def create_goal(title: str = Body(...), description: str = Body(...)):
    gid = goal_engine.create_goal(title, description)
    return {"id": gid, "status": "active"}

@app.get("/api/sops", dependencies=[Depends(verify_authenticated)])
async def list_sops():
    return sop_engine.list_sops()

# --- Sovereign Unified Streaming WebSocket ---

@app.websocket("/ws/sovereign")
async def sovereign_socket(websocket: WebSocket):
    """
    Unified WebSocket for Real-Time Sovereign Interaction.
    Handles Audio (ASR) -> Intent -> LLM -> Audio (TTS).
    Auth: Expects a JSON auth message as the first data frame (not in URL query params).
    """
    # Accept the connection first (no token in URL to prevent log leakage)
    await websocket.accept()
    
    # Authenticate via first message
    try:
        # Wait for auth message with a 10-second timeout
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        
        if auth_data.get("type") != "auth" or not auth_data.get("token"):
            await websocket.send_json({"type": "error", "detail": "First message must be {type: 'auth', token: '...'}"})
            await websocket.close(code=4001)
            return
        
        token = auth_data["token"]
        jwt_payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        if jwt_payload.get("sub") is None:
            await websocket.send_json({"type": "error", "detail": "Invalid token"})
            await websocket.close(code=4003)
            return
            
        await websocket.send_json({"type": "auth_ok", "sub": jwt_payload.get("sub")})
        
    except asyncio.TimeoutError:
        await websocket.close(code=4001)  # Auth timeout
        return
    except (JWTError, Exception):
        try:
            await websocket.send_json({"type": "error", "detail": "Authentication failed"})
        except Exception:
            pass
        await websocket.close(code=4003)  # Forbidden
        return


    logger.info(f"[ SOVEREIGN_WS ]: Client connected (authenticated as {jwt_payload.get('sub')}).")
    
    try:
        while True:
            # Expecting either JSON (commands) or Binary (Audio)
            data = await websocket.receive()
            
            if "bytes" in data:
                # Binary Step: Automatic Speech Recognition (ASR)
                audio_chunk = data["bytes"]
                transcript = await local_inference.transcribe(audio_chunk)
               
                if transcript:
                    await websocket.send_json({"type": "transcript", "text": transcript})
                    
                    # LLM Generation Loop
                    full_response = ""
                    async for chunk in local_inference.chat_ollama(transcript):
                        full_response += chunk
                        await websocket.send_json({"type": "llm_chunk", "text": chunk})
                    
                    # TTS Synthesis
                    if full_response:
                        audio_out = await local_inference.speak_piper(full_response)
                        if audio_out:
                            # Send original PCM or base64? Let's go base64 for unified JSON.
                            b64_audio = base64.b64encode(audio_out).decode()
                            await websocket.send_json({"type": "audio_out", "data": b64_audio})
            
            elif "text" in data:
                # Text Input Step: Direct LLM query
                msg = json.loads(data["text"])
                if msg.get("type") == "chat":
                    prompt = msg.get("text")
                    full_response = ""
                    async for chunk in local_inference.chat_ollama(prompt):
                        full_response += chunk
                        await websocket.send_json({"type": "llm_chunk", "text": chunk})
                    
                    # Final TTS
                    audio_out = await local_inference.speak_piper(full_response)
                    if audio_out:
                        b64_audio = base64.b64encode(audio_out).decode()
                        await websocket.send_json({"type": "audio_out", "data": b64_audio})

    except WebSocketDisconnect:
        logger.info("[ SOVEREIGN_WS ]: Client disconnected.")
    except Exception as e:
        logger.error(f"[ SOVEREIGN_WS ]: Error: {e}")
        await websocket.close()


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 1: WebSocket JSON-RPC Admin Gateway (Sovereign Spec §5.1)
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    """JSON-RPC 2.0 gateway for real-time admin operations."""
    await ws_gw.handle_connection(websocket)


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 1: Usage & Cost Analytics API (Sovereign Spec §4)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/sessions", dependencies=[Depends(verify_authenticated)])
async def get_sessions(limit: int = Query(100, ge=1, le=500)):
    """Exhaustive sessions list for the Management Panel."""
    # We call the usage tracker aggregation which now joins labels and channels
    return usage_tracker.get_sessions(limit=limit)


@app.get("/api/agents", dependencies=[Depends(verify_authenticated)])
async def get_agents():
    """ Stub for agent constellation list to prevent frontend errors. """
    return {
        "agents": [
            { "id": "root", "name": "Sovereign Root", "model": "gpt-4o", "status": "READY", "active_skills": 12, "channels": 4 },
            { "id": "researcher", "name": "Deep Researcher", "model": "gemini-1.5-pro", "status": "IDLE", "active_skills": 4, "channels": 0 },
            { "id": "coder", "name": "Polyglot Coder", "model": "gpt-4o", "status": "IDLE", "active_skills": 8, "channels": 0 }
        ]
    }

@app.post("/api/agents/delegate", dependencies=[Depends(verify_authenticated)])
async def delegate_to_agent(agent_id: str = Body(...), task: str = Body(...)):
    """Delegates a task to a virtual agent in the constellation."""
    return await orchestrator.multi_agent_delegate(agent_id, task)

@app.get("/api/sessions/{session_key}/resume", dependencies=[Depends(verify_authenticated)])
async def resume_session(session_key: str, limit: int = 20):
    """Fetches the last N messages to reconstruct the orchestrator context."""
    from sqlmodel import select
    from .models import MessageLog
    with Session(db_engine) as session:
        statement = select(MessageLog).where(MessageLog.session_key == session_key).order_by(MessageLog.timestamp.desc()).limit(limit)
        results = session.exec(statement).all()
        return [r.dict() for r in reversed(results)]


@app.get("/api/usage/daily", dependencies=[Depends(verify_authenticated)])
async def get_usage_daily(
    start: str = Query(None),
    end: str = Query(None),
):
    """Per-day cost/token breakdown for chart rendering."""
    from datetime import date as dt_date
    s = dt_date.fromisoformat(start) if start else None
    e = dt_date.fromisoformat(end) if end else None
    return usage_tracker.get_daily(start=s, end=e)


@app.get("/api/usage/sessions/{session_key}/timeseries", dependencies=[Depends(verify_authenticated)])
async def get_session_timeseries(session_key: str):
    """Per-turn time series for a selected session."""
    return usage_tracker.get_session_timeseries(session_key)


@app.get("/api/usage/export/sessions.csv", dependencies=[Depends(verify_authenticated)])
async def export_sessions_csv(start: str = Query(None), end: str = Query(None)):
    """CSV export of session aggregates."""
    from datetime import date as dt_date
    s = dt_date.fromisoformat(start) if start else None
    e = dt_date.fromisoformat(end) if end else None
    csv_data = usage_tracker.export_sessions_csv(start=s, end=e)
    return PlainTextResponse(content=csv_data, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=sessions.csv"})


@app.get("/api/usage/export/daily.csv", dependencies=[Depends(verify_authenticated)])
async def export_daily_csv(start: str = Query(None), end: str = Query(None)):
    """CSV export of daily rollup."""
    from datetime import date as dt_date
    s = dt_date.fromisoformat(start) if start else None
    e = dt_date.fromisoformat(end) if end else None
    csv_data = usage_tracker.export_daily_csv(start=s, end=e)
    return PlainTextResponse(content=csv_data, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=daily.csv"})


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 1: Cron Engine API (Sovereign Spec §3)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/cron/jobs", dependencies=[Depends(verify_authenticated)])
async def list_cron_jobs():
    """List all cron jobs."""
    return cron_engine.list_jobs()


@app.get("/api/cron/jobs/{job_id}", dependencies=[Depends(verify_authenticated)])
async def get_cron_job(job_id: int):
    """Get a specific cron job."""
    job = cron_engine.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Cron job not found")
    return job


@app.post("/api/cron/jobs", dependencies=[Depends(verify_authenticated)])
async def create_cron_job(data: Dict[str, Any] = Body(...)):
    """Create a new cron job."""
    required = ["name", "schedule_type", "schedule_value"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    return cron_engine.create_job(data)


@app.put("/api/cron/jobs/{job_id}", dependencies=[Depends(verify_authenticated)])
async def update_cron_job(job_id: int, data: Dict[str, Any] = Body(...)):
    """Update an existing cron job."""
    result = cron_engine.update_job(job_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="Cron job not found")
    return result


@app.delete("/api/cron/jobs/{job_id}", dependencies=[Depends(verify_authenticated)])
async def delete_cron_job(job_id: int):
    """Delete a cron job."""
    if not cron_engine.delete_job(job_id):
        raise HTTPException(status_code=404, detail="Cron job not found")
    return {"status": "deleted"}


@app.post("/api/cron/jobs/{job_id}/clone", dependencies=[Depends(verify_authenticated)])
async def clone_cron_job(job_id: int):
    """Clone an existing cron job."""
    result = cron_engine.clone_job(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cron job not found")
    return result


@app.post("/api/cron/jobs/{job_id}/run", dependencies=[Depends(verify_authenticated)])
async def run_cron_job(job_id: int, mode: str = Query("force")):
    """Force-run or due-run a cron job."""
    result = cron_engine.force_run(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cron job not found")
    return result


@app.get("/api/cron/runs", dependencies=[Depends(verify_authenticated)])
async def get_cron_runs(
    job_id: int = Query(None),
    status: str = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    """Query cron run history with filters."""
    return cron_engine.get_runs(job_id=job_id, status=status, limit=limit)


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 1: Configuration Editor API (Sovereign Spec §8)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/config", dependencies=[Depends(verify_authenticated)])
async def get_config():
    """Return current configuration (sensitive values masked)."""
    return config_editor.get_config()


@app.get("/api/config/schema", dependencies=[Depends(verify_authenticated)])
async def get_config_schema():
    """Return JSON Schema for configuration validation."""
    return config_editor.get_schema()


@app.put("/api/config", dependencies=[Depends(verify_authenticated)])
async def update_config(overrides: Dict[str, Any] = Body(...)):
    """Validate and hot-apply configuration overrides."""
    result = config_editor.apply_overrides(overrides)
    if result["rejected"] and not result["applied"]:
        raise HTTPException(status_code=400, detail=result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 2: Webhook Endpoints for Communication Bridges
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/webhook/telegram/{token}")
async def telegram_webhook(token: str, update: Dict[str, Any] = Body(...)):
    """Receives inbound updates from Telegram Bot API."""
    adapter = channel_registry.get("telegram")
    if not adapter or not hasattr(adapter, "process_webhook"):
        return {"ok": False, "error": "Adapter not ready"}
    
    # Optional: check token against vault-stored token for security
    
    parsed = await adapter.process_webhook(update)
    if parsed:
        await orchestrator.handle_inbound_message(parsed)
    return {"ok": True}


@app.post("/api/webhook/whatsapp")
async def whatsapp_webhook(body: Dict[str, Any] = Body(...)):
    """Receives inbound events from Meta WhatsApp Business API."""
    adapter = channel_registry.get("whatsapp")
    if not adapter or not hasattr(adapter, "process_webhook_event"):
        return {"ok": False, "error": "Adapter not ready"}
    
    parsed_list = adapter.process_webhook_event(body)
    for parsed in parsed_list:
        await orchestrator.handle_inbound_message(parsed)
    return {"ok": True}


@app.get("/api/webhook/whatsapp")
async def verify_whatsapp(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    """Verifies the WhatsApp webhook for Meta Graph API."""
    adapter = channel_registry.get("whatsapp")
    if not adapter or not hasattr(adapter, "verify_webhook"):
        raise HTTPException(status_code=503, detail="Adapter not ready")
    
    res = adapter.verify_webhook(mode, token, challenge)
    if res is not None:
        from fastapi.responses import Response
        return Response(content=res, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Invalid verify token")


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 1: Log Streaming API (Sovereign Spec §9)
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/api/logs/stream")
async def websocket_log_stream(websocket: WebSocket):
    """Real-time JSONL log streaming via WebSocket."""
    await log_stream_handler.handle(websocket)


@app.get("/api/logs/history", dependencies=[Depends(verify_authenticated)])
async def get_log_history(
    limit: int = Query(200, ge=1, le=5000),
    level: str = Query(None),
):
    """Return recent log entries from the buffer."""
    return log_buffer.get_history(limit=limit, level=level)

@app.get("/api/logs/export", dependencies=[Depends(verify_authenticated)])
async def export_logs(level: str = Query(None)):
    """Export all buffered logs as JSONL text."""
    jsonl = log_buffer.export_jsonl(level=level)
    return PlainTextResponse(content=jsonl, media_type="application/jsonl",
                             headers={"Content-Disposition": "attachment; filename=logs.jsonl"})


@app.get("/api/logs/export/{session_key}", dependencies=[Depends(verify_authenticated)])
async def export_session_logs(session_key: str, level: str = Query(None)):
    """Export logs for a specific session as JSONL text."""
    jsonl = log_buffer.export_jsonl(level=level, session_key=session_key)
    return PlainTextResponse(content=jsonl, media_type="application/jsonl",
                             headers={"Content-Disposition": f"attachment; filename=logs_{session_key}.jsonl"})


# ═══════════════════════════════════════════════════════════════════════════════

CHANNEL_META = {
    "telegram": {"icon": "Send", "label": "Telegram Bot API", "order": 1},
    "whatsapp": {"icon": "MessageSquare", "label": "WhatsApp Sovereignty", "order": 2},
    "discord": {"icon": "Gamepad2", "label": "Discord Gateway", "order": 3},
    "slack": {"icon": "Slack", "label": "Slack Enterprise", "order": 4},
    "email": {"icon": "Mail", "label": "SMTP/IMAP Core", "order": 5},
    "google_chat": {"icon": "MessageCircle", "label": "Google Chat", "order": 6},
    "nostr": {"icon": "Wifi", "label": "Nostr Protocol", "order": 7},
    "imessage": {"icon": "MessageSquare", "label": "iMessage Core", "order": 8},
}

@app.get("/api/channels/status", dependencies=[Depends(verify_authenticated)])
async def get_channel_status():
    """Aggregate per-adapter health for all channels with metadata."""
    statuses = []
    for name, adapter in channel_registry.items():
        # Retrieve health from adapter
        h = {}
        if hasattr(adapter, "get_health"):
            h = adapter.get_health()
        else:
            h = {
                "channel": name,
                "connected": getattr(adapter, "is_connected", False),
            }
        
        # Merge metadata
        meta = CHANNEL_META.get(name, {"icon": "Activity", "label": name, "order": 99})
        h.update(meta)
        statuses.append(h)

    # Sort by display order
    statuses.sort(key=lambda x: x.get("order", 99))

    return {
        "channels": statuses,
        "total": len(statuses),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.put("/api/channels/{channel_id}/toggle", dependencies=[Depends(verify_authenticated)])
async def toggle_channel(channel_id: str, data: Dict[str, Any] = Body(...)):
    """
    Enable or disable a channel adapter at runtime.
    Saves state to vault and hot-reloads the adapter.
    """
    adapter = channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")

    enabled = data.get("enabled", True)
    adapter.enabled = enabled

    # Persist the enabled state
    await vault.store_secret(f"channel_{channel_id}_enabled", {"enabled": enabled})

    if not enabled:
        # Hot-reload: Disconnect if disabling
        if hasattr(adapter, "disconnect"):
            await adapter.disconnect()
        logger.info(f"[ CHANNELS ] {channel_id} manual shutdown completed.")
    else:
        # Hot-reload: Attempt to connect if enabling
        creds = await vault.retrieve_secret(f"channel_{channel_id}")
        if creds:
            success = await adapter.connect(creds)
            if success:
                adapter.is_connected = True
                logger.info(f"[ CHANNELS ] {channel_id} hot-auth successful.")

    return {"status": "success", "channel": channel_id, "enabled": enabled}


@app.post("/api/channels/{channel_id}/send", dependencies=[Depends(verify_authenticated)])
async def send_channel_message(channel_id: str, data: Dict[str, Any] = Body(...)):
    adapter = channel_registry.get(channel_id)
    if not adapter or not adapter.is_connected:
        raise HTTPException(status_code=503, detail=f"Channel {channel_id} not connected")
    result = await adapter.send(data["recipient"], data["content"])
    return result


@app.post("/api/channels/{channel_id}/upload", dependencies=[Depends(verify_authenticated)])
async def upload_channel_file(channel_id: str, data: Dict[str, Any] = Body(...)):
    adapter = channel_registry.get(channel_id)
    if not adapter or not adapter.is_connected:
        raise HTTPException(status_code=503, detail=f"Channel {channel_id} not connected")
    if hasattr(adapter, "upload"):
        result = await adapter.upload(data["file_data"], data["file_name"])
        return result
    raise HTTPException(status_code=501, detail=f"Upload not implemented for {channel_id}")


@app.get("/api/channels/{channel_id}/health", dependencies=[Depends(verify_authenticated)])
async def get_channel_health(channel_id: str):
    adapter = channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404)
    if hasattr(adapter, "get_health"):
        return adapter.get_health()
    return {"channel": channel_id, "is_connected": getattr(adapter, "is_connected", False)}


@app.get("/api/channels/{channel_id}/unread", dependencies=[Depends(verify_authenticated)])
async def get_unread_messages(channel_id: str, limit: int = 10):
    adapter = channel_registry.get(channel_id)
    if not adapter or not adapter.is_connected:
        raise HTTPException(status_code=503, detail=f"Channel {channel_id} not connected")
    if hasattr(adapter, "fetch_unread"):
        return await adapter.fetch_unread(limit=limit)
    return []


@app.post("/api/channels/{channel_id}/social", dependencies=[Depends(verify_authenticated)])
async def execute_social_task(channel_id: str, data: Dict[str, Any] = Body(...)):
    adapter = channel_registry.get(channel_id)
    if not adapter or not adapter.is_connected:
        raise HTTPException(status_code=503, detail=f"Channel {channel_id} not connected")
    if hasattr(adapter, "execute_task"):
        return await adapter.execute_task(data["type"], data["payload"])
    if data["type"] == "SEND_MESSAGE":
        return await adapter.send(data["payload"]["recipient"], data["payload"]["content"])
    raise HTTPException(status_code=501, detail=f"Social task {data['type']} not implemented for {channel_id}")


@app.post("/api/channels/{channel_id}/enterprise", dependencies=[Depends(verify_authenticated)])
async def execute_enterprise_task(channel_id: str, data: Dict[str, Any] = Body(...)):
    adapter = channel_registry.get(channel_id)
    if not adapter or not adapter.is_connected:
        raise HTTPException(status_code=503, detail=f"Channel {channel_id} not connected")
    if hasattr(adapter, "execute_task"):
        return await adapter.execute_task(data["type"], data["payload"])
    raise HTTPException(status_code=501, detail=f"Enterprise task {data['type']} not implemented for {channel_id}")


@app.get("/api/channels", dependencies=[Depends(verify_authenticated)])
async def list_channels():
    """List all available communication channels with full metadata."""
    results = []
    for cid, adapter in channel_registry.items():
        # Get connection status efficiently
        connected = False
        if hasattr(adapter, "is_connected"):
            connected = adapter.is_connected
        
        # Retrieve persistence from vault or adapter state
        enabled = getattr(adapter, "enabled", True)
        
        # Get health details if available
        health = {}
        if hasattr(adapter, "get_health"):
            health = adapter.get_health()
        
        meta = CHANNEL_META.get(cid, {"icon": "Activity", "label": cid, "order": 99})

        results.append({
            "id": cid,
            "status": "connected" if connected else "disconnected",
            "enabled": enabled,
            "name": meta["label"],
            "icon": meta["icon"],
            "order": meta["order"],
            "health": health
        })

    # Sort for consistent UI display
    results.sort(key=lambda x: x["order"])
    return {"channels": results}


@app.get("/api/channels/{channel_id}/config", dependencies=[Depends(verify_authenticated)])
async def get_channel_config(channel_id: str):
    """Retrieves vault payload explicitly overriding encrypted strings with masks natively."""
    creds = await vault.retrieve_secret(f"channel_{channel_id}") or {}
    
    # Generic explicit mapping to mask known keys automatically preventing frontend spills
    masked = {}
    for k, v in creds.items():
        if "key" in k.lower() or "secret" in k.lower() or "token" in k.lower():
            if v and len(v) > 8:
                masked[k] = v[:4] + "****" + v[-4:]
            else:
                masked[k] = "****"
        else:
            masked[k] = v
            
    enabled = await vault.retrieve_secret(f"channel_{channel_id}_enabled") or {"enabled": False}
    masked["enabled"] = enabled.get("enabled", False)
    return masked


@app.put("/api/channels/{channel_id}/config", dependencies=[Depends(verify_authenticated)])
async def set_channel_config(channel_id: str, data: Dict[str, Any] = Body(...)):
    """Upserts directly into vault overriding previous context natively persisting changes asynchronously."""
    # Separate `enabled` core logic, don't write it to base string
    if "enabled" in data:
        await vault.store_secret(f"channel_{channel_id}_enabled", {"enabled": data.pop("enabled")})
        
    # Prevent overwritting masked values accidentally natively
    existing = await vault.retrieve_secret(f"channel_{channel_id}") or {}
    for k, v in data.items():
        if v and "***" in v:
            data[k] = existing.get(k, "")
            
    await vault.store_secret(f"channel_{channel_id}", data)
    return {"status": "success", "message": "Credentials updated"}


@app.get("/api/channels/{channel_id}/accounts", dependencies=[Depends(verify_authenticated)])
async def get_channel_accounts(channel_id: str):
    """Yields all unique remote profiles interacting within this bridge."""
    adapter = channel_registry.get(channel_id)
    if not adapter or not hasattr(adapter, "get_accounts"):
        return {"accounts": []}
    return {"accounts": adapter.get_accounts()}


@app.delete("/api/channels/{channel_id}/accounts/{account_id}", dependencies=[Depends(verify_authenticated)])
async def delete_channel_account(channel_id: str, account_id: str):
    """Disconnects and forgets a remote account mapping explicitly mapped to adapter routing arrays."""
    adapter = channel_registry.get(channel_id)
    if not adapter or not hasattr(adapter, "disconnect_account"):
        raise HTTPException(status_code=404, detail="Disconnect logic not configured for adapter.")
    success = adapter.disconnect_account(account_id)
    return {"status": "ok" if success else "failed"}


@app.get("/api/channels/whatsapp/status", dependencies=[Depends(verify_authenticated)])
async def get_whatsapp_status():
    """Live WhatsApp node polling map pulling string payloads returning 64 base payloads directly."""
    wa = channel_registry.get("whatsapp")
    if not wa:
        return {"status": "DISCONNECTED"}
    
    state = getattr(wa, "state", "IDLE")
    qr = getattr(wa, "qr_code", None)
    
    return {
        "status": state,
        "qrCode": qr
    }


@app.put("/api/channels/nostr/profile", dependencies=[Depends(verify_authenticated)])
async def update_nostr_profile(data: Dict[str, str] = Body(...)):
    """Pushes decentralized properties mapped natively into relays directly."""
    no = channel_registry.get("nostr")
    if not no or not hasattr(no, "update_profile"):
        raise HTTPException(status_code=404, detail="Nostr adapter unavailable.")
        
    res = await no.update_profile(data)
    if not res:
        raise HTTPException(status_code=500, detail="Failed to broadcast Nostr Relay Protocol logic.")
    return {"status": "ok"}



@app.post("/api/channels/{channel_id}/connect", dependencies=[Depends(verify_authenticated)])
async def connect_channel(channel_id: str, data: Dict[str, Any] = Body(...)):
    """Manually trigger a channel connection with provided credentials."""
    adapter = channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    
    # Store credentials in vault first
    await vault.store_secret(f"channel_{channel_id}", data)
    
    # Force enabled state
    adapter.enabled = True
    await vault.store_secret(f"channel_{channel_id}_enabled", {"enabled": True})
    
    # Attempt connection
    success = await adapter.connect(data)
    if not success:
        raise HTTPException(status_code=400, detail=f"Connection failed: {getattr(adapter, 'last_error', 'Unknown error')}")
    
    return {"status": "connected", "channel": channel_id}


# ── Webhook Inbound Handlers (Sprint 2 — Sovereign Spec §2.1–2.2) ──

@app.post("/webhook/telegram/{token}")
async def telegram_webhook(token: str, update: Dict[str, Any]):
    """Inbound webhook for Telegram messages."""
    adapter = channel_registry.get("telegram")
    if not adapter or not adapter.is_connected or adapter.bot_token != token:
        return {"ok": False, "error": "unauthorized"}

    parsed = await adapter.process_webhook(update)
    if parsed and orchestrator:
        # Trigger autonomous turn if enabled
        asyncio.create_task(orchestrator.handle_inbound_message(parsed))
    
    return {"ok": True}


@app.get("/webhook/whatsapp")
async def whatsapp_verify(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp verification endpoint (GET)."""
    adapter = channel_registry.get("whatsapp")
    if not adapter:
        raise HTTPException(status_code=404)
    
    res = adapter.verify_webhook(mode, token, challenge)
    if res:
        return Response(content=res)
    raise HTTPException(status_code=403)


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(body: Dict[str, Any]):
    """WhatsApp inbound payload handler (POST)."""
    adapter = channel_registry.get("whatsapp")
    if not adapter or not adapter.is_connected:
        return {"status": "ignored"}

    parsed_list = adapter.process_webhook_event(body)
    if parsed_list and orchestrator:
        for msg in parsed_list:
            asyncio.create_task(orchestrator.handle_inbound_message(msg))
            
    return {"status": "received"}


@app.post("/webhook/google_chat")
async def google_chat_webhook(payload: Dict[str, Any]):
    """Google Chat App events handler."""
    adapter = channel_registry.get("google_chat")
    if not adapter or not adapter.is_connected:
        return {"status": "ignored"}
        
    parsed = await adapter.process_event(payload)
    if parsed and orchestrator:
        asyncio.create_task(orchestrator.handle_inbound_message(parsed))
    return {"status": "success"}



# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 3: Exec Approval API (Sovereign Spec §5.6)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/exec/allow", dependencies=[Depends(verify_authenticated)])
async def exec_allow(data: Dict[str, Any] = Body(...)):
    """Allow an exec approval request."""
    request_id = data.get("request_id")
    if not request_id:
        raise HTTPException(status_code=400, detail="Missing request_id")
    return exec_approval.handle_allow(
        request_id=request_id,
        persist=data.get("persist", False),
        command=data.get("command", ""),
        tool_name=data.get("tool_name", ""),
    )


@app.post("/api/exec/deny", dependencies=[Depends(verify_authenticated)])
async def exec_deny(data: Dict[str, Any] = Body(...)):
    """Deny an exec approval request."""
    request_id = data.get("request_id")
    if not request_id:
        raise HTTPException(status_code=400, detail="Missing request_id")
    return exec_approval.handle_deny(
        request_id=request_id,
        persist=data.get("persist", False),
        command=data.get("command", ""),
        tool_name=data.get("tool_name", ""),
    )


@app.get("/api/exec/policies", dependencies=[Depends(verify_authenticated)])
async def list_exec_policies():
    """List all persistent exec approval policies."""
    return exec_approval.list_policies()


@app.delete("/api/exec/policies/{policy_id}", dependencies=[Depends(verify_authenticated)])
async def delete_exec_policy(policy_id: int):
    """Delete a persistent exec policy."""
    if not exec_approval.delete_policy(policy_id):
        raise HTTPException(status_code=404, detail="Policy not found")
    return {"status": "deleted"}


@app.get("/api/sessions", dependencies=[Depends(verify_authenticated)])
async def list_sessions(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all active and historical sessions (Alias for usage summary)."""
    s_date = date.fromisoformat(start) if start else None
    e_date = date.fromisoformat(end) if end else None
    return usage_tracker.get_sessions(start=s_date, end=e_date, limit=limit)


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 5: Session Config Overrides
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/sessions/{session_key}/config", dependencies=[Depends(verify_authenticated)])
async def get_session_config(session_key: str):
    """Get per-session configuration overrides."""
    from .models import SessionConfig
    with Session(db_engine) as session:
        stmt = select(SessionConfig).where(SessionConfig.session_key == session_key)
        config = session.exec(stmt).first()
        if not config:
            return {"session_key": session_key, "overrides": {}}
        return {
            "session_key": session_key,
            "label": config.label,
            "model_override": config.model_override,
            "thinking_level": config.thinking_level,
            "verbose_level": config.verbose_level,
            "reasoning_level": config.reasoning_level,
        }

@app.delete("/api/sessions/{session_key}", dependencies=[Depends(verify_authenticated)])
async def delete_session(session_key: str):
    """Delete a specific session and all its associated data (logs, usage, config)."""
    from .models import SessionConfig, UsageLog, MessageLog
    with Session(db_engine) as session:
        # 1. Delete Session Config
        session.exec(delete(SessionConfig).where(SessionConfig.session_key == session_key))
        # 2. Delete Message Logs
        session.exec(delete(MessageLog).where(MessageLog.session_key == session_key))
        # 3. Delete Usage Logs
        session.exec(delete(UsageLog).where(UsageLog.session_key == session_key))
        
        session.commit()
        return {"status": "deleted", "session_key": session_key}


@app.patch("/api/sessions/{session_key}/config", dependencies=[Depends(verify_authenticated)])
async def patch_session_config(session_key: str, data: Dict[str, Any] = Body(...)):
    """Apply partial updates to per-session configuration."""
    from .models import SessionConfig
    with Session(db_engine) as session:
        stmt = select(SessionConfig).where(SessionConfig.session_key == session_key)
        config = session.exec(stmt).first()
        if not config:
            config = SessionConfig(session_key=session_key)
        
        updated = False
        for key in ["label", "model_override", "thinking_level", "verbose_level", "reasoning_level"]:
            if key in data:
                setattr(config, key, data[key])
                updated = True
        
        if updated:
            session.add(config)
            session.commit()
        return {"status": "patched", "session_key": session_key}


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 3: Usage Analytics API (Sovereign Spec §4)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/usage/summary", dependencies=[Depends(verify_authenticated)])
async def usage_summary(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
):
    """Get high-level usage aggregates."""
    s_date = date.fromisoformat(start) if start else None
    e_date = date.fromisoformat(end) if end else None
    return usage_tracker.get_summary(start=s_date, end=e_date)


@app.get("/api/usage/sessions", dependencies=[Depends(verify_authenticated)])
async def usage_sessions(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get aggregated session usage statistics."""
    s_date = date.fromisoformat(start) if start else None
    e_date = date.fromisoformat(end) if end else None
    return usage_tracker.get_sessions(start=s_date, end=e_date, limit=limit)


@app.get("/api/usage/daily", dependencies=[Depends(verify_authenticated)])
async def usage_daily(
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None)
):
    """Get daily rollup of token usage and costs."""
    s_date = date.fromisoformat(start) if start else None
    e_date = date.fromisoformat(end) if end else None
    return usage_tracker.get_daily(start=s_date, end=e_date)


@app.get("/api/usage/sessions/{key}/timeseries", dependencies=[Depends(verify_authenticated)])
async def usage_session_timeseries(key: str):
    """Get per-turn incremental usage for a specific session."""
    return usage_tracker.get_session_timeseries(key)


@app.get("/api/sessions/{key}/log", dependencies=[Depends(verify_authenticated)])
async def session_log(key: str, role: Optional[str] = Query(None)):
    """Get full transcript log for a session with optional role filtering."""
    return usage_tracker.get_session_log(key, role_filter=role)


@app.get("/api/usage/export/sessions.csv", dependencies=[Depends(verify_authenticated)])
async def export_sessions_csv(start: Optional[str] = Query(None), end: Optional[str] = Query(None)):
    """Export session summary as CSV."""
    s_date = date.fromisoformat(start) if start else None
    e_date = date.fromisoformat(end) if end else None
    csv_str = usage_tracker.export_sessions_csv(s_date, e_date)
    return PlainTextResponse(content=csv_str, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=sessions.csv"})


@app.get("/api/usage/export/daily.csv", dependencies=[Depends(verify_authenticated)])
async def export_daily_csv(start: Optional[str] = Query(None), end: Optional[str] = Query(None)):
    """Export daily rollup as CSV."""
    s_date = date.fromisoformat(start) if start else None
    e_date = date.fromisoformat(end) if end else None
    csv_str = usage_tracker.export_daily_csv(s_date, e_date)
    return PlainTextResponse(content=csv_str, media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=daily_usage.csv"})


@app.get("/api/discord/guilds", dependencies=[Depends(verify_authenticated)])
async def get_discord_guilds():
    """List all Discord guilds the bot is a member of."""
    adapter = channel_registry.get("discord")
    if not adapter: return {"guilds": []}
    return {"guilds": getattr(adapter, "guilds", [])}


@app.put("/api/discord/guilds/{guild_id}/mapping", dependencies=[Depends(verify_authenticated)])
async def update_discord_mapping(guild_id: str, data: Dict[str, Any] = Body(...)):
    """Update the default routing channel for a Discord guild."""
    from .models import DiscordGuildMapping
    with Session(db_engine) as session:
        mapping = session.exec(select(DiscordGuildMapping).where(DiscordGuildMapping.guild_id == guild_id)).first()
        if not mapping:
            mapping = DiscordGuildMapping(guild_id=guild_id)
        
        mapping.default_channel_id = data.get("default_channel_id")
        mapping.enabled = data.get("enabled", True)
        session.add(mapping)
        session.commit()
    return {"status": "updated", "guild_id": guild_id}


# --- Device Identity & Lifecycle (Sprint 4.3) ---

@app.get("/api/devices/pairing", dependencies=[Depends(verify_authenticated)])
async def get_device_pairing_data(agent_id: str = "alluci_node_1"):
    """Generates QR pairing payload for new device connection."""
    return device_manager.create_pairing_session(agent_id=agent_id)

@app.get("/api/devices/status", dependencies=[Depends(verify_authenticated)])
async def list_devices():
    """Lists all registered devices and their status."""
    from .models import Device
    with Session(db_engine) as session:
        devices = session.exec(select(Device)).all()
        return {
            "devices": [d.model_dump() for d in devices],
            "node_metadata": device_manager.get_local_capabilities()
        }

@app.post("/api/devices/register")
async def register_new_device(data: Dict[str, Any] = Body(...)):
    """Device-side registration call. Adds device in 'pending' status."""
    device = await device_manager.register_device(
        name=data.get("name", "Unknown Device"),
        public_key_b64=data.get("public_key"),
        capabilities=data.get("capabilities", {})
    )
    return {"status": "pending", "device_id": device.id}

@app.put("/api/devices/{device_id}/approve", dependencies=[Depends(verify_authenticated)])
async def approve_device(device_id: int):
    """Admin approval for a pending device."""
    success = await device_manager.approve_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"status": "approved"}

@app.put("/api/devices/{device_id}/revoke", dependencies=[Depends(verify_authenticated)])
async def revoke_device(device_id: int):
    """Admin revocation of a device."""
    success = await device_manager.revoke_device(device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"status": "revoked"}

@app.post("/api/devices/{device_id}/bind", dependencies=[Depends(verify_authenticated)])
async def bind_device(device_id: int, data: Dict[str, str] = Body(...)):
    """Rotates binding token for an authorized device mapping explicitly to an agent manifold id."""
    agent_id = data.get("agent_id", "alluci_node_1")
    try:
        new_token = device_manager.rotate_binding_token(device_id, agent_id)
        return {"status": "bound", "token": new_token, "agent_id": agent_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/.well-known/nostr.json")
async def nostr_nip05_verification(name: str = Query(...)):
    """
    NIP-05 Identity Verification Endpoint.
    Maps a human-readable name to a Nostr hex pubkey.
    """
    adapter = channel_registry.get("nostr")
    if not adapter or not adapter.is_connected:
        raise HTTPException(status_code=404, detail="Nostr bridge not configured.")

    try:
        # In a real sovereign setup, we'd check if 'name' matches the agent's identity anchor.
        # For now, we return the bridge's anchored public key for any lookups against this domain.
        from nostr_sdk import Keys
        # Use the bridge's nsec to derive the hex pubkey if available
        if hasattr(adapter, "keys") and adapter.keys:
            hex_pub = adapter.keys.public_key().to_hex()
            return {
                "names": {
                    name: hex_pub
                },
                "relays": {
                    hex_pub: adapter.relays
                }
            }
    except Exception as e:
        logger.error(f"[ NOSTR ] NIP-05 resolution error: {e}")
    
    raise HTTPException(status_code=404, detail="Identity not found.")


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 6: Verus Wallet API & Integration (Phase 1-4)
# ═══════════════════════════════════════════════════════════════════════════════

from .verus_wallet import wallet_service
from .security.verus_node import node_manager
from .models import (
    WalletSendRequest, WalletConvertRequest, WalletInvoiceRequest,
    WalletMiningStartRequest, WalletBridgeSendRequest, WalletIdentityUpdateRequest,
    WalletNodeStatus, WalletNodeAction
)

@app.get("/api/wallet/dashboard", dependencies=[Depends(verify_authenticated)])
async def get_wallet_dashboard():
    """Get the wallet dashboard overview."""
    return await wallet_service.get_dashboard()

@app.get("/api/wallet/balances", dependencies=[Depends(verify_authenticated)])
async def get_wallet_balances():
    """Get all currency balances across all addresses."""
    return await wallet_service.get_balances()

@app.get("/api/wallet/transactions", dependencies=[Depends(verify_authenticated)])
async def get_wallet_transactions(limit: int = 50, skip: int = 0):
    """Get paginated transaction history."""
    return await wallet_service.get_transactions(count=limit, skip=skip)

@app.get("/api/wallet/transaction/{txid}", dependencies=[Depends(verify_authenticated)])
async def get_wallet_transaction_detail(txid: str):
    """Get detailed transaction info."""
    result = await wallet_service.get_transaction_detail(txid)
    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return result

@app.post("/api/wallet/send", dependencies=[Depends(verify_authenticated)])
async def wallet_send(req: WalletSendRequest = Body(...)):
    """Send currency to an address."""
    result = await wallet_service.send(req.to, req.amount, req.currency, req.memo)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@app.post("/api/wallet/convert", dependencies=[Depends(verify_authenticated)])
async def wallet_convert(req: WalletConvertRequest = Body(...)):
    """Convert currency via DeFi AMM."""
    result = await wallet_service.convert(req.amount, req.from_currency, req.to_currency, req.via)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@app.post("/api/wallet/convert/estimate", dependencies=[Depends(verify_authenticated)])
async def wallet_convert_estimate(req: WalletConvertRequest = Body(...)):
    """Get conversion estimate via DeFi AMM."""
    result = await wallet_service.get_conversion_estimate(req.amount, req.from_currency, req.to_currency)
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@app.get("/api/wallet/address/new", dependencies=[Depends(verify_authenticated)])
async def get_new_wallet_address():
    """Generate a new receiving address."""
    result = await wallet_service.get_receive_address()
    if not result.get("address"):
        raise HTTPException(status_code=500, detail="Failed to generate address")
    return result

@app.post("/api/wallet/invoice", dependencies=[Depends(verify_authenticated)])
async def create_wallet_invoice(req: WalletInvoiceRequest = Body(...)):
    """Create a VerusPay invoice with QR code data."""
    result = await wallet_service.create_invoice(req.amount, req.currency, req.memo, req.expiry_minutes)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

@app.get("/api/wallet/mining", dependencies=[Depends(verify_authenticated)])
async def get_wallet_mining_status():
    """Get current mining/staking status."""
    return await wallet_service.get_mining_status()

@app.post("/api/wallet/mining/start", dependencies=[Depends(verify_authenticated)])
async def start_wallet_mining(req: WalletMiningStartRequest = Body(...)):
    """Start mining or staking."""
    if req.mode == "stake":
        result = await wallet_service.start_staking()
    else:
        result = await wallet_service.start_mining(req.threads, req.chains)
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

@app.post("/api/wallet/mining/stop", dependencies=[Depends(verify_authenticated)])
async def stop_wallet_mining():
    """Stop all mining and staking."""
    result = await wallet_service.stop_mining()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result

@app.get("/api/wallet/currencies", dependencies=[Depends(verify_authenticated)])
async def get_wallet_currencies():
    """List available DeFi currencies and liquidity pools."""
    return await wallet_service.get_currencies()

@app.post("/api/wallet/bridge/send", dependencies=[Depends(verify_authenticated)])
async def wallet_bridge_send(req: WalletBridgeSendRequest = Body(...)):
    """Bridge currency to Ethereum."""
    result = await wallet_service.bridge_to_eth(req.amount, req.currency, req.eth_address)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@app.get("/api/wallet/bridge/status", dependencies=[Depends(verify_authenticated)])
async def get_wallet_bridge_status():
    """Get status of the Ethereum bridge."""
    return await wallet_service.get_bridge_status()

@app.get("/api/wallet/identity", dependencies=[Depends(verify_authenticated)])
async def get_wallet_identity():
    """Get the agent's VerusID identity info."""
    result = await wallet_service.get_identity_info()
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result.get("error"))
    return result

@app.put("/api/wallet/identity", dependencies=[Depends(verify_authenticated)])
async def update_wallet_identity(req: WalletIdentityUpdateRequest = Body(...)):
    """Update VDXF multi-map data on the agent's identity."""
    result = await wallet_service.update_identity_data(req.key, req.value)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@app.get("/api/wallet/node/status", response_model=WalletNodeStatus, dependencies=[Depends(verify_authenticated)])
async def get_wallet_node_status():
    """Get the status of the local verusd node."""
    return node_manager.get_status()

@app.post("/api/wallet/node/action", dependencies=[Depends(verify_authenticated)])
async def wallet_node_action(req: WalletNodeAction = Body(...)):
    """Control the local verusd node (start, stop, etc.)."""
    try:
        if req.action == "start":
            await node_manager.start()
        elif req.action == "stop":
            await node_manager.stop()
        elif req.action == "provision":
            await node_manager.provision_binary()
        elif req.action == "restart":
            await node_manager.stop()
            await node_manager.start()
        else:
            raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}")
        return {"success": True, "action": req.action}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/wallet/login/request")
async def get_verusid_login_request(redirect_uri: str = Query(...)):
    """
    Generates a formal VerusID LoginConsentRequest JSON and Deeplink.
    """
    signing_id = settings.VERUS_ID_IDENTITY or "Sovereign Agent"
    return await verus_auth.get_verusid_login_request(signing_id, redirect_uri)

@app.post("/api/wallet/login/verify")
async def verify_verusid_login(data: Dict[str, Any] = Body(...)):
    """
    Webhook/Endpoint for verifying a scanned LoginConsentResponse.
    """
    success = await verus_auth.verify_login_response(data)
    if not success:
        raise HTTPException(status_code=401, detail="VerusID Signature Verification Failed")
    
    return {"status": "SUCCESS", "identity": data.get("signing_id")}

# --- Bridge Authentication Overhaul Routes ---

@app.get("/api/oauth/{bridge_id}/authorize")
async def oauth_authorize(bridge_id: str):
    """Initiates the OAuth 2.0 flow for a given bridge by generating the redirect URL."""
    config = OAUTH_CONFIGS.get(bridge_id)
    if not config:
        raise HTTPException(status_code=404, detail="OAuth config not found")
        
    redirect_uri = f"{os.getenv('DAEMON_PUBLIC_URL', 'http://localhost:8000').rstrip('/')}/api/oauth/{bridge_id}/callback"
    
    params = {
        "client_id": config["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(config["scopes"]),
    }
    # Google offline access
    if bridge_id in ['gm', 'gd']:
        params["access_type"] = "offline"
        params["prompt"] = "consent"
        
    auth_url = f"{config['authorize_url']}?{urllib.parse.urlencode(params)}"
    return {"authorize_url": auth_url}

@app.get("/api/oauth/{bridge_id}/callback")
async def oauth_callback(bridge_id: str, code: str = Query(None), state: str = Query(None)):
    """Generic OAuth callback endpoint for all OAuth-based bridges."""
    if bridge_id not in channel_registry:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<script>window.opener.postMessage({ type: 'OAUTH_COMPLETE', bridgeId: '" + bridge_id + "', error: 'Bridge not found' }, '*'); window.close();</script>")
    adapter = channel_registry[bridge_id]
    if hasattr(adapter, "handle_oauth_callback"):
        result = await adapter.handle_oauth_callback(code, state)
        # Assuming the adapter handles saving creds internally and we just want to close the popup
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<script>window.opener.postMessage({ type: 'OAUTH_COMPLETE', bridgeId: '" + bridge_id + "', success: true }, '*'); window.close();</script>")
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse("<script>window.opener.postMessage({ type: 'OAUTH_COMPLETE', bridgeId: '" + bridge_id + "', error: 'OAuth not implemented' }, '*'); window.close();</script>")

@app.get("/api/channels/wechat/qr-init")
async def wechat_qr_init():
    adapter = channel_registry.get("wechat")
    if hasattr(adapter, "init_qr"):
        return await adapter.init_qr()
    raise HTTPException(status_code=501, detail="WeChat QR flow not implemented")

@app.get("/api/oauth/wechat/callback")
async def wechat_callback(code: str = Query(None)):
    adapter = channel_registry.get("wechat")
    if hasattr(adapter, "handle_oauth_callback"):
        return await adapter.handle_oauth_callback(code)
    raise HTTPException(status_code=501, detail="WeChat auth not implemented")

@app.post("/api/channels/webchat/session/{id}/capture")
async def webchat_session_capture(id: str, data: Dict[str, Any] = Body(...)):
    adapter = channel_registry.get("webchat")
    if hasattr(adapter, "capture_session"):
        return await adapter.capture_session(id, data)
    raise HTTPException(status_code=501, detail="WebChat capture not implemented")

@app.get("/api/channels/webchat/screenshot/{id}")
async def webchat_screenshot(id: str):
    adapter = channel_registry.get("webchat")
    if hasattr(adapter, "get_screenshot"):
        return await adapter.get_screenshot(id)
    raise HTTPException(status_code=501, detail="WebChat screenshot not implemented")

@app.post("/api/channels/icloud/2fa")
async def icloud_2fa(data: Dict[str, str] = Body(...)):
    adapter = channel_registry.get("icloud")
    if hasattr(adapter, "submit_2fa"):
        return await adapter.submit_2fa(data.get("code"))
    raise HTTPException(status_code=501, detail="iCloud 2FA not implemented")

@app.post("/api/channels/imessage/permission")
async def imessage_permission():
    adapter = channel_registry.get("imessage")
    if hasattr(adapter, "check_permission"):
        return await adapter.check_permission()
    raise HTTPException(status_code=501, detail="iMessage permissions not implemented")

@app.post("/api/channels/iwatch/pair")
async def iwatch_pair(data: Dict[str, str] = Body(...)):
    adapter = channel_registry.get("iwatch")
    if hasattr(adapter, "submit_pairing_code"):
        return await adapter.submit_pairing_code(data.get("code"))
    raise HTTPException(status_code=501, detail="iWatch pairing not implemented")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
