import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .. import services
from ..security.auth import verify_token
from jose import JWTError

logger = logging.getLogger("WebsocketRouter")
router = APIRouter(tags=["WebSockets"])

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
    if not await authenticate_ws(websocket, token):
        return
        
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket)

@router.websocket("/ws/admin")
async def admin_websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    """JSON-RPC 2.0 gateway for real-time admin operations."""
    if not await authenticate_ws(websocket, token):
        return
        
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket)

@router.websocket("/api/logs/stream")
async def log_stream_endpoint(websocket: WebSocket, token: str = Query(None)):
    """Live system telemetry and log streaming."""
    if not await authenticate_ws(websocket, token):
        return
        
    from ..log_streamer import log_stream_handler
    await log_stream_handler.handle(websocket)
