
import sys
import re
import contextlib
import psutil
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from cryptography.fernet import Fernet

from .config import load_settings, Settings
from .database import create_db_and_tables, get_session
from .models import (
    ObjectiveRequest, TelemetryData, SystemStatus, LoginRequest,
    TaskUpdate, TaskItem, SoulPreferences, SoulManifest
)
from .security.vault import VaultManager
from .security.auth import create_access_token, verify_authenticated
from .security.verus import SovereignIdentity
from .inference.router import ModelRouter
from .ace.engine import AffectiveEngine
from .orchestrator import ExecutiveOrchestrator
from .tasks import TaskManager
from .security.verusid_auth import verus_auth
from .security.verus_rpc import verus_rpc

logger = logging.getLogger("PolytopeApp")

settings = load_settings()

# Global Services
vault: VaultManager = None
router: ModelRouter = None
ace: AffectiveEngine = None
orchestrator: ExecutiveOrchestrator = None
task_manager: TaskManager = None
skill_manager: SkillManager = None
sovereign_identity: SovereignIdentity = None

# --- Input Sanitization ---

# Patterns that indicate prompt injection attempts
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"you\s+are\s+now\s+(?:a|an)\s+(?:new|different)",
    r"system\s*:\s*",
    r"<\s*(?:system|admin|root)\s*>",
    r"\[\s*SYSTEM\s*\]",
    r"override\s+(?:all\s+)?(?:safety|security|restrictions)",
]
_injection_re = re.compile("|".join(PROMPT_INJECTION_PATTERNS), re.IGNORECASE)


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent prompt injection attacks."""
    if _injection_re.search(text):
        logger.warning(f"[SECURITY] Potential prompt injection detected and sanitized.")
        raise HTTPException(
            status_code=400,
            detail="Input contains disallowed patterns."
        )
    # Strip null bytes and excessive whitespace
    text = text.replace("\x00", "").strip()
    # Limit input length
    if len(text) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Input exceeds maximum allowed length (10000 characters)."
        )
    return text


# --- Rate Limiting ---

class InMemoryRateLimiter:
    """Simple in-memory rate limiter. Replace with Redis for multi-process."""
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = {}

    def is_allowed(self, client_id: str) -> bool:
        now = datetime.now(timezone.utc).timestamp()
        window_start = now - self.window_seconds

        if client_id not in self._requests:
            self._requests[client_id] = []

        # Prune old entries
        self._requests[client_id] = [
            ts for ts in self._requests[client_id] if ts > window_start
        ]

        if len(self._requests[client_id]) >= self.max_requests:
            return False

        self._requests[client_id].append(now)
        return True


rate_limiter = InMemoryRateLimiter(max_requests=settings.RATE_LIMIT_PER_MINUTE)


# --- Lifespan ---

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global vault, router, ace, orchestrator, task_manager, skill_manager

    logger.info("[ POLYTOPE_DAEMON ] Booting up...")
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

    # 7. Background Services
    await orchestrator.start_background_services()

    logger.info("[ POLYTOPE_DAEMON ] All systems nominal. Ready.")

    yield

    logger.info("[ POLYTOPE_DAEMON ] Shutting down...")
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


# --- Middleware ---

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware — applied to all routes."""
    # Skip rate limiting for health/ready endpoints
    if request.url.path in ("/health", "/ready"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."}
        )
    return await call_next(request)


@app.middleware("http")
async def verify_v_auth_signature(request: Request, call_next):
    """
    Middleware to optionally verify SovereignIdentity V-Auth signatures on incoming requests.
    In a full implementation, this checks the `X-V-Auth-Signature` header.
    """
    # For now, we act as a pass-through structural enforcement point
    # Real implementation would read body bytes and verify against signature header
    return await call_next(request)


# --- Health & Readiness ---

@app.get("/health")
async def health_check():
    """Kubernetes-style liveness probe."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/ready")
async def readiness_check():
    """Kubernetes-style readiness probe."""
    ready = orchestrator is not None and vault is not None and router is not None
    if not ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}


# --- Auth ---

    raise HTTPException(status_code=401, detail="Invalid key")


# --- VerusID (SSID) Auth ---

@app.get("/auth/verusid/challenge")
async def get_verusid_challenge(identity: str = Query("")):
    """Generates a login challenge for Verus Mobile scan."""
    if not settings.VERUS_AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="VerusID Authentication not enabled")
    return verus_auth.create_login_challenge(identity)

@app.post("/auth/verusid/callback")
async def verusid_callback(payload: Dict[str, str] = Body(...)):
    """Verifies the signed challenge and issues a JWT."""
    identity = payload.get("identity")
    signature = payload.get("signature")
    challenge_id = payload.get("challenge_id")
    
    if not all([identity, signature, challenge_id]):
        raise HTTPException(status_code=400, detail="Missing identity, signature, or challenge_id")
    
    is_valid = await verus_auth.verify_login_response(identity, signature, challenge_id)
    if is_valid:
        token = create_access_token(data={"sub": identity, "vauth": True})
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
    
    success = vault.rotate_keys(new_key)
    if not success:
        raise HTTPException(status_code=500, detail="Vault key rotation failed")
    
    # In production, we'd also update the env/settings persisting the MASTER_KEY
    return {"status": "success", "message": "All Active Vaults Cryptographically Rotated"}

@app.post("/api/vault/flush", dependencies=[Depends(verify_authenticated)])
async def flush_vault():
    vault.flush_cache()
    return {"status": "success", "message": "Cache flushed."}

@app.post("/api/check-health", dependencies=[Depends(verify_authenticated)])
async def check_health():
    """Triggers a health check across all model manifolds."""
    results = await router.check_health()
    for provider, status in results.items():
        vault.update_vault_status(provider, status)
    return {"status": "success", "results": results}


# --- Objective Execution ---

@app.post("/objective/execute", dependencies=[Depends(verify_authenticated)])
async def execute_objective(req: ObjectiveRequest):
    try:
        # Sanitize user-provided objective
        sanitized_objective = sanitize_input(req.objective)
        result = await orchestrator.execute_objective(sanitized_objective, req.autonomy_level)
        return {"result": result}
    except HTTPException:
        raise  # Re-raise sanitization errors
    except Exception as e:
        logger.error(f"Objective execution failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    return task_manager.get_tasks(status, priority, timeline)

@app.post("/tasks", dependencies=[Depends(verify_authenticated)])
async def add_task(task: TaskUpdate):
    return task_manager.add_task(task)

@app.put("/tasks/{index}", dependencies=[Depends(verify_authenticated)])
async def update_task(index: int, task: TaskUpdate):
    result = task_manager.update_task(index, task)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result

@app.delete("/tasks/{index}", dependencies=[Depends(verify_authenticated)])
async def delete_task(index: int):
    if not task_manager.delete_task(index):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "deleted"}


# --- Identity Forge (Soul Manifest) Routes ---

@app.get("/soul/manifest", dependencies=[Depends(verify_authenticated)])
async def get_soul_manifest():
    try:
        data = vault.retrieve_secret("soul_manifest")
        if data:
            return SoulManifest(**data)
        return SoulManifest()
    except Exception as e:
        logger.error(f"Failed to load Soul Manifest: {e}")
        return SoulManifest()

@app.put("/soul/manifest", dependencies=[Depends(verify_authenticated)])
async def update_soul_manifest(manifest: SoulManifest):
    try:
        vault.store_secret("soul_manifest", manifest.model_dump())
        return {"status": "ok", "message": "Soul Manifest updated."}
    except Exception as e:
        logger.error(f"Failed to save Soul Manifest: {e}")
        raise HTTPException(status_code=500, detail="Failed to persist Soul Manifest.")

@app.post("/soul/preview", dependencies=[Depends(verify_authenticated)])
async def preview_soul_manifest(manifest: SoulManifest, control_question: str = Body("Analysis of current status?", embed=True)):
    """Simulates the new personality with full cognitive context."""
    try:
        # Build context from the candidate manifest
        context_parts = [
            f"# IDENTITY CORE\n{manifest.identityCore}",
            f"\n# VOICE PROFILE\n{manifest.voiceProfile}",
            f"\n# REASONING STYLE\n{manifest.reasoningStyle}",
            f"\n# DIRECTIVES\n" + "\n".join(f"- {d}" for d in manifest.directives),
        ]

        # Merge active skills
        if skill_manager:
            active_skills = skill_manager.list_skills()
            if active_skills:
                merged = skill_manager.merge_skills_for_runtime(
                    [s.get("id") for s in active_skills if s.get("verified")]
                )
                if merged.get("logic"):
                    context_parts.append(f"\n# ACTIVE COGNITIVE MODULES\n" +
                                       "\n".join(f"- {l}" for l in merged["logic"]))

        full_context = "\n".join(context_parts)

        # Sanitize control question
        sanitized_question = sanitize_input(control_question)

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
        return {
            "preview_response": response,
            "context_length": len(full_context),
            "skills_loaded": len(active_skills) if skill_manager else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview failed: {str(e)}")


# --- Legacy Support for simple preferences ---

@app.get("/soul/preferences", dependencies=[Depends(verify_authenticated)])
async def get_soul_preferences():
    manifest_data = vault.retrieve_secret("soul_manifest")
    if manifest_data and "preferences" in manifest_data:
        return SoulPreferences(**manifest_data["preferences"])
    return SoulPreferences()

@app.put("/soul/preferences", dependencies=[Depends(verify_authenticated)])
async def update_soul_preferences(prefs: SoulPreferences):
    manifest_data = vault.retrieve_secret("soul_manifest")
    if not manifest_data:
        manifest_data = SoulManifest().model_dump()
    manifest_data["preferences"] = prefs.model_dump()
    vault.store_secret("soul_manifest", manifest_data)
    return {"status": "ok", "preferences": prefs}


# --- Skill Registry & Review Routes ---

@app.get("/skills", dependencies=[Depends(verify_authenticated)])
async def list_skills():
    if not skill_manager:
        raise HTTPException(status_code=503, detail="Skill Manager not initialized")
    return skill_manager.list_skills()

@app.post("/skills", dependencies=[Depends(verify_authenticated)])
async def create_skill(skill: Dict[str, Any]):
    return skill_manager.save_skill(skill)

@app.delete("/skills/{skill_id}", dependencies=[Depends(verify_authenticated)])
async def delete_skill(skill_id: str):
    success = skill_manager.delete_skill(skill_id)
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
    return skill_manager.get_review_queue()

@app.post("/skills/review/{skill_id}/promote", dependencies=[Depends(verify_authenticated)])
async def promote_skill(skill_id: str):
    success = skill_manager.promote_from_queue(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Skill '{skill_id}' not found in review queue")
    return {"status": "promoted", "id": skill_id}


# --- Gemini API Proxy (server-side key management) ---

@app.post("/api/gemini/proxy", dependencies=[Depends(verify_authenticated)])
async def gemini_proxy(payload: Dict[str, Any]):
    """
    Proxies Gemini API requests so the API key never leaves the server.
    Frontend sends the prompt; backend adds the key and forwards.
    """
    try:
        prompt = payload.get("prompt", "")
        complexity = payload.get("complexity", "MEDIUM")
        sanitized = sanitize_input(prompt)
        result = await router.get_response(sanitized, complexity=complexity)
        return {"result": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Gemini proxy error: {e}")
        raise HTTPException(status_code=500, detail="Inference request failed.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
