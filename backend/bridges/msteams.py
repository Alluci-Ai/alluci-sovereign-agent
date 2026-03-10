import httpx
import os
import json
import asyncio
from typing import Dict, Any, List, Optional
from .base import BridgeAdapter
from datetime import datetime, timezone

class MSTeamsBridge(BridgeAdapter):
    """
    Sovereign MS Teams Bridge using Microsoft Graph API and MSAL.
    Ref: https://learn.microsoft.com/en-us/graph/api/chat-post-messages
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.user_id: Optional[str] = None

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
                data = res.json()
                self.user_id = data.get("id")
                self.is_connected = True
                self.logger.info(f"MS Teams Graph API session established for {data.get('userPrincipalName')}")
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
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        if not self.is_connected or not token:
            return {"status": "failed", "error": "Not connected"}
            
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.base_url}/chats/{recipient}/messages",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"body": {"content": content}}
            )
            
            if res.status_code == 201:
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "id": res.json().get("id")}
            else:
                self.last_error = res.text
                return {"status": "failed", "error": res.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def process_webhook(self, payload: Dict[str, Any]):
        """Standardized entry point for MS Teams / Bot Framework webhooks."""
        # Bot Framework Activity schema
        # Ref: https://learn.microsoft.com/en-us/azure/bot-service/rest-api/bot-framework-rest-connector-api-reference
        if payload.get("type") == "message":
            sender = payload.get("from", {}).get("id")
            if sender == self.user_id:
                return

            normalized = {
                "id": payload.get("id"),
                "from": sender,
                "body": payload.get("text", ""),
                "channel_id": payload.get("conversation", {}).get("id"),
                "protocol": "MSTEAMS",
                "timestamp": payload.get("localTimestamp") or datetime.now(timezone.utc).isoformat(),
                "raw": payload
            }
            await self._dispatch_inbound(normalized)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
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
                    "from": c.get("chatType"),
                    "body": c.get("lastMessagePreview", {}).get("body", {}).get("content", ""),
                    "timestamp": c.get("lastMessagePreview", {}).get("createdDateTime"),
                    "protocol": "MSTEAMS"
                } for c in chats]
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        health = super().get_health()
        if self.is_connected:
            health.update({
                "user_id": self.user_id,
                "api_version": "v1.0"
            })
        return health
