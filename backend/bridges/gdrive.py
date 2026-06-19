import os
import json
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from .base import BridgeAdapter
from datetime import datetime, timezone

class GDriveBridge(BridgeAdapter):
    """
    Sovereign Google Drive Bridge using Google REST API.
    Supports drive.file scope for reading/writing agent-specific files.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.version = "v3"
        self.base_url = f"https://www.googleapis.com/drive/{self.version}"
        self.accounts: Dict[str, Dict[str, Any]] = {}

    def build_oauth_url(self, redirect_uri: str, state: str) -> str:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        if not client_id:
            raise ValueError("GOOGLE_CLIENT_ID not found in environment.")
        
        scopes = "openid email profile https://www.googleapis.com/auth/drive.file"
        
        import urllib.parse
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scopes,
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    async def handle_oauth_callback(self, code: str, state: str, redirect_uri: str) -> Dict[str, Any]:
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError("Google OAuth credentials missing from environment.")

        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri
                }
            )
            res.raise_for_status()
            tokens = res.json()
            
            # Fetch user email
            user_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {tokens['access_token']}"}
            )
            user_res.raise_for_status()
            email = user_res.json().get("email")
            
            return {
                "access_token": tokens["access_token"],
                "refresh_token": tokens.get("refresh_token"),
                "email": email,
                "client_id": client_id,
                "client_secret": client_secret
            }

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        token = credentials.get("access_token")
        if not token:
            return False

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token}"}
            )
            if res.status_code == 200:
                email = res.json().get("email")
                if not email: return False
                
                account_state = {
                    "credentials": credentials,
                    "is_connected": True,
                    "refresh_task": None,
                    "last_activity": datetime.now(timezone.utc).isoformat()
                }
                
                self.accounts[email] = account_state
                self.is_connected = True
                self.logger.info(f"GDrive API session established for {email}.")
                
                # Start background refresh loop
                account_state["refresh_task"] = asyncio.create_task(self._token_refresh_loop(
                    get_creds_fn=lambda: self._load_credentials(account_id=email),
                    set_creds_fn=lambda c: self._save_credentials(c, account_id=email),
                    token_url="https://oauth2.googleapis.com/token",
                    client_id=credentials.get("client_id") or os.getenv("GOOGLE_CLIENT_ID") or "",
                    client_secret=credentials.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET") or ""
                ))
                return True
            elif res.status_code == 401 and credentials.get("refresh_token"):
                email = credentials.get("email") or "default"
                account_state = {
                    "credentials": credentials,
                    "is_connected": True,
                    "refresh_task": None,
                    "last_activity": datetime.now(timezone.utc).isoformat()
                }
                self.accounts[email] = account_state
                self.is_connected = True
                account_state["refresh_task"] = asyncio.create_task(self._token_refresh_loop(
                    get_creds_fn=lambda: self._load_credentials(account_id=email),
                    set_creds_fn=lambda c: self._save_credentials(c, account_id=email),
                    token_url="https://oauth2.googleapis.com/token",
                    client_id=credentials.get("client_id") or os.getenv("GOOGLE_CLIENT_ID") or "",
                    client_secret=credentials.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET") or ""
                ))
                return True
                
            self.logger.error(f"GDrive connect failed. Status: {res.status_code}, Response: {res.text}")
            return False

    async def _ensure_auth(self, account_id: str):
        """Standardizes token refresh for Google."""
        account = self.accounts.get(account_id)
        if not account: return
        
        creds = account["credentials"]
        client_id = creds.get("client_id") or os.getenv("GOOGLE_CLIENT_ID")
        client_secret = creds.get("client_secret") or os.getenv("GOOGLE_CLIENT_SECRET")
        
        if not client_id or not creds.get("refresh_token"):
            return
            
        try:
            account["credentials"] = await self._get_valid_token(
                creds, 
                "https://oauth2.googleapis.com/token",
                client_id,
                client_secret  # type: ignore
            )
        except Exception as e:
            self.logger.error(f"Failed to refresh Google token for {account_id}: {e}")

    async def disconnect(self, account_id: Optional[str] = None):
        if account_id and account_id in self.accounts:
            acc = self.accounts.pop(account_id)
            if acc.get("refresh_task"): acc["refresh_task"].cancel()
        elif not account_id:
            for acc in self.accounts.values():
                if acc.get("refresh_task"): acc["refresh_task"].cancel()
            self.accounts.clear()
            self.is_connected = False
            self.logger.info("GDrive Bridge completely disconnected.")

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """GDrive uploads a text snippet to a file in the agent's partitioned folder."""
        account_id = kwargs.get("account_id") or (list(self.accounts.keys())[0] if self.accounts else None)
        if not account_id or account_id not in self.accounts:
            return {"status": "failed", "error": "Not connected or invalid account"}
            
        await self._ensure_auth(account_id)
        token = self.accounts[account_id]["credentials"].get("access_token")
        if not token:
            return {"status": "failed", "error": "No access token"}
            
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
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": f"multipart/related; boundary={boundary}"
                },
                content=body
            )
            if res.status_code == 200:
                self.accounts[account_id]["last_activity"] = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "fileId": res.json().get("id")}
            return {"status": "failed", "error": res.text}

    async def send_message(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        return await self.send(recipient, content, **kwargs)

    async def fetch_unread(self, limit: int = 10, **kwargs) -> List[Dict[str, Any]]:
        account_id = kwargs.get("account_id") or (list(self.accounts.keys())[0] if self.accounts else None)
        if not account_id or account_id not in self.accounts:
            return []
            
        await self._ensure_auth(account_id)
        token = self.accounts[account_id]["credentials"].get("access_token")
        if not token:
            return []
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"{self.base_url}/files",
                headers={"Authorization": f"Bearer {token}"},
                params={"pageSize": limit, "orderBy": "createdTime desc"}
            )
            if res.status_code == 200:
                self.accounts[account_id]["last_activity"] = datetime.now(timezone.utc).isoformat()
                return [{"fileId": f["id"], "name": f["name"], "sender": account_id} for f in res.json().get("files", [])]
        return []

    async def validate_integrity(self) -> bool:
        return len(self.accounts) > 0

    def get_health(self) -> Dict[str, Any]:
        """Health reporting for GDrive."""
        health = super().get_health()
        if self.accounts:
            health.update({
                "accounts": list(self.accounts.keys()),
                "scope": "drive.file"
            })
        return health

    def get_accounts_status(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": email,
                "alias": email,
                "status": "active" if acc.get("is_connected") else "offline",
                "last_active": acc.get("last_activity")
            }
            for email, acc in self.accounts.items()
        ]
