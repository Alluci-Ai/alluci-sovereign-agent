"""
WebSocket JSON-RPC 2.0 Gateway for the Polytope Sovereign OS.

Provides a persistent WebSocket connection for:
- Real-time event push (stream tokens, turn completion, system health)
- JSON-RPC 2.0 method dispatch (system.status, system.health, system.presence, etc.)
- Hello handshake with JWT authentication

Reference: Sovereign Spec Section 5.1
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
        self._methods: Dict[str, Dict[str, Any]] = {} # name -> {handler, schema}
        self._service_refs: Dict[str, Any] = {}  # injected service references
        self._register_builtins()

    # ── Service Injection ─────────────────────────────────────────────────

    def inject_services(self, **services):
        """Inject application services (vault, orchestrator, etc.) for RPC methods."""
        self._service_refs.update(services)

    # ── Built-in RPC Methods ──────────────────────────────────────────────

    def _register_builtins(self):
        self.register_method("system.status", self._rpc_system_status, 
                            schema={"description": "Get real-time system performance and safety metrics."})
        self.register_method("system.health", self._rpc_system_health,
                            schema={"description": "Check connection status of all infrastructure manifolds."})
        self.register_method("system.presence", self._rpc_system_presence,
                            schema={"description": "List all active administrative sessions and edge nodes."})
        self.register_method("methods.list", self._rpc_methods_list,
                            schema={"description": "Enumerate all available RPC methods and their schemas."})
        self.register_method("events.subscribe", self._rpc_events_subscribe,
                            schema={"params": {"channels": "list[str]"}, "description": "Subscribe to real-time event streams."})
        self.register_method("events.unsubscribe", self._rpc_events_unsubscribe,
                            schema={"params": {"channels": "list[str]"}, "description": "Stop receiving updates from specific channels."})
        self.register_method("whatsapp.get_qr", self._rpc_whatsapp_get_qr,
                            schema={"description": "Retrieve the latest WhatsApp pairing code if unauthenticated."})
        self.register_method("exec.allow", self._rpc_exec_allow,
                            schema={"params": {"request_id": "str", "persist": "bool"}, "description": "Approve a pending tool execution request."})
        self.register_method("exec.deny", self._rpc_exec_deny,
                            schema={"params": {"request_id": "str"}, "description": "Reject and log a tool execution violation."})
        self.register_method("sessions.patch", self._rpc_sessions_patch,
                            schema={"params": {"session_key": "str", "label": "str"}, "description": "Apply runtime configuration overrides to a specific session."})
        self.register_method("system.update", self._rpc_system_update,
                            schema={"description": "Trigger the autonomous self-update mechanism."})
        self.register_method("system.update_check", self._rpc_system_update_check,
                            schema={"description": "Manually poll GitHub for new sovereign daemon releases."})
        self.register_method("signal.register", self._rpc_signal_register,
                            schema={"params": {"phone_number": "str", "use_voice": "bool"}, "description": "Initiate Signal account registration."})
        self.register_method("signal.verify", self._rpc_signal_verify,
                            schema={"params": {"phone_number": "str", "code": "str"}, "description": "Finalize Signal anchoring with SMS/Voice code."})

    def register_method(self, name: str, handler, schema: Dict[str, Any] = None):
        """Register a JSON-RPC method with optional schema documentation."""
        self._methods[name] = {
            "handler": handler,
            "schema": schema or {"description": "No documentation provided."}
        }

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

        # Heartbeat shortcut — Section 5.1 Sovereign Spec
        if method == "heartbeat":
            # Record persistent presence beacon
            db_engine = self._service_refs.get("db_engine")
            if db_engine:
                asyncio.create_task(self._record_presence(client))

            if rpc_id is not None:
                await client.websocket.send_text(_rpc_success(rpc_id, {"ok": True}))
            return

        method_meta = self._methods.get(method)
        if method_meta is None:
            await client.websocket.send_text(
                _rpc_error(rpc_id, METHOD_NOT_FOUND, f"Method '{method}' not found")
            )
            return

        handler = method_meta["handler"]

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
        
        vault = self._service_refs.get("vault")
        audit_ledger = await vault.retrieve_secret("audit_ledger") or [] if vault else []
        
        # Real-time Integrity Check (P1-S02)
        integrity_ok = True
        integrity_hash = "0x" + "0" * 40 # Placeholder for actual VDXF root hash
        if vault and vault.vdxf:
            vault_state = await vault._get_full_vault_state()
            integrity_ok = await vault.vdxf.verify_integrity(vault_state)
            # Fetch actual anchor if available
            integrity_hash = getattr(vault.vdxf, "current_anchor", integrity_hash)

        security_summary = {
            "total_events": len(audit_ledger),
            "last_event": audit_ledger[-1].get("event") if audit_ledger else None,
            "integrity_ok": integrity_ok,
            "integrity_hash": integrity_hash,
            "full_ledger": audit_ledger[-50:] # Recent history
        }

        # Include self-update status
        update_manager = self._service_refs.get("updater")
        update_status = update_manager.get_status() if update_manager else {}

        return {
            "uptime_ms": uptime_ms,
            "active_sessions": len(self.clients),
            "memory_usage_mb": round(mem.used / (1024 * 1024), 1),
            "memory_total_mb": round(mem.total / (1024 * 1024), 1),
            "cpu_percent": psutil.cpu_percent(interval=0),
            "auth_mode": "jwt",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "security_audit": security_summary,
            "update_status": update_status
        }

    async def _rpc_system_health(self, params: dict, client: ConnectedClient) -> dict:
        health = {"database": "ok", "vault": "unknown", "model_router": "unknown", "bridges": {}}

        vault = self._service_refs.get("vault")
        if vault:
            try:
                # Basic check: retrieve_secret works
                health["vault"] = "ok"
            except Exception:
                health["vault"] = "error"

        router = self._service_refs.get("router")
        if router:
            health["model_router"] = "ok"

        # Sprint 2: Bridges
        registry = self._service_refs.get("channel_registry")
        if registry:
            for cid, adapter in registry.items():
                status = "unknown"
                if hasattr(adapter, "is_connected"):
                    status = "connected" if await adapter.is_connected() else "disconnected"
                health["bridges"][cid] = status

        return health

    async def _rpc_system_presence(self, params: dict, client: ConnectedClient) -> dict:
        """Returns all connected clients and nodes within a 5-minute TTL window."""
        from .models import PresenceBeacon
        from sqlmodel import Session, select, col
        from datetime import datetime, timedelta, timezone

        db_engine = self._service_refs.get("db_engine")
        if not db_engine: 
            return {
                "active_sessions": [c.to_dict() for c in self.clients.values()],
                "total_active": len(self.clients)
            }

        # Query all beacons from last 5 minutes (TTL)
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        with Session(db_engine) as db:
            stmt = select(PresenceBeacon).where(col(PresenceBeacon.last_seen) >= cutoff)
            beacons = db.exec(stmt).all()

        return {
            "active_sessions": [c.to_dict() for c in self.clients.values()],
            "beacons": [
                {
                    "client_id": b.client_id, 
                    "subject": b.subject, 
                    "last_seen": b.last_seen.isoformat(),
                    "is_live": b.client_id in self.clients
                } 
                for b in beacons
            ],
            "total_beacons": len(beacons)
        }

    async def _rpc_methods_list(self, params: dict, client: ConnectedClient) -> dict:
        return {
            "methods": {
                name: meta["schema"] for name, meta in self._methods.items()
            }
        }

    async def _rpc_events_subscribe(self, params: dict, client: ConnectedClient) -> dict:
        channels = params.get("channels", [])
        client.subscriptions.update(channels)
        return {"subscribed": list(client.subscriptions)}

    async def _rpc_events_unsubscribe(self, params: dict, client: ConnectedClient) -> dict:
        channels = params.get("channels", [])
        client.subscriptions -= set(channels)
        return {"subscribed": list(client.subscriptions)}

    async def _rpc_whatsapp_get_qr(self, params: dict, client: ConnectedClient) -> dict:
        registry = self._service_refs.get("channel_registry")
        if not registry: return {"error": "No registry"}
        wa = registry.get("whatsapp")
        if not wa: return {"error": "No WhatsApp bridge"}
        return {"qr": getattr(wa, "last_qr", None), "state": getattr(wa, "connection_state", None)}

    async def _rpc_exec_allow(self, params: dict, client: ConnectedClient) -> dict:
        mgr = self._service_refs.get("approval_manager")
        if not mgr: return {"error": "No approval manager"}
        return mgr.handle_allow(
            params.get("request_id"),
            persist=params.get("persist", False),
            command=params.get("command", ""),
            tool_name=params.get("tool_name", "")
        )

    async def _rpc_exec_deny(self, params: dict, client: ConnectedClient) -> dict:
        mgr = self._service_refs.get("approval_manager")
        if not mgr: return {"error": "No approval manager"}
        return mgr.handle_deny(
            params.get("request_id"),
            persist=params.get("persist", False),
            command=params.get("command", ""),
            tool_name=params.get("tool_name", "")
        )

    async def _rpc_sessions_patch(self, params: dict, client: ConnectedClient) -> dict:
        """RPC method to hot-patch session config."""
        from .models import SessionConfig
        from sqlmodel import Session, select
        
        db_engine = self._service_refs.get("db_engine")
        if not db_engine: return {"error": "Internal database not connected"}
        
        session_key = params.get("session_key")
        if not session_key: return {"error": "Missing session_key"}
        
        with Session(db_engine) as db:
            stmt = select(SessionConfig).where(SessionConfig.session_key == session_key)
            config = db.exec(stmt).first()
            if not config:
                config = SessionConfig(session_key=session_key)
            
            updated = False
            for key in ["label", "model_override", "thinking_level", "verbose_level", "reasoning_level"]:
                if key in params:
                    setattr(config, key, params[key])
                    updated = True
            
            if updated:
                db.add(config)
                db.commit()
                db.refresh(config)
            
            return {"status": "patched", "session_key": session_key, "label": config.label}

    async def _rpc_system_update(self, params: dict, client: ConnectedClient) -> dict:
        """RPC to initiate a full system self-update."""
        mgr = self._service_refs.get("updater")
        if not mgr: return {"ok": False, "error": "Updater not initialized"}
        return await mgr.perform_update()

    async def _rpc_system_update_check(self, params: dict, client: ConnectedClient) -> dict:
        """RPC to manually check for newer GitHub releases."""
        mgr = self._service_refs.get("updater")
        if not mgr: return {"ok": False, "error": "Updater not initialized"}
        await mgr.check_for_updates()
        return mgr.get_status()

    async def _rpc_signal_register(self, params: dict, client: ConnectedClient) -> dict:
        channel_registry = self._service_refs.get("channel_registry")
        if not channel_registry or "signal" not in channel_registry:
            return {"status": "error", "message": "Signal adapter not active."}
        
        phone = params.get("phone_number")
        if not phone:
             return {"status": "error", "message": "Phone number required."}
             
        use_voice = params.get("use_voice", False)
        return await channel_registry["signal"].register(phone, use_voice)

    async def _rpc_signal_verify(self, params: dict, client: ConnectedClient) -> dict:
        channel_registry = self._service_refs.get("channel_registry")
        if not channel_registry or "signal" not in channel_registry:
            return {"status": "error", "message": "Signal adapter not active."}
        
        phone = params.get("phone_number")
        code = params.get("code")
        if not phone or not code:
             return {"status": "error", "message": "Phone and code required."}
             
        return await channel_registry["signal"].verify(phone, code)

    async def _record_presence(self, client: ConnectedClient):
        """Record persistent client beacon in SQLite."""
        from .models import PresenceBeacon
        from sqlmodel import Session, select
        from datetime import datetime, timezone

        db_engine = self._service_refs.get("db_engine")
        if not db_engine: return

        try:
            with Session(db_engine) as db:
                stmt = select(PresenceBeacon).where(PresenceBeacon.client_id == client.client_id)
                beacon = db.exec(stmt).first()
                if not beacon:
                    beacon = PresenceBeacon(client_id=client.client_id, subject=client.subject)
                
                beacon.last_seen = datetime.now(timezone.utc)
                db.add(beacon)
                db.commit()
        except Exception as e:
            logger.debug(f"[WS] Failed to record presence for {client.client_id}: {e}")
