import httpx
import os
import json
from typing import Dict, Any, List
from .base import BridgeAdapter

class MSTeamsBridge(BridgeAdapter):
    """
    Sovereign MS Teams Bridge using Microsoft Graph API and MSAL.
    Ref: https://learn.microsoft.com/en-us/graph/api/chat-post-messages
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.base_url = "https://graph.microsoft.com/v1.0"

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.credentials = credentials
        token = credentials.get("access_token")
        if not token:
            return False
            
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{self.base_url}/me",
                headers={"Authorization": f"Bearer {token}"}
            )
            if res.status_code == 200:
                self.is_connected = True
                self.logger.info(f"MS Teams Graph API session established for account {self.bridge_id}")
                return True
            elif res.status_code == 401 and credentials.get("refresh_token"):
                self.is_connected = True
                return True
        return False

    async def _ensure_auth(self):
        """Standardizes token refresh for Microsoft."""
        client_id = self.credentials.get("client_id") or os.getenv("MSTEAMS_CLIENT_ID")
        client_secret = self.credentials.get("client_secret") or os.getenv("MSTEAMS_CLIENT_SECRET")
        
        if not client_id or not self.credentials.get("refresh_token"):
            return
            
        try:
            # Microsoft uses a common endpoint or tenant-specific one
            token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
            self.credentials = await self._get_valid_token(
                self.credentials, 
                token_url,
                client_id,
                client_secret
            )
        except Exception as e:
            self.logger.error(f"Failed to refresh Microsoft token: {e}")

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Sends a message to a Chat or Channel.
        Recipient is expected to be a Chat ID or Channel ID.
        """
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        if not self.is_connected or not token:
            return {"status": "failed", "error": "Not connected"}
            
        async with httpx.AsyncClient() as client:
            # POST message to a specific chat/channel
            res = await client.post(
                f"{self.base_url}/chats/{recipient}/messages",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"body": {"content": content}}
            )
            
            if res.status_code == 201:
                return {"status": "success", "id": res.json().get("id")}
            else:
                return {"status": "failed", "error": res.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent messages from the user's chats."""
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        if not self.is_connected or not token:
            return []
            
        async with httpx.AsyncClient() as client:
            res = await client.get(
                f"{self.base_url}/me/chats",
                headers={"Authorization": f"Bearer {token}"},
                params={"$top": limit, "$expand": "lastMessagePreview"}
            )
            if res.status_code == 200:
                chats = res.json().get("value", [])
                return [{
                    "id": c["id"],
                    "sender": c.get("chatType"),
                    "snippet": c.get("lastMessagePreview", {}).get("body", {}).get("content", ""),
                    "timestamp": c.get("lastMessagePreview", {}).get("createdDateTime")
                } for c in chats]
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected
