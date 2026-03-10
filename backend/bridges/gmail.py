import os
import json
import base64
import httpx
import asyncio
from email.message import EmailMessage
from typing import Dict, Any, List, Optional
from .base import BridgeAdapter
from datetime import datetime, timezone

class GmailBridge(BridgeAdapter):
    """
    Sovereign Gmail Bridge using Google REST API.
    Supports offline access tokens and MIME parsing.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.email_address: Optional[str] = None
        self._poll_task: Optional[asyncio.Task] = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.credentials = credentials
        token = credentials.get("access_token")
        if not token:
            return False
            
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            if res.status_code == 200:
                self.email_address = res.json().get("email")
                self.is_connected = True
                self.logger.info(f"Gmail API session established for {self.email_address}.")
                # Start background polling
                if not self._poll_task:
                    self._poll_task = asyncio.create_task(self._poll_loop())
                return True
            elif res.status_code == 401 and credentials.get("refresh_token"):
                self.is_connected = True 
                if not self._poll_task:
                    self._poll_task = asyncio.create_task(self._poll_loop())
                return True
                
        return False

    async def _ensure_auth(self):
        """Standardizes token refresh for Google."""
        client_id = self.credentials.get("client_id") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = self.credentials.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not client_id or not self.credentials.get("refresh_token"):
            return
            
        try:
            self.credentials = await self._get_valid_token(
                self.credentials, 
                "https://oauth2.googleapis.com/token",
                client_id,
                client_secret
            )
        except Exception as e:
            self.logger.error(f"Failed to refresh Google token: {e}")

    async def send(self, recipient: str, content: str, subject: str = "Message from Sovereign Agent", **kwargs) -> Dict[str, Any]:
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        if not self.is_connected or not token:
            return {"status": "failed", "error": "Not connected"}
            
        msg = EmailMessage()
        msg.set_content(content)
        msg['To'] = recipient
        msg['From'] = self.email_address or "me"
        msg['Subject'] = subject

        raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')

        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {token}"},
                json={"raw": raw_msg}
            )
            if res.status_code == 200:
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "id": res.json().get("id")}
            return {"status": "failed", "error": res.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        if not self.is_connected or not token:
            return []
            
        messages = []
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {token}"},
                params={"q": "is:unread", "maxResults": limit}
            )
            if res.status_code != 200:
                return []
                
            msg_list = res.json().get("messages", [])
            for m in msg_list:
                m_res = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {token}"},
                    params={"format": "full"}
                )
                if m_res.status_code == 200:
                    data = m_res.json()
                    snippet = data.get("snippet", "")
                    headers = data.get("payload", {}).get("headers", [])
                    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                    timestamp_ms = int(data.get("internalDate", 0))
                    
                    parsed = {
                        "id": m["id"],
                        "from": sender,
                        "body": snippet,
                        "timestamp": datetime.fromtimestamp(timestamp_ms/1000, timezone.utc).isoformat(),
                        "protocol": "GMAIL",
                        "account_id": self.email_address
                    }
                    messages.append(parsed)
                    
                    # Mark read
                    await client.post(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}/modify",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"removeLabelIds": ["UNREAD"]}
                    )
        return messages

    async def _poll_loop(self):
        """Autonomous polling loop for new emails."""
        while self.is_connected:
            try:
                unread = await self.fetch_unread(limit=5)
                for msg in unread:
                    await self._dispatch_inbound(msg)
                
                if unread:
                    self.last_activity = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                self.logger.error(f"Gmail poll error: {e}")
            
            await asyncio.sleep(60) # Poll every minute

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        """Health reporting for Gmail."""
        health = super().get_health()
        if self.is_connected:
            health.update({
                "email": self.email_address,
                "polling": True
            })
        return health

    async def disconnect(self):
        if self._poll_task:
            self._poll_task.cancel()
        await super().disconnect()
