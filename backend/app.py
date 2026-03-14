
import logging
import contextlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .logging_config import configure_logging
from . import services
from .routers import auth, objectives, telemetry, system, vault, channels, voice, crons, wallet, sessions, config, soul, exec_approval, tasks, dag, websockets, memory, goals, sop

logger = logging.getLogger("PolytopeApp")

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(app_env=settings.APP_ENV)
    logger.info("[ POLYTOPE_DAEMON ] Booting up...")
    await services.init_services(app)
    
    # SEC-001: WebAuthn Redis Initialization
    from .security.webauthn_store import webauthn_store, WebAuthnChallengeStore
    if services.redis_client:
        import backend.security.webauthn_store as _wa_store_module
        _wa_store_module.webauthn_store = WebAuthnChallengeStore(services.redis_client)
        logger.info("[ WEBAUTHN ] Challenge store backed by Redis.")
        
    yield
    await services.shutdown_services()

app = FastAPI(
    title="Alluci Sovereign Agent",
    description="Sovereign Executive Assistant with Polytopic Manifolds",
    version="2.1.0",
    lifespan=lifespan
)

# CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(auth.router)
app.include_router(objectives.router)
app.include_router(tasks.router)
app.include_router(dag.router)
app.include_router(websockets.router)
app.include_router(memory.router)
app.include_router(goals.router)
app.include_router(sop.router)
app.include_router(vault.router)
app.include_router(channels.router)
app.include_router(voice.router)
app.include_router(crons.router)
app.include_router(wallet.router)
app.include_router(telemetry.router)
app.include_router(system.router)
app.include_router(sessions.router)
app.include_router(config.router)
app.include_router(soul.router)
app.include_router(exec_approval.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
