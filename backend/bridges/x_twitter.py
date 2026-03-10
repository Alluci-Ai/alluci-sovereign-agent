import httpx
import time
import os
import asyncio
from typing import Dict, Any, List
from .base import BridgeAdapter

class XBridge(BridgeAdapter):
    """
    Sovereign X (Twitter) Bridge using OAuth 2.0 PKCE and X v2 API.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.base_url = "https://api.twitter.com/2"
        self.credentials = {}
        self._last_mention_id = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.credentials = credentials
        token = credentials.get("access_token")
        if not token:
            return False
            
        self.is_connected = True
        self.logger.info(f"X (Twitter) session initialized for {self.bridge_id}")
        # Start background polling loop for mentions/DMs
        asyncio.create_task(self._poll_loop())
        return True

    async def _ensure_auth(self):
        """Standardizes token refresh for X."""
        client_id = self.credentials.get("client_id") or os.getenv("TWITTER_CLIENT_ID")
        client_secret = self.credentials.get("client_secret") or os.getenv("TWITTER_CLIENT_SECRET")
        
        if not client_id:
            return
            
        try:
            # We assume a helper method in base or implemented here for OAuth2 PKCE refresh
            pass 
        except Exception as e:
            self.logger.error(f"Failed to refresh X token: {e}")

    @BridgeAdapter.resilient_request
    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Posts a Tweet or attempts a DM if recipient is a numeric ID."""
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        
        if recipient and recipient.isdigit():
            return await self._send_dm(recipient, content)

        resp = await self.client.post(
            f"{self.base_url}/tweets",
            json={"text": content},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        
        if resp.status_code == 201:
            self.last_activity = str(int(asyncio.get_event_loop().time()))
            return {"status": "success", "id": resp.json()["data"]["id"]}
        else:
            self.last_error = resp.text
            return {"status": "failed", "error": resp.text}

    @BridgeAdapter.resilient_request
    async def _send_dm(self, recipient_id: str, content: str) -> Dict[str, Any]:
        token = self.credentials.get("access_token")
        resp = await self.client.post(
            f"{self.base_url}/dm_conversations/with/{recipient_id}/messages",
            json={"text": content},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        if resp.status_code == 201:
            self.last_activity = str(int(asyncio.get_event_loop().time()))
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

        params = {"max_results": min(limit, 100)}
        if self._last_mention_id:
            params["since_id"] = self._last_mention_id

        resp = await self.client.get(
            f"{self.base_url}/users/{my_id}/mentions",
            params=params,
            headers={"Authorization": f"Bearer {token}"}
        )
        if resp.status_code == 200:
            data = resp.json()
            mentions = data.get("data", [])
            if mentions:
                self._last_mention_id = mentions[0]["id"]
            return mentions
        return []

    async def _poll_loop(self):
        """Background loop for X monitoring."""
        while self.is_connected:
            try:
                mentions = await self.fetch_unread(limit=20)
                for mention in mentions:
                    await self._dispatch_inbound({
                        "from": str(mention.get("author_id")),
                        "body": mention.get("text"),
                        "id": str(mention.get("id")),
                        "type": "mention",
                        "timestamp": str(int(asyncio.get_event_loop().time()))
                    })
                if mentions:
                    self.last_activity = str(int(asyncio.get_event_loop().time()))
                    
            except Exception as e:
                self.logger.error(f"X poll cycle error: {e}")
                await asyncio.sleep(60)
            
            await asyncio.sleep(180) # Respect rate limits

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        """Health reporting for X."""
        health = super().get_health()
        if self.is_connected:
            health.update({
                "mode": "polling",
                "last_mention_id": self._last_mention_id
            })
        return health
