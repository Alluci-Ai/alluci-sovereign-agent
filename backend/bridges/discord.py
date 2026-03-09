import asyncio
from typing import Dict, Any, List
from .base import BridgeAdapter
import logging

class DiscordBridge(BridgeAdapter):
    """
    Sovereign Discord Bridge.
    Pure Python implementation using discord.py.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.client = None
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
        self.client = discord.Client(intents=intents)

        @self.client.event
        async def on_ready():
            self.is_connected = True
            self.logger.info(f"Discord connected as {self.client.user}")

        # Start the client in the background
        self.task = asyncio.create_task(self.client.start(self.bot_token))
        
        # Wait a bit for connection
        for _ in range(10):
            if self.is_connected: break
            await asyncio.sleep(1)
            
        return self.is_connected

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return {"status": "failed", "error": "Not connected"}
            
        try:
            # 1. Try fetching as a channel
            target = self.client.get_channel(int(recipient))
            
            # 2. Try fetching as a user (for DMs)
            if not target:
                target = await self.client.fetch_user(int(recipient))
                
            if not target:
                return {"status": "failed", "error": f"Target {recipient} not found"}
                
            await target.send(content)
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"Discord send failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent history from default/last channels."""
        if not self.is_connected or not self.client:
            return []
            
        messages = []
        # In a real bot, we'd look at channels we have permission for
        for guild in self.client.guilds:
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
        return self.is_connected and not self.client.is_closed()

    async def disconnect(self):
        if self.client:
            await self.client.close()
        if self.task:
            self.task.cancel()
        self.is_connected = False
