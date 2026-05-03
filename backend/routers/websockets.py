import os
from ..logging_config import get_logger
from fastapi import APIRouter, WebSocket, Query
from .. import services
from ..security.auth import verify_token
from jose import JWTError
from ..config import settings

logger = get_logger("WebsocketRouter")
router = APIRouter(tags=["WebSockets"])

def _verify_origin(websocket: WebSocket) -> bool:
    """
    Enforces Same-Origin Policy (SOP) for WebSockets to prevent Cross-Site WebSocket Hijacking (CSWH).
    Strictly rejects connections without an Origin header or from unauthorized origins.
    """
    origin = websocket.headers.get("origin")
    if not origin:
        logger.warning("[WS] Blocked connection: Missing Origin header (CSWH risk)")
        return False

    # Normalize origin for comparison
    origin = origin.rstrip("/")
    
    # Check against canonical allowed origins from config
    if origin in settings.ALLOWED_ORIGINS:
        return True

    # Fallback to DAEMON_PUBLIC_URL if explicitly set
    public_url = os.getenv("DAEMON_PUBLIC_URL", "")
    if public_url and origin == public_url.rstrip("/"):
        return True

    logger.warning(f"[WS] Blocked connection from unauthorized origin: {origin}")
    return False

async def authenticate_ws(websocket: WebSocket, token: str):
    """Verifies token from query string or cookies."""
    if not token:
        token = websocket.cookies.get("alluci_daemon_token")
    
    if not token:
        await websocket.close(code=4001, reason="Authentication required")
        return False
    
    try:
        verify_token(token)
        return True
    except JWTError:
        await websocket.close(code=4003, reason="Invalid token")
        return False

@router.websocket("/ws/sovereign")
async def sovereign_websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """Main communication manifold for the Sovereign Identity."""
    await websocket.accept()
    if not _verify_origin(websocket):
        await websocket.close(code=4003, reason="Origin not allowed")
        return
        
    if not await authenticate_ws(websocket, token):
        return
        
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket)

@router.websocket("/ws/admin")
async def admin_websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """JSON-RPC 2.0 gateway for real-time admin operations."""
    await websocket.accept()
    if not _verify_origin(websocket):
        await websocket.close(code=4003, reason="Origin not allowed")
        return

    if not await authenticate_ws(websocket, token):
        return
        
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket)

@router.websocket("/api/logs/stream")
async def log_stream_endpoint(websocket: WebSocket, token: str = Query(None)):
    """Live system telemetry and log streaming."""
    await websocket.accept()
    if not _verify_origin(websocket):
        await websocket.close(code=4003, reason="Origin not allowed")
        return

    if not await authenticate_ws(websocket, token):
        return
        
    from ..log_streamer import log_stream_handler
    await log_stream_handler.handle(websocket)
