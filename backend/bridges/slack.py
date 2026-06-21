import os
import json
import asyncio
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter

from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler

class SlackBridge(BridgeAdapter):
    """
    Production Slack Bridge using slack_bolt in Socket Mode.
    Provides a seamless, secure connection without requiring public IP or ngrok.
    """

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.bot_token: str = ""
        self.app_token: str = ""
        self.default_channel: str = ""
        self.workspace_id: Optional[str] = None
        self.bot_user_id: Optional[str] = None
        
        self.app: Optional[AsyncApp] = None
        self.handler: Optional[AsyncSocketModeHandler] = None
        self._listener_task: Optional[asyncio.Task] = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        if not credentials:
            return False
            
        self.bot_token = credentials.get("bot_token", "")
        self.app_token = credentials.get("app_token", "")
        self.default_channel = credentials.get("default_channel", "")
        
        if not self.bot_token or not self.app_token:
            self.logger.error("[SLACK] Missing bot_token or app_token for Socket Mode.")
            return False

        try:
            self.app = AsyncApp(token=self.bot_token)
            
            # Fetch bot identity to ignore our own messages
            auth_test = await self.app.client.auth_test()
            self.bot_user_id = auth_test.get("user_id")
            self.workspace_id = auth_test.get("team_id")
            
            # Register message listener
            @self.app.message(".*")
            async def handle_messages(message, say, logger):
                if message.get("user") == self.bot_user_id:
                    return # Ignore self

                # Ignore edits/deletions for now to prevent duplicate triggers
                if message.get("subtype"):
                    return
                    
                normalized = {
                    "id": message.get("ts"),
                    "from": message.get("user"),
                    "body": message.get("text", ""),
                    "channel_id": message.get("channel"),
                    "protocol": "SLACK",
                    "account_id": self.workspace_id,
                    "timestamp": datetime.fromtimestamp(float(message.get("ts", "0")), timezone.utc).isoformat(),
                }
                if hasattr(self, "_dispatch_inbound"):
                    await self._dispatch_inbound(normalized)

            # Start Socket Mode
            self.handler = AsyncSocketModeHandler(self.app, self.app_token)
            self._listener_task = asyncio.create_task(self.handler.start_async())
            
            self.is_connected = True
            self.logger.info(f"Slack Socket Mode Connected. Team: {self.workspace_id} Bot User: {self.bot_user_id}")
            
            # Broadcast status if UI is listening
            if self.on_event:
                asyncio.create_task(self.on_event("bridge.status", {
                    "bridge_id": self.bridge_id,
                    "status": "CONNECTED"
                }))
                
            return True
            
        except Exception as e:
            self.logger.error(f"Slack Socket Mode connection failed: {e}")
            self.is_connected = False
            return False

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not self.app:
            return {"status": "failed", "error": "Bridge Disconnected"}

        target = recipient if recipient else self.default_channel
        if not target:
            return {"status": "failed", "error": "No recipient specified"}

        payload: Dict[str, Any] = {"channel": target, "text": content}
        if kwargs.get("blocks"):
            payload["blocks"] = kwargs["blocks"]
        if kwargs.get("thread_ts"):
            payload["thread_ts"] = kwargs["thread_ts"]

        try:
            res = await self.app.client.chat_postMessage(**payload)
            if res.get("ok"):
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "ts": res.get("ts"), "channel": res.get("channel")}
            self.last_error = res.get("error")
            return {"status": "failed", "error": res.get("error")}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def validate_integrity(self) -> bool:
        if not self.app: return False
        try:
            res = await self.app.client.auth_test()
            return res.get("ok", False)
        except Exception:
            return False

    def get_health(self) -> Dict[str, Any]:
        health = super().get_health()
        if self.is_connected:
            health.update({
                "workspace_id": self.workspace_id,
                "bot_user_id": self.bot_user_id,
                "default_channel": self.default_channel
            })
        return health
