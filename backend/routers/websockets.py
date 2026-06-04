import asyncio
import json
import os
from typing import Optional
from fastapi import APIRouter, WebSocket, Query, HTTPException, status
from .. import services
from ..security.auth import verify_token
from jose import JWTError
from ..config import settings
from ..logging_config import get_logger

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

async def authenticate_ws_handshake(websocket: WebSocket) -> Optional[str]:
    """
    Extracts and verifies JWT token from cookies or query string before acceptance.
    """
    token = websocket.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token:
        token = websocket.query_params.get("token")
        if token:
            logger.warning("[WS] Query param token authentication is deprecated. Use HttpOnly cookies or message auth.")
    
    if not token or token == "undefined":
        return None
    
    try:
        verify_token(token)
        return token
    except JWTError:
        return None

@router.websocket("/ws/sovereign")
async def sovereign_websocket_endpoint(websocket: WebSocket):
    """Main communication manifold for the Sovereign Identity."""
    if not _verify_origin(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not allowed")
        return
        
    token = await authenticate_ws_handshake(websocket)
    if not token:
        # Fallback: Accept and wait for first auth message
        await websocket.accept()
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            msg = json.loads(raw)
            if msg.get("type") == "auth":
                token = msg.get("token")
                verify_token(token)  # type: ignore
            else:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
                return
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token or authentication timeout")
            return
    else:
        await websocket.accept()
        
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket, already_accepted=True)

@router.websocket("/ws/admin")
async def admin_websocket_endpoint(websocket: WebSocket):
    """JSON-RPC 2.0 gateway for real-time admin operations."""
    if not _verify_origin(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not allowed")
        return

    token = await authenticate_ws_handshake(websocket)
    if not token:
        # Fallback: Accept and let the gateway handle JSON-RPC hello authentication
        await websocket.accept()
    else:
        await websocket.accept()
        
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket, already_accepted=True)

@router.websocket("/api/logs/stream")
async def log_stream_endpoint(websocket: WebSocket):
    """Live system telemetry and log streaming."""
    if not _verify_origin(websocket):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Origin not allowed")
        return

    token = await authenticate_ws_handshake(websocket)
    if not token:
        # Fallback: Accept and wait for first auth message
        await websocket.accept()
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            msg = json.loads(raw)
            if msg.get("type") == "auth":
                token = msg.get("token")
                verify_token(token)  # type: ignore
            else:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication required")
                return
        except Exception:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid token or authentication timeout")
            return
    else:
        await websocket.accept()
        
    from ..log_streamer import log_stream_handler
    await log_stream_handler.handle(websocket, already_accepted=True)
