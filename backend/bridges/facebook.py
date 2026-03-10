import httpx
import os
import asyncio
from typing import Dict, Any, List
from .base import BridgeAdapter

class FacebookBridge(BridgeAdapter):
    """
    Sovereign Facebook Bridge using Graph API Messenger.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.version = "v20.0"
        self.base_url = f"https://graph.facebook.com/{self.version}"
        self.credentials = {}

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.credentials = credentials
        token = credentials.get("access_token")
        if not token:
            return False
            
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.base_url}/me", params={"access_token": token})
                if res.status_code == 200:
                    self.is_connected = True
                    self.logger.info(f"Facebook session established for {self.bridge_id}")
                    return True
        except Exception as e:
            self.logger.error(f"Facebook connection failed: {e}")
            
        return False

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Sends a message via the Messenger API."""
        if not self.is_connected:
            return {"status": "failed", "error": "Not connected"}
            
        token = self.credentials.get("access_token")
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/me/messages",
                params={"access_token": token},
                json={
                    "recipient": {"id": recipient},
                    "message": {"text": content}
                }
            )
            
            if resp.status_code == 200:
                self.last_activity = str(int(asyncio.get_event_loop().time()))
                return {"status": "success", "id": resp.json().get("message_id")}
            else:
                self.last_error = resp.text
                return {"status": "failed", "error": resp.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch conversations. Requires webhooks for real-time messages."""
        token = self.credentials.get("access_token")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/me/conversations",
                params={
                    "access_token": token, 
                    "fields": "messages.limit(1){message,from,created_time},participants", 
                    "limit": limit
                }
            )
            if resp.status_code == 200:
                return resp.json().get("data", [])
            return []

    async def process_webhook(self, data: Dict[str, Any]):
        """Standardized entry point for Facebook Messenger webhooks."""
        try:
            for entry in data.get("entry", []):
                for messaging_event in entry.get("messaging", []):
                    if messaging_event.get("message"):
                        sender_id = messaging_event["sender"]["id"]
                        message_data = messaging_event["message"]
                        body = message_data.get("text", "[Media/Attachment]")
                        
                        await self._dispatch_inbound({
                            "from": sender_id,
                            "body": body,
                            "timestamp": messaging_event.get("timestamp"),
                            "id": message_data.get("mid"),
                            "account_id": entry.get("id"),
                            "raw": messaging_event
                        })
        except Exception as e:
            self.logger.error(f"Facebook webhook parse failed: {e}")

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        """Health reporting for Facebook Messenger."""
        health = super().get_health()
        if self.is_connected:
            health.update({
                "api_version": self.version,
                "verified": True
            })
        return health
