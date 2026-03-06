import os
import json
import base64
from email.message import EmailMessage
from typing import Dict, Any, List
from urllib.parse import urlencode
from .base import BridgeAdapter
from ..oauth_config import OAUTH_CONFIGS

class GmailBridge(BridgeAdapter):
    """
    Sovereign Gmail Bridge using Google REST API.
    Supports offline access tokens and MIME parsing.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.access_token = None
        self.refresh_token = None
        self.email_address = None

    async def handle_oauth_callback(self, code: str, state: str = None) -> bool:
        """Exchanges authorization code for tokens and saves to vault."""
        import httpx
        config = OAUTH_CONFIGS.get(self.bridge_id)
        if not config:
            return False

        redirect_uri = f"{os.getenv('DAEMON_PUBLIC_URL', 'http://localhost:8000').rstrip('/')}/api/oauth/{self.bridge_id}/callback"
        
        async with httpx.AsyncClient() as client:
            res = await client.post(config["token_url"], data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri
            })
            
            if res.status_code != 200:
                self.logger.error(f"OAuth Exchange Failed: {res.text}")
                return False
                
            data = res.json()
            creds = {
                "access_token": data.get("access_token"),
                "refresh_token": data.get("refresh_token"),
            }
            # Optional: save to vault and connect
            try:
                # Assuming base adapter implements vault saving
                with open(os.path.join(self.vault_root, f"{self.bridge_id}_config.json"), "w") as f:
                    json.dump(creds, f)
            except Exception:
                pass

            return await self.connect(creds)

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.access_token = credentials.get("access_token")
        self.refresh_token = credentials.get("refresh_token")
        if not self.access_token:
            return False
            
        import httpx
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {self.access_token}"}
            )
            if res.status_code == 200:
                self.email_address = res.json().get("email")
                self.is_connected = True
                self.logger.info(f"Gmail API session established for {self.email_address}.")
                return True
            elif res.status_code == 401 and self.refresh_token:
                # Attempt refresh, handled in _get_valid_token if implemented
                pass
                
        return False

    async def send(self, recipient: str, content: str, subject: str = "Message from Sovereign Agent", **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not self.access_token:
            return {"status": "failed", "error": "Not connected"}
            
        msg = EmailMessage()
        msg.set_content(content)
        msg['To'] = recipient
        msg['From'] = self.email_address
        msg['Subject'] = subject

        raw_msg = base64.urlsafe_bencode(msg.as_bytes()).decode('utf-8')

        import httpx
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {self.access_token}"},
                json={"raw": raw_msg}
            )
            if res.status_code == 200:
                return {"status": "success", "id": res.json().get("id")}
            return {"status": "failed", "error": res.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
            
        import httpx
        messages = []
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {self.access_token}"},
                params={"q": "is:unread", "maxResults": limit}
            )
            if res.status_code != 200:
                return []
                
            msg_list = res.json().get("messages", [])
            for m in msg_list:
                m_res = await client.get(
                    f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    params={"format": "full"}
                )
                if m_res.status_code == 200:
                    data = m_res.json()
                    snippet = data.get("snippet", "")
                    headers = data.get("payload", {}).get("headers", [])
                    sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
                    messages.append({
                        "id": m["id"],
                        "sender": sender,
                        "snippet": snippet
                    })
                    # Mark read
                    await client.post(
                        f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}/modify",
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        json={"removeLabelIds": ["UNREAD"]}
                    )
        return messages

    async def validate_integrity(self) -> bool:
        return self.is_connected
