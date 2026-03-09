import asyncio
import json
import logging
import os
import uuid
import httpx
import websockets
from typing import Dict, Any, Optional

logger = logging.getLogger("TunnelHandler")

class TunnelHandler:
    """
    Sovereign Secure Tunnel Handler.
    Creates a persistent WebSocket connection to a remote relay server
    to receive HTTP webhooks even when behind enterprise firewalls.
    """
    def __init__(self, local_base_url: str = "http://localhost:8000"):
        self.local_base_url = local_base_url.rstrip("/")
        self.relay_url = os.getenv("TUNNEL_RELAY_URL")  # e.g., wss://relay.alluci.ai
        self.daemon_id = os.getenv("DAEMON_ID", str(uuid.uuid4())[:8])
        self.is_running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        """Starts the tunnel in the background."""
        if not self.relay_url:
            logger.warning("TUNNEL_RELAY_URL not set. Secure Tunnel is inactive.")
            return

        if self.is_running:
            return

        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Secure Tunnel initiated. Daemon ID: {self.daemon_id}")

    async def stop(self):
        """Stops the tunnel."""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Secure Tunnel stopped.")

    async def _run_loop(self):
        """Main connection loop with production-grade exponential backoff."""
        uri = f"{self.relay_url.rstrip('/')}/tunnel/{self.daemon_id}"
        
        # In production, this would be an actual VDXF-signed token or similar
        headers = {
            "Authorization": f"Bearer {os.getenv('DAEMON_TOKEN', 'anonymous')}",
            "X-Sovereign-Spec": "A2-Production-v1"
        }
        
        retry_delay = 1
        while self.is_running:
            try:
                async with websockets.connect(uri, extra_headers=headers) as websocket:
                    logger.info("Connected to Secure Tunnel relay.")
                    retry_delay = 1 # Reset on success
                    async for message in websocket:
                        try:
                            payload = json.loads(message)
                            # Expected payload: {"id": "req_123", "method": "POST", "path": "/api/webhook/slack", "headers": {...}, "body": "..."}
                            asyncio.create_task(self._handle_request(websocket, payload))
                        except Exception as e:
                            logger.error(f"Error processing tunnel message: {e}")
            except Exception as e:
                logger.error(f"Tunnel connection failed: {e}. Retrying in {retry_delay}s...")
                await asyncio.sleep(min(retry_delay, 60))
                retry_delay *= 2

    async def _handle_request(self, websocket, payload: Dict[str, Any]):
        """Dispatches the proxied request to the local application."""
        req_id = payload.get("id")
        method = payload.get("method", "POST")
        path = payload.get("path", "")
        headers = payload.get("headers", {})
        body = payload.get("body", "")

        url = f"{self.local_base_url}{path}"
        
        try:
            async with httpx.AsyncClient() as client:
                # Remove host header to avoid local app rejection
                headers.pop("host", None)
                headers.pop("Host", None)
                
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    content=body,
                    timeout=30.0
                )
                
                # Send response back to relay
                response_payload = {
                    "id": req_id,
                    "status_code": resp.status_code,
                    "headers": dict(resp.headers),
                    "body": resp.text
                }
                await websocket.send(json.dumps(response_payload))
                
        except Exception as e:
            logger.error(f"Failed to proxy request to {path}: {e}")
            if req_id:
                await websocket.send(json.dumps({
                    "id": req_id,
                    "status_code": 502,
                    "body": f"Tunnel Proxy Error: {str(e)}"
                }))

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_active": self.is_running and self._task is not None and not self._task.done(),
            "daemon_id": self.daemon_id,
            "relay_url": self.relay_url
        }
