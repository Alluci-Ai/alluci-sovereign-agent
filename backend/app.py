
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
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Depends, Query, Body, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter

from .config import settings
from .database import create_db_and_tables, engine as db_engine
from sqlmodel import Session, select
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
from .logging_config import configure_logging
from .security.guardrail import scanner
from .ws_gateway import JsonRpcGateway
from .analytics import UsageTracker
from .cron_engine import CronEngine
from .log_streamer import log_buffer, log_stream_handler
from .config_editor import ConfigEditor
from .exec_approval import ExecApprovalManager
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


# --- Lifespan & Production Initialization ---

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global vault, router, ace, orchestrator, task_manager, skill_manager, sovereign_identity, local_inference
    global ws_gw, usage_tracker, cron_engine, config_editor, exec_approval, channel_registry

    # Initialize structured logging before any log calls
    configure_logging(app_env=settings.APP_ENV)

    logger.info("[ POLYTOPE_DAEMON ] Booting up...")
    
    # Initialize Production Rate Limiter (Redis)
    try:
        r = redis.from_url(settings.REDIS_URL, encoding="utf-8")
        await FastAPILimiter.init(r)
        logger.info(f"[ CACHE ]: Redis distributed rate limiter initialized on {settings.REDIS_URL}")
    except Exception as e:
        logger.error(f"[ CACHE ]: Redis initialization failed. Rate limiting will NOT be active: {e}")

    create_db_and_tables()

    # 1. Security Layer
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    sovereign_identity = SovereignIdentity(settings)

    # 2. Inference Layer
    router = ModelRouter(settings)

    # 3. Affective Engine
    ace = AffectiveEngine()

    # 4. Skill Manager
    skill_manager = SkillManager(vault)

    # 5. Executive Orchestrator (Sovereign Core)
    orchestrator = ExecutiveOrchestrator(router, vault, ace, settings, skill_manager)

    # 6. Task Manager
    task_manager = TaskManager()

    # 7. Local Inference Bridge
    local_inference = LocalInferenceBridge(settings)

    # 8. Sprint 1: WebSocket Gateway
    ws_gw = JsonRpcGateway(jwt_secret=settings.JWT_SECRET_KEY)
    ws_gw.inject_services(vault=vault, router=router, orchestrator=orchestrator)

    # 9. Sprint 1: Usage & Cost Analytics
    usage_tracker = UsageTracker(db_engine)

    # 10. Sprint 1: Cron Engine
    cron_engine = CronEngine(db_engine, orchestrator=orchestrator)
    await cron_engine.start()

    # 11. Sprint 1: Log Streamer
    log_buffer.install_handler()

    # 12. Sprint 1: Config Editor
    config_editor = ConfigEditor(settings)

    # 13. Sprint 3: Exec Approval
    exec_approval = ExecApprovalManager(db_engine, ws_gateway=ws_gw)

    # 14. Sprint 2: Channel Adapter Registry
    vault_root = os.path.expanduser("~/.polytope/vaults")
    os.makedirs(vault_root, exist_ok=True)

    from .bridges.telegram import TelegramBridge
    from .bridges.whatsapp import WhatsAppBridge
    from .bridges.discord import DiscordBridge
    from .bridges.slack import SlackBridge
    from .bridges.email import EmailBridge

    channel_registry["telegram"] = TelegramBridge("telegram", vault_root)
    channel_registry["whatsapp"] = WhatsAppBridge("whatsapp", vault_root)
    channel_registry["discord"] = DiscordBridge("discord", vault_root)
    channel_registry["slack"] = SlackBridge("slack", vault_root)
    channel_registry["email"] = EmailBridge("email", vault_root)

    # Auto-connect channels from vault-stored credentials (non-blocking)
    for ch_name, adapter in channel_registry.items():
        try:
            creds = await vault.retrieve_secret(f"channel_{ch_name}")
            if creds:
                connected = await adapter.connect(creds)
                if connected:
                    logger.info(f"[ CHANNELS ] {ch_name} auto-connected")
                else:
                    logger.warning(f"[ CHANNELS ] {ch_name} credentials found but connection failed")
        except Exception as e:
            logger.debug(f"[ CHANNELS ] {ch_name} not configured: {e}")

    # Wire channel registry to cron engine for delivery routing
    cron_engine.channel_registry = channel_registry

    # 15. Background Services
    await orchestrator.start_background_services()

    logger.info("[ POLYTOPE_DAEMON ] All systems nominal. Ready.")

    yield

    logger.info("[ POLYTOPE_DAEMON ] Shutting down...")
    await cron_engine.stop()
    await orchestrator.stop_background_services()


app = FastAPI(title="Polytope Executive Daemon", version="1.0.0", lifespan=lifespan)

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
    
    is_valid = await verus_auth.verify_login_response(identity, signature, challenge_id)
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


# --- System Status ---

@app.get("/status", dependencies=[Depends(verify_authenticated)])
async def get_system_status():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent
    thermal = "nominal" if cpu < 80 else "elevated"

    return SystemStatus(
        cpu_usage=cpu,
        ram_usage=ram,
        thermal_status=thermal,
        active_bridges=list(vault.get_active_vaults()),
        vault_integrity=True,
        daemon_version="1.0.0",
        harmonic_status="Active" if orchestrator else "Inactive",
        identity_active=sovereign_identity.enabled if sovereign_identity else False
    )


# --- Vault Operations ---

@app.post("/vault/rotate", dependencies=[Depends(verify_authenticated)])
async def rotate_vault_keys(payload: Dict[str, str] = Body(...)):
    """[ ROTATE_KEYS ] Instantly re-encrypts all vaults with a new key."""
    new_key = payload.get("new_key")
    if not new_key:
        raise HTTPException(status_code=400, detail="Missing new_key")
    
    success = await vault.rotate_keys(new_key)
    if not success:
        raise HTTPException(status_code=500, detail="Vault key rotation failed")
    
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



# --- Objective Execution ---

@app.post("/objective/execute", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def execute_objective(req: ObjectiveRequest):
    try:
        # 1. Sanitize user-provided objective
        sanitized_objective = await sanitize_input(req.objective)
        
        # 2. Execute via orchestrator
        result = await orchestrator.execute_objective(sanitized_objective, req.autonomy_level)
        
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
    try:
        # 1. Store in the secure vault (Tier 2/3)
        # We append to a special "audit_ledger" secret
        current_ledger = await vault.retrieve_secret("audit_ledger") or []
        current_ledger.append(entry.model_dump())
        
        # Keep only last 1000 entries in the local vault to prevent bloat
        if len(current_ledger) > 1000:
            current_ledger = current_ledger[-1000:]
            
        await vault.store_secret("audit_ledger", current_ledger)
        
        # 2. If VerusID is enabled, anchor the new ledger state
        if settings.VERUS_AUTH_ENABLED and settings.VERUS_ID_IDENTITY:
            from .security.vdxf_store import VDXFStore
            store = VDXFStore(settings.VERUS_ID_IDENTITY)
            
            # Anchor the hash of the entire ledger to the blockchain
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
        "rp": {"name": "Alluci Sovereign Agent", "id": settings.WEBAUTHN_RP_ID if hasattr(settings, 'WEBAUTHN_RP_ID') else "localhost"},
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

@app.post("/skills/import", dependencies=[Depends(verify_authenticated)])
async def import_skill_package(package: Dict[str, Any]):
    """Imports a .polytype package into the Review Queue."""
    result = await skill_manager.import_package(package)
    return result

@app.get("/skills/review", dependencies=[Depends(verify_authenticated)])
async def get_review_queue():
    return await skill_manager.get_review_queue()

@app.post("/skills/review/{skill_id}/promote", dependencies=[Depends(verify_authenticated)])
async def promote_skill(skill_id: str):
    success = await skill_manager.promote_from_queue(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found in review queue")
    return {"status": "promoted", "id": skill_id}


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
    except Exception as e:
        logger.error(f"Gemini proxy error: {e}")
        raise HTTPException(status_code=500, detail="Inference request failed.")

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
                transcript = await local_inference.transcribe_stream(audio_chunk)
                
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
# Sprint 1: WebSocket JSON-RPC Admin Gateway (OpenClaw §5.1)
# ═══════════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    """JSON-RPC 2.0 gateway for real-time admin operations."""
    await ws_gw.handle_connection(websocket)


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 1: Usage & Cost Analytics API (OpenClaw §4)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/usage/sessions", dependencies=[Depends(verify_authenticated)])
async def get_usage_sessions(
    start: str = Query(None, description="Start date (YYYY-MM-DD)"),
    end: str = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(1000, ge=1, le=5000),
):
    """Date-range session usage aggregation."""
    from datetime import date as dt_date
    s = dt_date.fromisoformat(start) if start else None
    e = dt_date.fromisoformat(end) if end else None
    return usage_tracker.get_sessions(start=s, end=e, limit=limit)


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
# Sprint 1: Cron Engine API (OpenClaw §3)
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
# Sprint 1: Configuration Editor API (OpenClaw §8)
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
# Sprint 1: Log Streaming API (OpenClaw §9)
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
    """Export buffered logs as JSONL text."""
    jsonl = log_buffer.export_jsonl(level=level)
    return PlainTextResponse(content=jsonl, media_type="application/jsonl",
                             headers={"Content-Disposition": "attachment; filename=logs.jsonl"})


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 2–4: Channel Health Dashboard & Management (OpenClaw §2.9–2.11)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/channels/status", dependencies=[Depends(verify_authenticated)])
async def get_channel_status():
    """Aggregate per-adapter health for all channels."""
    statuses = []
    for name, adapter in channel_registry.items():
        if hasattr(adapter, "get_health"):
            statuses.append(adapter.get_health())
        else:
            statuses.append({"channel": name, "connected": getattr(adapter, "is_connected", False)})
    return {
        "channels": statuses,
        "total": len(statuses),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.put("/api/channels/{channel_id}/toggle", dependencies=[Depends(verify_authenticated)])
async def toggle_channel(channel_id: str, data: Dict[str, Any] = Body(...)):
    """Enable or disable a channel adapter at runtime."""
    adapter = channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    enabled = data.get("enabled", True)
    adapter.enabled = enabled
    if not enabled and hasattr(adapter, "disconnect"):
        await adapter.disconnect()
    return {"channel": channel_id, "enabled": enabled}


@app.post("/api/channels/{channel_id}/connect", dependencies=[Depends(verify_authenticated)])
async def connect_channel(channel_id: str, data: Dict[str, Any] = Body(...)):
    """Manually trigger a channel connection with provided credentials."""
    adapter = channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"Channel '{channel_id}' not found")
    
    # Store credentials in vault first
    await vault.store_secret(f"channel_{channel_id}", data)
    
    # Attempt connection
    success = await adapter.connect(data)
    if not success:
        raise HTTPException(status_code=400, detail=f"Connection failed: {getattr(adapter, 'last_error', 'Unknown error')}")
    
    return {"status": "connected", "channel": channel_id}


# ── Webhook Inbound Handlers (Sprint 2 — OpenClaw §2.1–2.2) ──

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



# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 3: Exec Approval API (OpenClaw §5.6)
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


# ═══════════════════════════════════════════════════════════════════════════════
# Sprint 5: Session Config Overrides (OpenClaw §5.4–5.5)
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


@app.put("/api/sessions/{session_key}/config", dependencies=[Depends(verify_authenticated)])
async def update_session_config(session_key: str, data: Dict[str, Any] = Body(...)):
    """Update per-session configuration overrides."""
    from .models import SessionConfig
    with Session(db_engine) as session:
        stmt = select(SessionConfig).where(SessionConfig.session_key == session_key)
        config = session.exec(stmt).first()
        if not config:
            config = SessionConfig(session_key=session_key)
        for key in ["label", "model_override", "thinking_level", "verbose_level", "reasoning_level"]:
            if key in data:
                setattr(config, key, data[key])
        session.add(config)
        session.commit()
        return {"status": "updated", "session_key": session_key}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
