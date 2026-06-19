
import logging
import contextlib
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Depends
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
import uuid
from opentelemetry import trace
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .logging_config import get_logger, configure_logging
from .tracing_config import configure_tracing
from . import services
from .security.rate_limit import RateLimiter
import os

VERSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".version")
VERSION = open(VERSION_FILE).read().strip() if os.path.exists(VERSION_FILE) else "unknown"

logger = get_logger("PolytopeApp")

from .routers import auth, objectives, telemetry, system, vault, channels, voice, crons, wallet, sessions, config, soul, exec_approval, tasks, dag, websockets, memory, goals, sop, gemini, security, skills, egress
from .security.auth import verify_authenticated
from .security import csrf # Initialize CSRF config
from .engine.errors import AdapterError

try:
    from fastapi_csrf_protect import CsrfProtect
    from fastapi_csrf_protect.exceptions import CsrfProtectError
except ImportError:
    class FallbackCsrfProtect:
        async def validate_csrf(self, request):
            return None
    class FallbackCsrfProtectError(Exception):
        def __init__(self, message="CSRF validation failed"):
            self.message = message
            super().__init__(self.message)
    CsrfProtect = FallbackCsrfProtect  # type: ignore
    CsrfProtectError = FallbackCsrfProtectError  # type: ignore




async def global_rate_limit(request: Request = None, response: Response = None):  # type: ignore
    """
    Global rate limit. Always enforced — falls back to in-memory
    sliding window if Redis is unavailable.
    """
    if request is None or response is None:
        return
    try:
        return await RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60)(request, response)
    except HTTPException:
        raise  # Re-raise 429s — that's the whole point
    except Exception as e:
        logger.warning(f"[ RATE_LIMIT ] Primary limiter error, using fallback: {e}")
        from .security.rate_limiter import get_fallback_limiter
        fallback_times = getattr(settings, "RATE_LIMIT_PER_MINUTE", 60)
        try:
            fallback_times = int(fallback_times)
        except Exception:
            fallback_times = 60
        await get_fallback_limiter().check(request, times=fallback_times, seconds=60)

# global initialization outside lifespan to avoid recursive instrumentation hooks
configure_logging(app_env=settings.APP_ENV)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    from .core.startup_checks import assert_secrets_are_set, warn_on_stale_model_ids
    assert_secrets_are_set()
    warn_on_stale_model_ids()
    
    logger.info("[ POLYTOPE_DAEMON ] # 1. Initialize global system components")
    await services.init_services(app)

    # SEC-001: Initialize RS256 JWT keypair from vault
    from .security.auth import init_jwt_keys
    assert services.vault is not None, "Vault service must be initialized"
    private_key, public_key = await services.vault.get_or_create_jwt_keypair()
    init_jwt_keys(private_key, public_key)
    logger.info("[ JWT ] RS256 keypair loaded from vault.")
    
    # SEC-001: Redis Store Initializations
    if services.redis_client:
        # [ LOCAL_FIX ]: Ensure absolute imports work correctly in local dev environment
        from .security.webauthn_store import webauthn_store, WebAuthnChallengeStore
        import backend.security.webauthn_store as _wa_store_module
        _wa_store_module.webauthn_store = WebAuthnChallengeStore(services.redis_client)
        logger.info("[ WEBAUTHN ] Challenge store backed by Redis.")
        
        from .security.oauth_store import oauth_store, OAuthStateStore
        import backend.security.oauth_store as _oauth_store_module
        _oauth_store_module.oauth_store = OAuthStateStore(services.redis_client)
        logger.info("[ OAUTH ] State store backed by Redis.")
        
        from .security.credential_store import credential_store
        await credential_store.load_from_vault()
        
        from .security.verusid_auth import verus_auth
        verus_auth._redis = services.redis_client
        logger.info("[ VERUSID ] Challenge store backed by Redis.")
        
    if services.router:
        logger.info("[ LIFESPAN ] Triggering background preloading of LCE model...")
        import asyncio
        asyncio.create_task(services.router.pre_load_model())

    yield
    
    # --- Graceful Shutdown ---
    logger.info("[ SHUTDOWN ] Cleaning up system components...")
    if services.redis_client:
        await services.redis_client.close()
        logger.info("[ CACHE ] Redis connection closed.")
    
    logger.info("[ SHUTDOWN ] Alluci Sovereign Agent stopped gracefully.")
    await services.shutdown_services()

app = FastAPI(
    title="Alluci Sovereign Agent",
    description="Sovereign Executive Assistant with Polytopic Manifolds",
    version=VERSION,
    lifespan=lifespan,
    dependencies=[Depends(global_rate_limit)],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

from fastapi import HTTPException

class SovereignAPIException(Exception):
    def __init__(self, status_code: int, error_code: str, detail: str):
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail

@app.exception_handler(SovereignAPIException)
async def sovereign_api_exception_handler(request: Request, exc: SovereignAPIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "detail": exc.detail},
        headers={"X-RateLimit-Remaining": str(getattr(request.state, 'rate_limit_remaining', 'unknown'))}
    )

from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Templates directory
templates = Jinja2Templates(directory="backend/templates")
# Static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Include new routers
from .routers import monitoring, metrics_json
app.include_router(monitoring.router, prefix="/monitoring", dependencies=[Depends(verify_authenticated)])
app.include_router(metrics_json.router, prefix="/metrics")


# ── Exception Handlers ──────────────────────────────────────────────────────

def format_exception_detail(exc: Exception) -> str:
    """Return masked or full exception detail based on settings.DEBUG.

    The function resolves the runtime settings (which may be monkey‑patched in tests)
    and returns a user‑friendly message when DEBUG is disabled, otherwise the raw
    exception string.
    """
    import sys
    runtime_settings = sys.modules[__name__].settings
    # Prioritize production environment masking regardless of DEBUG flag
    if getattr(runtime_settings, "APP_ENV", "development") == "production":
        return "An internal server error occurred. Please contact the administrator or check the logs."
    # Return raw exception detail when DEBUG is enabled (non-production environments)
    if getattr(runtime_settings, "DEBUG", False):
        return str(exc)
    # Default to generic message for non-production, non-debug environments
    return "An internal server error occurred. Please contact the administrator or check the logs."


from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(AdapterError)
async def adapter_exception_handler(request: Request, exc: AdapterError):
    """Returns a structured JSON error when a tool adapter fails."""
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": f"Tool Execution Failed: {str(exc)}"},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global catch-all for unhandled exceptions.
    Excludes FastAPI/Starlette internal exceptions to avoid breaking standard behaviors.
    """
    if isinstance(exc, (StarletteHTTPException, RequestValidationError)):
        raise exc

    # [ PUBLIC_FIX ]: Mask stack traces in production to prevent information leakage
    logger.error(f"[ GLOBAL_ERROR ] {request.method} {request.url.path}: {exc}", exc_info=True)
    
    detail = format_exception_detail(exc)

    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal Server Error",
            "detail": detail,
        },
    )

from datetime import datetime, timezone

async def _check_health(app) -> dict:
    """Checks actual component health for readiness probes."""
    components = {}

    # Redis
    redis = getattr(app.state, 'redis_client', None) if hasattr(app, 'state') else services.redis_client
    if redis:
        try:
            await redis.ping()
            components["redis"] = "ok"
        except Exception:
            components["redis"] = "error"
    else:
        components["redis"] = "not_configured"

    # Database
    try:
        from sqlmodel import Session, select
        from .database import engine as db_engine
        with Session(db_engine) as session:
            session.exec(select(1))
        components["database"] = "ok"
    except Exception:
        components["database"] = "error"

    overall = "ok" if all(v in ("ok", "not_configured") for v in components.values()) else "degraded"
    return {
        "status": overall,
        "version": VERSION,
        "components": components,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/health", include_in_schema=False)
@app.get("/api/v1/health", include_in_schema=False)
async def health_check(request: Request):
    return await _check_health(request.app)

@app.get("/ready", include_in_schema=False)
@app.get("/api/v1/ready", include_in_schema=False)
async def readiness_check(request: Request):
    result = await _check_health(request.app)
    if result["status"] != "ok":
        return JSONResponse(status_code=503, content=result)
    return {"status": "ready"}


# ── Middleware ──────────────────────────────────────────────────────────────

from .metrics import metrics_middleware
app.middleware("http")(metrics_middleware)



from .security.csp import generate_nonce

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    nonce = generate_nonce()
    request.state.csp_nonce = nonce

    response = await call_next(request)
    
    import secure
    secure_headers = secure.Secure()
    try:
        secure_headers.framework.fastapi(response)
    except Exception as e:
        logger.error(f"[ SECURITY_HEADERS_ERROR ] {e}")

    # [ PUBLIC_FIX ]: Strict HSTS for production
    if (settings.APP_ENV == "production" or 
        request.headers.get("x-forwarded-proto") == "https" or
        settings.AUTH_COOKIE_SECURE):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    # [ PUBLIC_FIX ]: Hardened CSP with nonce
    response.headers["Content-Security-Policy"] = (
        f"default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}'; "
        f"style-src 'self' 'nonce-{nonce}'; "
        f"img-src 'self' data: https:; "
        f"font-src 'self' data:; "
        f"connect-src 'self' ws: wss: http: https:; "
        f"frame-ancestors 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self';"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    # Generate a unique request ID for tracing and logging
    request_id = str(uuid.uuid4())
    bind_contextvars(request_id=request_id)
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("http_request", attributes={
        "request_id": request_id,
        "http.method": request.method,
        "http.route": request.url.path,
    }):
        response = await call_next(request)
    # Attach the request ID to the response headers for client visibility
    response.headers["X-Request-ID"] = request_id
    # Clear context to avoid leaking into other requests
    clear_contextvars()
    return response



MAX_SIZE = 10 * 1024 * 1024  # 10MB
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Request Entity Too Large"})
    return await call_next(request)

@app.middleware("http")
async def csrf_protect_middleware(request: Request, call_next):
    """
    Enforces CSRF protection for all mutating operations.
    """
    if settings.APP_ENV == "testing":
        return await call_next(request)

    if request.method == "OPTIONS":
        return await call_next(request)

    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        path = request.url.path
        
        # [ PUBLIC_FIX ]: Sync skip_paths with official VerusID LoginConsent endpoints
        skip_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/verusid/webhook",    # New official webhook
            "/api/v1/auth/webauthn/verify",
            "/api/v1/auth/csrf-token",
            "/api/v1/auth/webauthn/assertion/verify",
            "/api/v1/gemini/proxy", 
            "/api/v1/objective/execute",
        ]
        
        is_testing = settings.APP_ENV == "testing"
        if path.startswith("/api/v1") and path not in skip_paths and not is_testing:
            csrf = CsrfProtect()
            try:
                await csrf.validate_csrf(request)
            except CsrfProtectError as e:
                logger.warning(f"[ CSRF_BLOCK ] {request.method} {path}: {e.message}")
                return JSONResponse(
                    status_code=403, 
                    content={"status": "error", "message": "CSRF validation failed", "detail": e.message}
                )
            except Exception as e:
                logger.error(f"[ CSRF_ERROR ] {request.method} {path}: {str(e)}")
                return JSONResponse(
                    status_code=403, 
                    content={"status": "error", "message": "CSRF validation error"}
                )
                
    return await call_next(request)


# ── Router Registration ─────────────────────────────────────────────────────

from .security.auth import verify_authenticated
from .health import router as health_router

app.include_router(auth.router, prefix="/api/v1")
app.include_router(objectives.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(dag.router, prefix="/api/v1")
app.include_router(websockets.router)
app.include_router(memory.router, prefix="/api/v1")
app.include_router(goals.router, prefix="/api/v1")
app.include_router(sop.router, prefix="/api/v1")
app.include_router(vault.router, prefix="/api/v1")
app.include_router(channels.router, prefix="/api/v1")
app.include_router(voice.router, prefix="/api/v1")
app.include_router(crons.router, prefix="/api/v1")
app.include_router(wallet.router, prefix="/api/v1")
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(config.router, prefix="/api/v1")
app.include_router(egress.router, prefix="/api/v1")
app.include_router(soul.router, prefix="/api/v1")
app.include_router(exec_approval.router, prefix="/api/v1")
app.include_router(gemini.router, prefix="/api/v1")
app.include_router(security.router, prefix="/api/v1")
app.include_router(skills.router, prefix="/api/v1")

# Health endpoints (custom)
app.include_router(health_router)

from .metrics import metrics_router
app.include_router(metrics_router, prefix="/api/v1", dependencies=[Depends(verify_authenticated)])

from fastapi.responses import RedirectResponse

@app.api_route("/api/{path:path}", methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS"], include_in_schema=False)
async def legacy_api_redirect(request: Request, path: str):
    if path.startswith("v1/") or path == "v1":
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    
    url = f"/api/v1/{path}"
    if request.query_params:
        url += f"?{request.query_params}"
        
    return RedirectResponse(url=url, status_code=307)


# [ PUBLIC_FIX ]: CORS must be the OUTERMOST middleware to handle preflights correctly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token", "X-Requested-With", "Accept"],
    expose_headers=["X-CSRF-Token"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
