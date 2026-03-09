import httpx
import os
import json
from typing import Dict, Any, List
from .base import BridgeAdapter

class InstagramBridge(BridgeAdapter):
    """
    Sovereign Instagram Bridge.
    Uses Graph API for Business/Creator (DMs).
    Ref: https://developers.facebook.com/docs/messenger-platform/instagram
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
            
        async with httpx.AsyncClient() as client:
            # Verify token via me/accounts (needs instagram_manage_messages scope)
            res = await client.get(
                f"{self.base_url}/me",
                params={"access_token": token}
            )
            if res.status_code == 200:
                self.is_connected = True
                self.logger.info(f"Instagram session established for account {self.bridge_id}")
                return True
            elif res.status_code == 401 and credentials.get("refresh_token"):
                self.is_connected = True
                return True
        return False

    async def _ensure_auth(self):
        """Standardizes token refresh for Meta/Instagram."""
        client_id = self.credentials.get("client_id") or os.getenv("FACEBOOK_CLIENT_ID")
        client_secret = self.credentials.get("client_secret") or os.getenv("FACEBOOK_CLIENT_SECRET")
        
        if not client_id or not self.credentials.get("refresh_token"):
            return
            
        try:
            token_url = f"https://graph.facebook.com/{self.version}/oauth/access_token"
            self.credentials = await self._get_valid_token(
                self.credentials, 
                token_url,
                client_id,
                client_secret
            )
        except Exception as e:
            self.logger.error(f"Failed to refresh Instagram token: {e}")

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        if not self.is_connected or not token:
            return {"status": "failed", "error": "Not connected"}
            
        payload = {
            "recipient": {"id": recipient},
            "message": {"text": content}
        }
        
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/me/messages",
                headers={"Authorization": f"Bearer {token}"},
                json=payload
            )
            if res.status_code == 200:
                return {"status": "success", "id": res.json().get("message_id")}
            return {"status": "failed", "error": res.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        if not self.is_connected or not token:
            return []
            
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{self.base_url}/me/conversations",
                params={"access_token": token, "limit": limit}
            )
            if res.status_code == 200:
                conversations = res.json().get("data", [])
                # Further expansion would fetch messages per conversation
                return [{"id": c["id"], "sender": "Instagram User"} for c in conversations]
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected
