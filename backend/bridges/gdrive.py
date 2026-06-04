import os
import json
import httpx
from typing import Dict, Any, List, Optional
from .base import BridgeAdapter
from datetime import datetime, timezone

class GDriveBridge(BridgeAdapter):
    """
    Sovereign Google Drive Bridge.
    Supports drive.file scope for reading/writing agent-specific files.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.version = "v3"
        self.base_url = f"https://www.googleapis.com/drive/{self.version}"
        self.email_address: Optional[str] = None

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
                self.logger.info(f"GDrive API session established for {self.email_address}.")
                return True
            elif res.status_code == 401 and credentials.get("refresh_token"):
                self.is_connected = True
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
                client_secret  # type: ignore
            )
        except Exception as e:
            self.logger.error(f"Failed to refresh Google token: {e}")

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """GDrive uploads a text snippet to a file in the agent's partitioned folder."""
        await self._ensure_auth()
        token = self.credentials.get("access_token")
        if not self.is_connected or not token:
            return {"status": "failed", "error": "Not connected"}
            
        metadata = {
            "name": f"Agent Message to {recipient}.txt",
            "mimeType": "text/plain"
        }
        boundary = "gd_bridge_boundary"
        body = (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            "Content-Type: text/plain\r\n\r\n"
            f"{content}\r\n"
            f"--{boundary}--"
        )
        
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}"
                },
                content=body
            )
            if res.status_code == 200:
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "fileId": res.json().get("id")}
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
                f"{self.base_url}/files",
                headers={"Authorization": f"Bearer {token}"},
                params={"pageSize": limit, "orderBy": "createdTime desc"}
            )
            if res.status_code == 200:
                return [{"fileId": f["id"], "name": f["name"], "sender": self.email_address} for f in res.json().get("files", [])]
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        """Health reporting for GDrive."""
        health = super().get_health()
        if self.is_connected:
            health.update({
                "email": self.email_address,
                "scope": "drive.file"
            })
        return health
