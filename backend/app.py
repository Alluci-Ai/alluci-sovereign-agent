
import logging
import contextlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter.depends import RateLimiter
from .config import settings
from .logging_config import get_logger

logger = get_logger("PolytopeApp")
from . import services
from .routers import auth, objectives, telemetry, system, vault, channels, voice, crons, wallet, sessions, config, soul, exec_approval, tasks, dag, websockets, memory, goals, sop

async def global_rate_limit(request: Request, response: Response):
    """
    Global rate limit dependency. 
    Skips if Redis is not configured or available.
    """
    if services.redis_client:
        return await RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60)(request, response)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    from .logging_config import configure_logging
    from .tracing_config import configure_tracing
    configure_logging(app_env=settings.APP_ENV)
    configure_tracing(app=app)
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
        logger.info("[ WEBAUTHN ] Credentials loaded from vault.")
        
    yield
    await services.shutdown_services()

app = FastAPI(
    title="Alluci Sovereign Agent",
    description="Sovereign Executive Assistant with Polytopic Manifolds",
    version="2.1.0",
    lifespan=lifespan,
    dependencies=[Depends(global_rate_limit)]
)

@app.get("/health", include_in_schema=False)
async def root_health():
    return {"status": "healthy"}

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

# Register Routers (Versioned API)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(objectives.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(dag.router, prefix="/api/v1")
app.include_router(websockets.router, prefix="/api/v1")
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

from fastapi.responses import RedirectResponse

@app.api_route("/api/{path:path}",
    methods=["GET","POST","PUT","DELETE","PATCH","OPTIONS"],
    include_in_schema=False)
async def legacy_api_redirect(path: str):
    """Redirect unversioned /api/ paths to /api/v1/ for backward compat."""
    return RedirectResponse(url=f"/api/v1/{path}", status_code=307)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
