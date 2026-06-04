import asyncio
import logging
from typing import Dict, Any, List, Optional
from .base import BridgeAdapter

class DiscordBridge(BridgeAdapter):
    """
    Sovereign Discord Bridge.
    Pure Python implementation using discord.py.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.client = None  # type: ignore
        self.bot_token = None
        self.task = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        try:
            import discord
        except ImportError:
            self.logger.error("discord.py missing. Run: pip install discord.py")
            return False

        self.bot_token = credentials.get("bot_token") or credentials.get("access_token")
        if not self.bot_token:
            self.logger.error("Missing bot_token in credentials")
            return False

        intents = discord.Intents.default()
        intents.message_content = True
        self.client = discord.Client(intents=intents)  # type: ignore

        @self.client.event  # type: ignore
        async def on_ready():
            self.is_connected = True
            self.logger.info(f"Discord connected as {self.client.user}")  # type: ignore

        @self.client.event  # type: ignore
        async def on_message(message):
            if message.author == self.client.user:  # type: ignore
                return
            
            # Standardization into the unified inbound pipeline
            await self._dispatch_inbound({
                "from": str(message.author),
                "body": message.content,
                "channel_id": str(message.channel.id),
                "channel_name": getattr(message.channel, 'name', 'DM'),
                "guild": str(getattr(message.channel, 'guild', 'DM')),
                "timestamp": message.created_at.isoformat(),
                "attachments": [a.url for a in message.attachments]
            })

        # Start the client in the background
        self.task = asyncio.create_task(self.client.start(self.bot_token))  # type: ignore
        
        # Wait for connection
        for _ in range(15):
            if self.is_connected: break
            await asyncio.sleep(1)
            
        return self.is_connected

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return {"status": "failed", "error": "Not connected"}
            
        try:
            # 1. Try fetching as a channel
            try:
                target = self.client.get_channel(int(recipient))  # type: ignore
            except (ValueError, TypeError):
                target = None
            
            # 2. Try fetching as a user (for DMs)
            if not target:
                try:
                    target = await self.client.fetch_user(int(recipient))  # type: ignore
                except (ValueError, TypeError):
                    target = None
                
            if not target:
                return {"status": "failed", "error": f"Target {recipient} not found"}
                
            msg = await target.send(content)
            self.last_activity = str(int(asyncio.get_event_loop().time()))
            return {"status": "success", "id": str(msg.id)}
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Discord send failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent history if polling is required (though events are preferred)."""
        if not self.is_connected or not self.client:
            return []
            
        messages = []
        for guild in self.client.guilds:  # type: ignore
            for channel in guild.text_channels:
                try:
                    async for msg in channel.history(limit=limit):
                        messages.append({
                            "id": str(msg.id),
                            "from": str(msg.author),
                            "body": msg.content,
                            "channel": channel.name,
                            "guild": guild.name,
                            "timestamp": msg.created_at.isoformat()
                        })
                except:
                    continue
        return messages[:limit]

    async def validate_integrity(self) -> bool:
        return self.is_connected and not self.client.is_closed()  # type: ignore

    def get_health(self) -> Dict[str, Any]:
        """Enhanced Discord health reporting."""
        health = super().get_health()
        if self.client and self.is_connected:
            health.update({
                "latency_ms": int(self.client.latency * 1000) if self.client.latency else 0,  # type: ignore
                "guild_count": len(self.client.guilds),  # type: ignore
                "user": str(self.client.user)  # type: ignore
            })
        return health

    async def disconnect(self):
        if self.client:
            await self.client.close()  # type: ignore
        if self.task:
            self.task.cancel()
        self.is_connected = False
