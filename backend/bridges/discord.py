import asyncio
from typing import Dict, Any, List
from .base import BridgeAdapter
import logging

class DiscordBridge(BridgeAdapter):
    """
    Sovereign Discord Bridge.
    Pure Python implementation using discord.py, removing Node.js ds_sidecar dependency.
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

        self.bot_token = credentials.get("bot_token")
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

        @self.client.event
        async def on_message(message):
            if message.author == self.client.user:
                return
            # Pass to orchestrator in production

        self.task = asyncio.create_task(self.client.start(self.bot_token))
        return True

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not self.client:
            return {"status": "failed", "error": "Not connected"}
            
        try:
            channel = self.client.get_channel(int(recipient))
            if not channel:
                return {"status": "failed", "error": "Channel not found"}
            await channel.send(content)
            return {"status": "success"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected

    async def disconnect(self):
        if self.client:
            await self.client.close()
        if self.task:
            self.task.cancel()
        self.is_connected = False
