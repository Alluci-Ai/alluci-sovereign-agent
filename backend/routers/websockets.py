
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from .. import services

logger = logging.getLogger("WebsocketRouter")
router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws/sovereign")
async def sovereign_websocket_endpoint(websocket: WebSocket):
    """Main communication manifold for the Sovereign Identity."""
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket)

@router.websocket("/ws/admin")
async def admin_websocket_endpoint(websocket: WebSocket):
    """JSON-RPC 2.0 gateway for real-time admin operations."""
    if not services.ws_gw:
        await websocket.close(code=1001)
        return
    await services.ws_gw.handle_connection(websocket)

@router.websocket("/api/logs/stream")
async def log_stream_endpoint(websocket: WebSocket):
    """Live system telemetry and log streaming."""
    from ..log_streamer import log_stream_handler
    await log_stream_handler(websocket)
