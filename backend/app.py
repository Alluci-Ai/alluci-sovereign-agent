
import logging
import contextlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter.depends import RateLimiter

from .config import settings
from .logging_config import get_logger, configure_logging
from .tracing_config import configure_tracing
from . import services
from .security.rate_limiter import get_fallback_limiter

logger = get_logger("PolytopeApp")

_original_limiter_call = RateLimiter.__call__

async def _resilient_limiter_call(self, request: Request, response: Response):
    if services.redis_client:
        return await _original_limiter_call(self, request, response)

    times = getattr(self, "times", 60)
    seconds = getattr(self, "seconds", 60)
    minutes = getattr(self, "minutes", None)
    if minutes is not None:
        seconds = minutes * 60
    await get_fallback_limiter().check(request, times=times, seconds=seconds)

RateLimiter.__call__ = _resilient_limiter_call
from .routers import auth, objectives, telemetry, system, vault, channels, voice, crons, wallet, sessions, config, soul, exec_approval, tasks, dag, websockets, memory, goals, sop
from .security import csrf # Initialize CSRF config
from .engine.errors import AdapterError


async def global_rate_limit(request: Request, response: Response):
    """
    Global rate limit dependency. 
    Skips if Redis is not configured or available.
    """
    if services.redis_client:
        return await RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60)(request, response)

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
    private_key, public_key = await services.vault.get_or_create_jwt_keypair()
    init_jwt_keys(private_key, public_key)
    logger.info("[ JWT ] RS256 keypair loaded from vault.")
    
    # SEC-001: WebAuthn Redis Initialization
    from .security.webauthn_store import webauthn_store, WebAuthnChallengeStore
    if services.redis_client:
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
    version="6.4.0",
    lifespan=lifespan,
    dependencies=[Depends(global_rate_limit)]
)

# Instrument after app instance is created
configure_tracing(app=app)


# ── Exception Handlers ──────────────────────────────────────────────────────

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
        # Re-raise to let FastAPI's default handlers take over
        raise exc

    logger.error(f"[ GLOBAL_ERROR ] {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error", 
            "message": "Internal Server Error",
            "detail": str(exc) if settings.APP_ENV != "production" else "Check system logs"
        },
    )

@app.get("/health", include_in_schema=False)
async def health_check():
    from datetime import datetime, timezone
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/ready", include_in_schema=False)
async def root_ready():
    return {"status": "ready"}

@app.get("/api/v1/health", include_in_schema=False)
async def health_v1():
    from datetime import datetime, timezone
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/ready", include_in_schema=False)
async def ready_v1():
    return {"status": "ready"}

# Moved to bottom to ensure it's the outermost middleware for response headers

from .metrics import metrics_middleware

# Add after the security headers middleware:
app.middleware("http")(metrics_middleware)

# SEC-002: Security Headers — Nonce-based CSP
from .security.csp import generate_nonce

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # 1. Generate a fresh nonce for every request
    nonce = generate_nonce()
    request.state.csp_nonce = nonce

    response = await call_next(request)
    
    from secure import Secure
    secure_headers = Secure()
    secure_headers.framework.fastapi(response)

    # HSTS for production and secure development
    if (settings.APP_ENV == "production" or 
        request.headers.get("x-forwarded-proto") == "https" or
        settings.AUTH_COOKIE_SECURE):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    # Nonce-based CSP — no more unsafe-inline or unsafe-eval
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

# SEC-003: Request Body Size Limit Middleware (10MB)
MAX_SIZE = 10 * 1024 * 1024  # 10MB
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_SIZE:
            return JSONResponse(status_code=413, content={"detail": "Request Entity Too Large"})
    return await call_next(request)

# SEC-004: Global CSRF Validation for Mutating Routes
@app.middleware("http")
async def csrf_protect_middleware(request: Request, call_next):
    """
    Enforces CSRF protection for all POST, PUT, PATCH, and DELETE operations
    within the /api/v1/ prefix, excluding authentication entry points.
    """
    if request.method == "OPTIONS":
        return await call_next(request)

    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        path = request.url.path
        # Skip CSRF for login/auth entry points and health checks
        skip_paths = [
            "/api/v1/auth/login",
            "/api/v1/auth/verusid/callback",
            "/api/v1/auth/webauthn/verify",
            "/api/v1/auth/csrf-token", # Allow getting the token
            "/api/v1/auth/webauthn/assertion/verify" # WebAuthn login assertion
        ]
        
        if path.startswith("/api/v1") and path not in skip_paths and settings.APP_ENV != "testing":
            from fastapi_csrf_protect import CsrfProtect
            from fastapi_csrf_protect.exceptions import CsrfProtectError
            
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

from .security.auth import verify_authenticated

# Register Routers (Versioned API)
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
app.include_router(soul.router, prefix="/api/v1")
app.include_router(exec_approval.router, prefix="/api/v1")

# Observability — /api/v1/metrics (Prometheus scrape endpoint)
from .metrics import metrics_router
app.include_router(metrics_router, prefix="/api/v1", dependencies=[Depends(verify_authenticated)])

from fastapi.responses import RedirectResponse

@app.api_route("/api/{path:path}",
    methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS"],
    include_in_schema=False)
async def legacy_api_redirect(path: str):
    """
    Redirect unversioned /api/ paths to /api/v1/ for backward compat.
    Guard prevents recursive /api/v1/v1/... loops.
    """
    if path.startswith("v1/") or path == "v1":
        # This should have been caught by a router. If we're here, it's a 404.
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    
    return RedirectResponse(url=f"/api/v1/{path}", status_code=307)


# SEC-005: CORS Policy — OUTERMOST to ensure headers on errors
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
