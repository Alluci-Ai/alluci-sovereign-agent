import httpx
import time
import os
from typing import Dict, Any, List
from .base import BridgeAdapter

class XBridge(BridgeAdapter):
    """
    Sovereign X (Twitter) Bridge using OAuth 2.0 PKCE and X v2 API.
    Ref: https://developer.twitter.com/en/docs/twitter-api/tweets/manage-tweets/api-reference/post-tweets
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.base_url = "https://api.twitter.com/2"

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.credentials = credentials
        token = credentials.get("access_token")
        if not token:
            return False
            
        self.is_connected = True
        self.logger.info(f"X (Twitter) session initialized for account {self.bridge_id}")
        return True

    async def _ensure_auth(self):
        """Standardizes token refresh for X."""
        client_id = self.credentials.get("client_id") or os.getenv("TWITTER_CLIENT_ID")
        client_secret = self.credentials.get("client_secret") or os.getenv("TWITTER_CLIENT_SECRET")
        
        if not client_id:
            return
            
        try:
            self.credentials = await self._get_valid_token(
                self.credentials, 
                "https://api.twitter.com/2/oauth2/token",
                client_id,
                client_secret
            )
        except Exception as e:
            self.logger.error(f"Failed to refresh X token: {e}")

    @BridgeAdapter.resilient_request
    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Posts a Tweet. If a recipient is provided as a numeric ID, it attempts a DM.
        Defaults to public Tweet for general 'send' actions.
        """
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        
        # 1. Check if recipient is a numeric ID (DM flow)
        if recipient and recipient.isdigit():
            return await self._send_dm(recipient, content)

        # 2. Default: POST a Tweet
        resp = await self.client.post(
            f"{self.base_url}/tweets",
            json={"text": content},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        
        if resp.status_code == 201:
            data = resp.json()
            return {"status": "success", "id": data["data"]["id"]}
        else:
            return {"status": "failed", "error": resp.text}

    @BridgeAdapter.resilient_request
    async def _send_dm(self, recipient_id: str, content: str) -> Dict[str, Any]:
        """Specific DM implementation for X v2."""
        token = self.credentials.get("access_token")
        resp = await self.client.post(
            f"{self.base_url}/dm_conversations/with/{recipient_id}/messages",
            json={"text": content},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        if resp.status_code == 201:
            return {"status": "success", "type": "dm"}
        return {"status": "failed", "error": resp.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    @BridgeAdapter.resilient_request
    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch mentions for the authenticated user."""
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        
        # We first need the user ID
        me_resp = await self.client.get(f"{self.base_url}/users/me", headers={"Authorization": f"Bearer {token}"})
        if me_resp.status_code != 200:
            return []
        my_id = me_resp.json()["data"]["id"]

        resp = await self.client.get(
            f"{self.base_url}/users/{my_id}/mentions",
            params={"max_results": min(limit, 100)},
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", [])
        return []

    async def validate_integrity(self) -> bool:
        """Verify session by performing a lightweight /me check."""
        if not self.is_connected or not self.credentials.get("access_token"):
            return False
        try:
            await self._ensure_auth()
            token = self.credentials.get("access_token")
            resp = await self.client.get(f"{self.base_url}/users/me", headers={"Authorization": f"Bearer {token}"})
            return resp.status_code == 200
        except Exception:
            return False
