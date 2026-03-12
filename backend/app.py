
import logging
import contextlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .logging_config import configure_logging
from . import services
from .routers import auth, objectives, telemetry, system, vault, channels, voice, crons, wallet, sessions, config, soul, exec_approval

logger = logging.getLogger("PolytopeApp")

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(app_env=settings.APP_ENV)
    logger.info("[ POLYTOPE_DAEMON ] Booting up...")
    await services.init_services(app)
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
app.include_router(telemetry.router)
app.include_router(system.router)
app.include_router(vault.router)
app.include_router(channels.router)
app.include_router(voice.router)
app.include_router(crons.router)
app.include_router(wallet.router)
app.include_router(sessions.router)
app.include_router(config.router)
app.include_router(soul.router)
app.include_router(exec_approval.router)

# --- WebSocket Gateways ---

@app.websocket("/ws/sovereign")
async def sovereign_websocket_endpoint(websocket: WebSocket):
    """Main communication manifold for the Sovereign Identity."""
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket)

@app.websocket("/ws/admin")
async def admin_websocket_endpoint(websocket: WebSocket):
    """JSON-RPC 2.0 gateway for real-time admin operations."""
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket)

@app.websocket("/api/logs/stream")
async def log_stream_endpoint(websocket: WebSocket):
    """Live system telemetry and log streaming."""
    from .log_streamer import log_stream_handler
    await log_stream_handler(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
