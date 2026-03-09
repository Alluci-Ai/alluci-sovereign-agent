import httpx
import os
from typing import Dict, Any, List
from .base import BridgeAdapter

class FacebookBridge(BridgeAdapter):
    """
    Sovereign Facebook Bridge using Graph API Messenger.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.version}"

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.credentials = credentials
        token = credentials.get("access_token")
        if not token:
            return False
            
        # In a full flow, we might exchange for a long-lived token here
        self.is_connected = True
        self.logger.info(f"Facebook Graph API session established for account {self.bridge_id}")
        return True

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Sends a message via the Messenger API to a Page-Scoped ID (PSID).
        """
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
                return {"status": "success", "id": resp.json().get("message_id")}
            else:
                self.logger.error(f"Facebook send failed: {resp.text}")
                return {"status": "failed", "error": resp.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch conversations and their recent messages."""
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

    async def validate_integrity(self) -> bool:
        return self.is_connected
