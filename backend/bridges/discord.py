"""
Discord Bot Adapter for the Polytope Sovereign OS.

Provides:
- Bot token authentication via Discord HTTP API
- Guild/channel enumeration
- Message send/receive with embed formatting
- Slash command support
- Health reporting for channel dashboard

Reference: OpenClaw Section 2.3
"""

import httpx
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter


class DiscordBridge(BridgeAdapter):
    """
    Discord Bot adapter using the HTTP API (no discord.py dependency).
    """

    API_BASE = "https://discord.com/api/v10"

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.bot_token: str = ""
        self.application_id: str = ""
        self.bot_username: str = ""
        self.guilds: Dict[str, Dict[str, Any]] = {}
        self.last_activity: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.enabled: bool = True

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
        }

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Validate bot token by calling /users/@me.
        Fetches guild list on success.
        """
        self.bot_token = credentials.get("bot_token", "")
        if not self.bot_token:
            self.last_error = "Missing bot_token"
            return False

        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.API_BASE}/users/@me", headers=self._headers())
                data = res.json()

                if "id" not in data:
                    self.last_error = data.get("message", "Token validation failed")
                    return False

                self.application_id = data["id"]
                self.bot_username = f"{data.get('username', '')}#{data.get('discriminator', '0')}"
                self.is_connected = True
                self.last_activity = datetime.now(timezone.utc)

                # Fetch guilds
                await self._fetch_guilds(client)

                self.logger.info(f"Discord Connected. Bot: {self.bot_username}, Guilds: {len(self.guilds)}")
                return True

        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Discord connection failed: {e}")
            return False

    async def _fetch_guilds(self, client: httpx.AsyncClient):
        """Fetch all guilds the bot is a member of."""
        try:
            res = await client.get(f"{self.API_BASE}/users/@me/guilds", headers=self._headers())
            guilds = res.json()
            if isinstance(guilds, list):
                for g in guilds:
                    self.guilds[g["id"]] = {
                        "id": g["id"],
                        "name": g["name"],
                        "icon": g.get("icon"),
                        "channels": [],
                    }
                    # Fetch channels for each guild
                    ch_res = await client.get(
                        f"{self.API_BASE}/guilds/{g['id']}/channels",
                        headers=self._headers(),
                    )
                    channels = ch_res.json()
                    if isinstance(channels, list):
                        self.guilds[g["id"]]["channels"] = [
                            {"id": c["id"], "name": c["name"], "type": c["type"]}
                            for c in channels
                            if c.get("type") == 0  # text channels only
                        ]
        except Exception as e:
            self.logger.warning(f"Failed to fetch guilds: {e}")

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """
        Send a message to a Discord channel.
        `recipient` is the channel_id.
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.API_BASE}/channels/{recipient}/messages",
                    headers=self._headers(),
                    json={"content": content},
                )
                data = res.json()
                status = "success" if "id" in data else "failed"

                if status == "success":
                    self.last_activity = datetime.now(timezone.utc)

                self._persist_to_vault("sent", {
                    "channel_id": recipient,
                    "content": content[:200],
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                return {"status": status, "response": data}
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Discord send_message failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def send_embed(self, channel_id: str, title: str, description: str,
                         color: int = 0x5865F2, fields: list = None) -> Dict[str, Any]:
        """Send a rich embed message to a Discord channel."""
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        embed: Dict[str, Any] = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        if fields:
            embed["fields"] = fields

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.API_BASE}/channels/{channel_id}/messages",
                    headers=self._headers(),
                    json={"embeds": [embed]},
                )
                data = res.json()
                return {"status": "success" if "id" in data else "failed", "response": data}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Discord bots receive messages via Gateway/webhooks, not polling."""
        return []

    def process_interaction(self, interaction: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incoming Discord interaction (slash command, button, etc.)."""
        self.last_activity = datetime.now(timezone.utc)

        parsed = {
            "id": interaction.get("id"),
            "type": interaction.get("type"),
            "guild_id": interaction.get("guild_id"),
            "channel_id": interaction.get("channel_id"),
            "user": interaction.get("member", {}).get("user", {}).get("username"),
            "protocol": "DISCORD",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if interaction.get("type") == 2:  # APPLICATION_COMMAND
            cmd_data = interaction.get("data", {})
            parsed["command"] = cmd_data.get("name")
            parsed["options"] = cmd_data.get("options", [])

        self._persist_to_vault("inbox", parsed)
        return parsed

    async def register_slash_command(self, guild_id: str, name: str,
                                     description: str) -> Dict[str, Any]:
        """Register a slash command for a guild."""
        if not self.is_connected:
            return {"status": "failed", "error": "Not connected"}

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.API_BASE}/applications/{self.application_id}/guilds/{guild_id}/commands",
                    headers=self._headers(),
                    json={"name": name, "description": description, "type": 1},
                )
                data = res.json()
                return {"status": "success" if "id" in data else "failed", "response": data}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        """Return health report for channel dashboard."""
        return {
            "channel": "discord",
            "connected": self.is_connected,
            "enabled": self.enabled,
            "bot_username": self.bot_username,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "last_error": self.last_error,
            "guild_count": len(self.guilds),
            "guilds": [
                {"id": g["id"], "name": g["name"], "channel_count": len(g.get("channels", []))}
                for g in self.guilds.values()
            ],
        }

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
