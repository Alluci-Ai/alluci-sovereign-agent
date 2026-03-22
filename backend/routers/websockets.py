import os
import logging
from ..logging_config import get_logger
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .. import services
from ..security.auth import verify_token
from fastapi_csrf_protect import CsrfProtect
from jose import JWTError
from ..config import settings
from urllib.parse import urlparse

logger = get_logger("WebsocketRouter")
router = APIRouter(tags=["WebSockets"])

def _verify_origin(websocket: WebSocket) -> bool:
    """
    Enforces Same-Origin Policy for WebSockets to prevent Cross-Site WebSocket Hijacking (CSWH).
    This is the WebSocket equivalent of CSRF protection.
    """
    origin = websocket.headers.get("origin")
    if not origin:
        # Allow connections without Origin header (e.g. native apps, curl)
        return True

    try:
        parsed_origin = urlparse(origin)
        allowed_origins = [
            "localhost", "127.0.0.1",
            urlparse(os.getenv("DAEMON_PUBLIC_URL", "")).hostname
        ]
        if parsed_origin.hostname in allowed_origins:
            return True
        
        logger.warning(f"[WS] Blocked connection from unauthorized origin: {origin}")
        return False
    except Exception:
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
