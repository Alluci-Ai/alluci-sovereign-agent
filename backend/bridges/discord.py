import httpx
import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select
from .base import BridgeAdapter
from ..database import engine as db_engine

class DiscordBridge(BridgeAdapter):
    """
    Discord Bot adapter using a Node.js sidecar (discord.js) for high-fidelity 
    Gateway interactions (OpenClaw §2.3).
    """

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.bot_token: str = ""
        self.bot_user: Dict[str, Any] = {}
        self.guilds: List[Dict[str, Any]] = []
        self.last_activity: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.enabled: bool = True
        self.on_event = None # Callback for orchestrator
        
        self._sidecar_process: Optional[asyncio.subprocess.Process] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._pending_rpcs: Dict[str, asyncio.Future] = {}

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Spawn the Node.js sidecar and login with bot_token."""
        self.bot_token = credentials.get("bot_token", "")
        if not self.bot_token:
            self.last_error = "Missing bot_token"
            return False

        if self._sidecar_process and self._sidecar_process.returncode is None:
            self.logger.info("Discord Sidecar already running.")
        else:
            sidecar_path = os.path.join(os.path.dirname(__file__), "ds_sidecar", "index.js")
            try:
                self._sidecar_process = await asyncio.create_subprocess_exec(
                    "node", sidecar_path, self.bridge_id, self.vault_path,
                    stdout=asyncio.subprocess.PIPE,
                    stdin=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                self._monitor_task = asyncio.create_task(self._monitor_sidecar())
            except Exception as e:
                self.last_error = f"Sidecar spawn failed: {e}"
                return False

        # Send login command
        await self._send_rpc("login", {"token": self.bot_token})
        return True

    async def _monitor_sidecar(self):
        """Read JSON-RPC events from sidecar stdout."""
        while self._sidecar_process and self._sidecar_process.stdout:
            line = await self._sidecar_process.stdout.readline()
            if not line: break
            try:
                payload = json.loads(line.decode().strip())
                await self._handle_sidecar_event(payload)
            except Exception as e:
                self.logger.debug(f"DS Sidecar Non-JSON: {line.decode().strip()} ({e})")
        
        # Read stderr for debugging
        if self._sidecar_process and self._sidecar_process.stderr:
            err = await self._sidecar_process.stderr.read()
            if err:
                self.logger.error(f"DS Sidecar Error: {err.decode()}")

    async def _handle_sidecar_event(self, payload: Dict[str, Any]):
        method = payload.get("method")
        params = payload.get("params", {})

        if method == "ready":
            self.is_connected = True
            self.bot_user = params.get("user", {})
            self.guilds = params.get("guilds", [])
            self.logger.info(f"Discord Sidecar Ready: {self.bot_user.get('tag')}")
            # Update mappings in DB based on current guilds
            self._sync_guilds_to_db()
        elif method == "message":
            msg = params.get("msg", {})
            if self.on_event:
                await self.on_event("message", msg)
        elif method == "interaction":
            interaction = params.get("interaction", {})
            if self.on_event:
                # Route interactions as objectives
                await self.on_event("message", {
                    "from": interaction.get("user_id"),
                    "from_name": interaction.get("user"),
                    "body": f"Slash Command: /{interaction.get('command')}",
                    "protocol": "DISCORD",
                    "channel_id": interaction.get("channel_id")
                })
        elif method == "response":
            rpc_id = payload.get("id")
            if rpc_id in self._pending_rpcs:
                self._pending_rpcs[rpc_id].set_result(params)

    def _sync_guilds_to_db(self):
        """Ensure all joined guilds have a mapping entry."""
        from ..models import DiscordGuildMapping
        with Session(db_engine) as session:
            for g in self.guilds:
                stmt = select(DiscordGuildMapping).where(DiscordGuildMapping.guild_id == g["id"])
                existing = session.exec(stmt).first()
                if not existing:
                    mapping = DiscordGuildMapping(
                        guild_id=g["id"],
                        guild_name=g["name"],
                        default_channel_id=g["channels"][0]["id"] if g["channels"] else None
                    )
                    session.add(mapping)
            session.commit()

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Send a message. If recipient is a guild_id, it uses the mapped default channel.
        Supports 'embeds' in kwargs.
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Not connected"}

        channel_id = recipient
        # Check if recipient is a guild ID that needs mapping
        if recipient.startswith("guild_") or len(recipient) == 18 or len(recipient) == 19:
            # Simple heuristic or lookup
            from ..models import DiscordGuildMapping
            with Session(db_engine) as session:
                mapping = session.exec(select(DiscordGuildMapping).where(DiscordGuildMapping.guild_id == recipient)).first()
                if mapping and mapping.default_channel_id:
                    channel_id = mapping.default_channel_id

        rpc_params = {
            "to": channel_id,
            "body": content,
            "embeds": kwargs.get("embeds", [])
        }
        
        return await self._send_rpc("send_message", rpc_params)

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def register_commands(self, guild_id: str, commands: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Register slash commands via sidecar."""
        return await self._send_rpc("register_commands", {"guild_id": guild_id, "commands": commands})

    async def _send_rpc(self, method: str, params: Dict[str, Any]) -> Any:
        if not self._sidecar_process or not self._sidecar_process.stdin:
            return {"status": "failed", "error": "Sidecar inactive"}
        
        rpc_id = f"rpc_{int(datetime.now().timestamp() * 1000)}"
        future = asyncio.get_event_loop().create_future()
        self._pending_rpcs[rpc_id] = future

        msg = JSON_RPC_Message(id=rpc_id, method=method, params=params)
        self._sidecar_process.stdin.write((json.dumps(msg) + "\n").encode())
        await self._sidecar_process.stdin.drain()

        try:
            return await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            return {"status": "failed", "error": "RPC Timeout"}
        finally:
            self._pending_rpcs.pop(rpc_id, None)

    async def validate_integrity(self) -> bool:
        return self.is_connected

    async def disconnect(self):
        if self._sidecar_process:
            self._sidecar_process.terminate()
            await self._sidecar_process.wait()
        self.is_connected = False

    def get_health(self) -> Dict[str, Any]:
        """Return health report for channel dashboard."""
        return {
            "channel": "discord",
            "connected": self.is_connected,
            "enabled": self.enabled,
            "bot_username": self.bot_user.get("tag") or "Connecting...",
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "last_error": self.last_error,
            "guild_count": len(self.guilds),
            "guilds": [
                {"id": g["id"], "name": g["name"], "channel_count": len(g.get("channels", []))}
                for g in self.guilds
            ],
        }

def JSON_RPC_Message(id, method, params):
    return {"jsonrpc": "2.0", "id": id, "method": method, "params": params}
