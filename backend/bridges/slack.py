import httpx
import os
import json
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter

# Constants for Slack OAuth
SLACK_OAUTH_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_OAUTH_TOKEN_URL = "https://slack.com/api/oauth.v2.access"

class SlackBridge(BridgeAdapter):
    """
    Production Slack Bridge using the Slack Web API.
    Supports OAuth 2.0 install flow, Events API, Block Kit messages, and workspace reporting.
    """

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.api_url = "https://slack.com/api"
        self.bot_token: str = ""
        self.default_channel: str = ""
        self.workspace_id: Optional[str] = None
        self.bot_user_id: Optional[str] = None
        self.client_id: Optional[str] = os.getenv("SLACK_CLIENT_ID")
        self.client_secret: Optional[str] = os.getenv("SLACK_CLIENT_SECRET")
        self.redirect_uri: Optional[str] = os.getenv("SLACK_REDIRECT_URI")

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        if not credentials:
            return False
            
        self.bot_token = credentials.get("access_token", credentials.get("bot_token", ""))
        self.default_channel = credentials.get("default_channel", self.default_channel)
        
        if not self.bot_token:
            return False

        # Validate token via auth.test
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.api_url}/auth.test",
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            data = res.json()
            if data.get("ok"):
                self.is_connected = True
                self.workspace_id = data.get("team_id")
                self.bot_user_id = data.get("user_id")
                self.logger.info(f"Slack Connected. Team: {data.get('team')} User: {data.get('user')}")
                return True
            else:
                self.logger.error(f"Slack auth failed: {data.get('error')}")
                self.is_connected = False
                return False

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        target = recipient if recipient else self.default_channel
        if not target:
            return {"status": "failed", "error": "No recipient specified"}

        payload: Dict[str, Any] = {"channel": target, "text": content}
        if kwargs.get("blocks"):
            payload["blocks"] = kwargs.get("blocks")

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.api_url}/chat.postMessage",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json=payload,
            )
            data = res.json()
            if data.get("ok"):
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "ts": data.get("ts")}
            else:
                self.last_error = data.get("error")
                return {"status": "failed", "error": data.get("error")}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def process_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Standardized entry point for Slack Events API."""
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            # Only handle channel messages (ignore bot messages, edits, etc.)
            if event.get("type") == "message" and not event.get("subtype"):
                if event.get("user") == self.bot_user_id:
                    return None # Ignore self

                normalized = {
                    "id": event.get("ts"),
                    "from": event.get("user"),
                    "body": event.get("text", ""),
                    "channel_id": event.get("channel"),
                    "protocol": "SLACK",
                    "account_id": self.workspace_id,
                    "timestamp": datetime.fromtimestamp(float(event.get("ts", "0")), timezone.utc).isoformat(),
                }
                await self._dispatch_inbound(normalized)
            return None
        return None

    async def validate_integrity(self) -> bool:
        if not self.bot_token: return False
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.api_url}/auth.test",
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            return res.json().get("ok", False)

    def get_health(self) -> Dict[str, Any]:
        health = super().get_health()
        if self.is_connected:
            health.update({
                "workspace_id": self.workspace_id,
                "bot_user_id": self.bot_user_id,
                "default_channel": self.default_channel
            })
        return health
