"""
Sovereign WhatsApp Adapter for Polytope Sovereign OS.
Integrates whatsapp-web.js via Node.js sidecar for personal account automation.

Provides:
- QR code streaming for pairing
- IDLE → QR_PENDING → CONNECTED → DISCONNECTED state machine
- Session state persistence using LocalAuth
- Inbound/Outbound text and media (images, docs)
- Stdout/Stdin JSON-RPC communication with sidecar

Reference: OpenClaw Section 2.1 (Sovereign Mode)
"""

import asyncio
import json
import os
import subprocess
import signal
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Callable
from collections import deque
from .base import BridgeAdapter

# ── PAIRING STATES ──────────────────────────────────────────────────────────
IDLE = "IDLE"
QR_PENDING = "QR_PENDING"
CONNECTED = "CONNECTED"
DISCONNECTED = "DISCONNECTED"

class WhatsAppBridge(BridgeAdapter):
    """
    WhatsApp Adapter using a Node.js sidecar (whatsapp-web.js).
    Supports QR pairing and full session persistence.
    """

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.connection_state = IDLE
        self._sidecar_process: Optional[asyncio.subprocess.Process] = None
        self._inbound_queue: deque = deque(maxlen=1000)
        self.last_qr: Optional[str] = None
        self.bot_info: Dict[str, Any] = {}
        self.last_activity: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.on_event: Optional[Callable[[str, Any], Any]] = None
        self.accounts: Dict[str, Dict[str, Any]] = {}
        self._monitor_task: Optional[asyncio.Task] = None

    async def connect(self, credentials: Dict[str, Any] = None) -> bool:
        """
        Starts the Node.js sidecar. Credentials not required for initial QR flow.
        """
        if self._sidecar_process and self._sidecar_process.returncode is None:
            self.logger.info("WhatsApp Sidecar already running.")
            return True

        self.logger.info("Launching WhatsApp Personal Sidecar...")
        sidecar_path = os.path.join(os.path.dirname(__file__), "wa_sidecar", "index.js")
        
        try:
            self._sidecar_process = await asyncio.create_subprocess_exec(
                "node", sidecar_path, self.bridge_id, self.vault_path,
                stdout=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self._monitor_task = asyncio.create_task(self._monitor_sidecar())
            self.connection_state = QR_PENDING
            return True
        except Exception as e:
            self.last_error = f"Failed to spawn Node.js sidecar: {e}"
            self.logger.error(self.last_error)
            self.connection_state = DISCONNECTED
            return False

    async def _monitor_sidecar(self):
        """Monitor stdout and stderr from the Node.js sidecar."""
        async def read_stdout():
            while self._sidecar_process and self._sidecar_process.stdout:
                line = await self._sidecar_process.stdout.readline()
                if not line: break
                try:
                    payload = json.loads(line.decode().strip())
                    await self._handle_sidecar_event(payload)
                except Exception as e:
                    self.logger.debug(f"Non-JSON or corrupt from sidecar: {line.decode().strip()} ({e})")

        async def read_stderr():
            while self._sidecar_process and self._sidecar_process.stderr:
                line = await self._sidecar_process.stderr.readline()
                if not line: break
                self.logger.debug(f"[SIDECAR_LOG] {line.decode().strip()}")

        await asyncio.gather(read_stdout(), read_stderr())

    async def _handle_sidecar_event(self, payload: Dict[str, Any]):
        """Dispatch JSON-RPC events from the sidecar."""
        method = payload.get("method")
        params = payload.get("params", {})

        if method == "qr":
            self.last_qr = params.get("qr")
            self.connection_state = QR_PENDING
            self.logger.info("New QR Code received from sidecar.")
            if self.on_event:
                await self.on_event("whatsapp.qr", {"qr": self.last_qr})

        elif method == "ready":
            self.is_connected = True
            self.connection_state = CONNECTED
            self.bot_info = params.get("info", {})
            self.last_qr = None
            self.logger.info(f"WhatsApp Connected: {self.bot_info.get('pushname')}")
            if self.on_event:
                await self.on_event("whatsapp.ready", self.bot_info)

        elif method == "status":
            state = params.get("state")
            self.connection_state = state if state in [IDLE, QR_PENDING, CONNECTED, DISCONNECTED] else self.connection_state
            if state == "DISCONNECTED":
                self.is_connected = False
            self.logger.info(f"WhatsApp State Change: {self.connection_state}")

        elif method == "message":
            msg = params.get("msg")
            if msg:
                self._inbound_queue.append(msg)
                self.last_activity = datetime.now(timezone.utc)
                # Track account
                sender = msg.get("from")
                self.accounts[sender] = {
                    "chat_id": sender,
                    "name": msg.get("from_name"),
                    "last_seen": datetime.now(timezone.utc).isoformat()
                }
                if self.on_event:
                    await self.on_event("whatsapp.message", msg)

        elif method == "auth_failure":
            self.last_error = params.get("message")
            self.connection_state = DISCONNECTED
            self.logger.error(f"WhatsApp Auth Failure: {self.last_error}")

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Legacy text send (WhatsApp)."""
        return await self.send(recipient, content)

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Sovereign send method (WhatsApp)."""
        if not self.is_connected or not self._sidecar_process:
            return {"status": "failed", "error": "Bridge not connected"}

        cmd = {
            "jsonrpc": "2.0",
            "method": "send_message",
            "params": {"to": recipient, "body": content},
            "id": f"send_{int(datetime.now().timestamp())}"
        }
        try:
            self._sidecar_process.stdin.write((json.dumps(cmd) + "\n").encode())
            await self._sidecar_process.stdin.drain()
            self.last_activity = datetime.now(timezone.utc)
            return {"status": "success", "sent_at": self.last_activity.isoformat()}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def send_media(self, recipient: str, mimetype: str, data: str, filename: str = None, caption: str = None) -> Dict[str, Any]:
        """Send media (image/doc) to the sidecar's stdin."""
        if not self.is_connected or not self._sidecar_process:
            return {"status": "failed", "error": "Bridge not connected"}

        cmd = {
            "jsonrpc": "2.0",
            "method": "send_media",
            "params": {
                "to": recipient,
                "mimetype": mimetype,
                "data": data,
                "filename": filename,
                "caption": caption
            },
            "id": f"send_media_{int(datetime.now().timestamp())}"
        }
        try:
            self._sidecar_process.stdin.write((json.dumps(cmd) + "\n").encode())
            await self._sidecar_process.stdin.drain()
            self.last_activity = datetime.now(timezone.utc)
            return {"status": "success", "sent_at": self.last_activity.isoformat()}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return queued inbound messages."""
        messages = []
        while self._inbound_queue and len(messages) < limit:
            messages.append(self._inbound_queue.popleft())
        return messages

    async def validate_integrity(self) -> bool:
        if not self._sidecar_process or self._sidecar_process.returncode is not None:
            return False
        return self.is_connected

    async def disconnect(self):
        if self._sidecar_process:
            try:
                self._sidecar_process.terminate()
                await self._sidecar_process.wait()
            except: pass
        self.is_connected = False
        self.connection_state = DISCONNECTED

    def get_health(self) -> Dict[str, Any]:
        """Health Report for Dashboard."""
        return {
            "channel": "whatsapp",
            "connected": self.is_connected,
            "state": self.connection_state,
            "bot_name": self.bot_info.get("pushname"),
            "wid": self.bot_info.get("wid"),
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "last_error": self.last_error,
            "account_count": len(self.accounts),
            "pending_qr": bool(self.last_qr),
            "accounts": list(self.accounts.values())
        }
