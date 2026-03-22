
import logging
import contextlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from secure import Secure

from .config import settings
from .logging_config import get_logger

logger = get_logger("PolytopeApp")
from . import services
from fastapi_limiter.depends import RateLimiter

# Monkeypatch RateLimiter to skip if services.redis_client is not initialized
# This prevents crashes on systems without Redis while allowing us to keep
# RateLimiter dependencies throughout the router files.
_original_limiter_call = RateLimiter.__call__
async def _safe_limiter_call(self, request: Request, response: Response):
    if not services.redis_client:
        return
    return await _original_limiter_call(self, request, response)
RateLimiter.__call__ = _safe_limiter_call
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

from .logging_config import configure_logging
from .tracing_config import configure_tracing

# global initialization outside lifespan to avoid recursive instrumentation hooks
configure_logging(app_env=settings.APP_ENV)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[ POLYTOPE_DAEMON ] Booting up...")
    await services.init_services(app)
    
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
    await services.shutdown_services()

app = FastAPI(
    title="Alluci Sovereign Agent",
    description="Sovereign Executive Assistant with Polytopic Manifolds",
    version="2.1.0",
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

# CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SEC-002: Security Headers (HSTS, NoSniff, XSS Protection)
secure_headers = Secure.with_default_headers()
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    secure_headers.set_headers(response)
    
    # HSTS for production and secure development
    if (settings.APP_ENV == "production" or 
        request.headers.get("x-forwarded-proto") == "https" or
        settings.AUTH_COOKIE_SECURE):
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        
    # Additional Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' ws: wss: http: https:;"
    )
    return response

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
app.include_router(metrics_router, prefix="/api/v1")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
