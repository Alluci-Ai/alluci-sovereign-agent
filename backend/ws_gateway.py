"""
WebSocket JSON-RPC 2.0 Gateway for the Polytope Sovereign OS.

Provides a persistent WebSocket connection for:
- Real-time event push (stream tokens, turn completion, system health)
- JSON-RPC 2.0 method dispatch (system.status, system.health, system.presence, etc.)
- Hello handshake with JWT authentication

Reference: OpenClaw Section 5.1
"""

import asyncio
import json
import time
import logging
import psutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set
from fastapi import WebSocket, WebSocketDisconnect
from jose import jwt, JWTError

logger = logging.getLogger("WSGateway")

# ─── Connected Client Registry ───────────────────────────────────────────────

class ConnectedClient:
    """Represents a single authenticated WebSocket client."""

    def __init__(self, websocket: WebSocket, client_id: str, subject: str):
        self.websocket = websocket
        self.client_id = client_id
        self.subject = subject
        self.connected_at = datetime.now(timezone.utc)
        self.last_heartbeat = self.connected_at
        self.subscriptions: Set[str] = set()  # event channels subscribed to

    def touch(self):
        self.last_heartbeat = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "subject": self.subject,
            "connected_at": self.connected_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "subscriptions": list(self.subscriptions),
        }


# ─── JSON-RPC Helpers ────────────────────────────────────────────────────────

def _rpc_success(id: Any, result: Any) -> str:
    return json.dumps({"jsonrpc": "2.0", "id": id, "result": result})


def _rpc_error(id: Any, code: int, message: str, data: Any = None) -> str:
    err: Dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return json.dumps({"jsonrpc": "2.0", "id": id, "error": err})


# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
AUTH_REQUIRED = -32000


# ─── Gateway Class ───────────────────────────────────────────────────────────

class JsonRpcGateway:
    """
    Manages all WebSocket admin connections, dispatches JSON-RPC 2.0 methods,
    and pushes server-side events.
    """

    def __init__(self, jwt_secret: str):
        self.jwt_secret = jwt_secret
        self.clients: Dict[str, ConnectedClient] = {}
        self._boot_time = time.monotonic()
        self._methods: Dict[str, Any] = {}
        self._service_refs: Dict[str, Any] = {}  # injected service references
        self._register_builtins()

    # ── Service Injection ─────────────────────────────────────────────────

    def inject_services(self, **services):
        """Inject application services (vault, orchestrator, etc.) for RPC methods."""
        self._service_refs.update(services)

    # ── Built-in RPC Methods ──────────────────────────────────────────────

    def _register_builtins(self):
        self.register_method("system.status", self._rpc_system_status)
        self.register_method("system.health", self._rpc_system_health)
        self.register_method("system.presence", self._rpc_system_presence)
        self.register_method("methods.list", self._rpc_methods_list)
        self.register_method("events.subscribe", self._rpc_events_subscribe)
        self.register_method("events.unsubscribe", self._rpc_events_unsubscribe)

    def register_method(self, name: str, handler):
        """Register a JSON-RPC method.  handler(params, client) -> result"""
        self._methods[name] = handler

    # ── WebSocket Lifecycle ───────────────────────────────────────────────

    async def handle_connection(self, websocket: WebSocket):
        """Full lifecycle for a single WebSocket connection."""
        await websocket.accept()

        # ── Step 1: Hello Handshake (auth required within 5 s) ────────────
        client = await self._authenticate(websocket)
        if client is None:
            return  # connection closed by _authenticate

        self.clients[client.client_id] = client
        logger.info(f"[WS] Client connected: {client.client_id} ({client.subject})")

        try:
            # Push hello event
            await websocket.send_text(json.dumps({
                "jsonrpc": "2.0",
                "method": "hello",
                "params": {
                    "client_id": client.client_id,
                    "server_uptime_ms": int((time.monotonic() - self._boot_time) * 1000),
                    "protocol": "json-rpc-2.0",
                    "available_methods": list(self._methods.keys()),
                },
            }))

            # ── Step 2: Message Loop ──────────────────────────────────────
            async for raw in websocket.iter_text():
                await self._dispatch(raw, client)

        except WebSocketDisconnect:
            logger.info(f"[WS] Client disconnected: {client.client_id}")
        except Exception as e:
            logger.error(f"[WS] Connection error for {client.client_id}: {e}")
        finally:
            self.clients.pop(client.client_id, None)

    # ── Authentication ────────────────────────────────────────────────────

    async def _authenticate(self, websocket: WebSocket) -> Optional[ConnectedClient]:
        """Wait for a hello message with a JWT token."""
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
            msg = json.loads(raw)

            token = msg.get("params", {}).get("token") or msg.get("token")
            if not token:
                await websocket.send_text(
                    _rpc_error(msg.get("id"), AUTH_REQUIRED, "Missing auth token")
                )
                await websocket.close(code=4001, reason="Auth required")
                return None

            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            subject = payload.get("sub", "unknown")

            import uuid
            client_id = str(uuid.uuid4())[:8]
            return ConnectedClient(websocket, client_id, subject)

        except asyncio.TimeoutError:
            await websocket.close(code=4002, reason="Auth timeout")
            return None
        except JWTError:
            await websocket.close(code=4003, reason="Invalid token")
            return None
        except Exception as e:
            logger.warning(f"[WS] Auth error: {e}")
            await websocket.close(code=4000, reason="Auth failed")
            return None

    # ── Dispatch ──────────────────────────────────────────────────────────

    async def _dispatch(self, raw: str, client: ConnectedClient):
        """Parse a JSON-RPC 2.0 request and call the handler."""
        client.touch()

        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            await client.websocket.send_text(_rpc_error(None, PARSE_ERROR, "Parse error"))
            return

        # Validate request shape
        method = msg.get("method")
        rpc_id = msg.get("id")  # may be None for notifications

        if not method:
            await client.websocket.send_text(
                _rpc_error(rpc_id, INVALID_REQUEST, "Missing 'method'")
            )
            return

        # Heartbeat shortcut
        if method == "heartbeat":
            if rpc_id is not None:
                await client.websocket.send_text(_rpc_success(rpc_id, {"ok": True}))
            return

        handler = self._methods.get(method)
        if handler is None:
            await client.websocket.send_text(
                _rpc_error(rpc_id, METHOD_NOT_FOUND, f"Method '{method}' not found")
            )
            return

        params = msg.get("params", {})
        try:
            result = await handler(params, client)
            if rpc_id is not None:
                await client.websocket.send_text(_rpc_success(rpc_id, result))
        except Exception as e:
            logger.error(f"[WS] RPC error in '{method}': {e}")
            if rpc_id is not None:
                await client.websocket.send_text(
                    _rpc_error(rpc_id, INTERNAL_ERROR, str(e))
                )

    # ── Event Push ────────────────────────────────────────────────────────

    async def broadcast_event(self, event_name: str, data: Any):
        """Push an event to all connected clients subscribed to that channel."""
        payload = json.dumps({
            "jsonrpc": "2.0",
            "method": event_name,
            "params": data,
        })
        dead = []
        for cid, client in self.clients.items():
            if event_name in client.subscriptions or not client.subscriptions:
                try:
                    await client.websocket.send_text(payload)
                except Exception:
                    dead.append(cid)
        for cid in dead:
            self.clients.pop(cid, None)

    # ── Built-in RPC Implementations ─────────────────────────────────────

    async def _rpc_system_status(self, params: dict, client: ConnectedClient) -> dict:
        uptime_ms = int((time.monotonic() - self._boot_time) * 1000)
        mem = psutil.virtual_memory()
        return {
            "uptime_ms": uptime_ms,
            "active_sessions": len(self.clients),
            "memory_usage_mb": round(mem.used / (1024 * 1024), 1),
            "memory_total_mb": round(mem.total / (1024 * 1024), 1),
            "cpu_percent": psutil.cpu_percent(interval=0),
            "auth_mode": "jwt",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def _rpc_system_health(self, params: dict, client: ConnectedClient) -> dict:
        health = {"database": "ok", "vault": "unknown", "model_router": "unknown"}

        vault = self._service_refs.get("vault")
        if vault:
            try:
                vault.get_active_vaults()
                health["vault"] = "ok"
            except Exception:
                health["vault"] = "error"

        router = self._service_refs.get("router")
        if router:
            health["model_router"] = "ok"  # present = ok

        return health

    async def _rpc_system_presence(self, params: dict, client: ConnectedClient) -> dict:
        return {
            "clients": [c.to_dict() for c in self.clients.values()],
            "total": len(self.clients),
        }

    async def _rpc_methods_list(self, params: dict, client: ConnectedClient) -> dict:
        return {"methods": list(self._methods.keys())}

    async def _rpc_events_subscribe(self, params: dict, client: ConnectedClient) -> dict:
        channels = params.get("channels", [])
        client.subscriptions.update(channels)
        return {"subscribed": list(client.subscriptions)}

    async def _rpc_events_unsubscribe(self, params: dict, client: ConnectedClient) -> dict:
        channels = params.get("channels", [])
        client.subscriptions -= set(channels)
        return {"subscribed": list(client.subscriptions)}
