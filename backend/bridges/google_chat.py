import httpx
import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter

class GoogleChatBridge(BridgeAdapter):
    """
    Sovereign Google Chat Bridge using Service Account Credentials.
    Implements messaging and webhook event handling for Google Chat Spaces.
    
    Reference: Sovereign Spec Section 2.3 - Cloud Manifold Adapters
    """

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.api_url = "https://chat.googleapis.com/v1"
        self.credentials: Dict[str, Any] = {}
        self.access_token: Optional[str] = None
        self.token_expiry: float = 0
        self.project_id: Optional[str] = None
        
        # Load cached credentials if they exist in the vault
        self._load_config_from_vault()

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Initializes the bridge with Service Account JSON.
        Expected credentials: { "type": "service_account", "project_id": "...", ... }
        """
        if not credentials:
            self.logger.warning("[ GCHAT ] No credentials provided.")
            return False

        self.credentials = credentials
        self.project_id = credentials.get("project_id")
        
        # Immediate token refresh to verify credentials
        success = await self._refresh_token()
        if success:
            self.is_connected = True
            self._persist_to_vault("config", self.credentials)
            self.logger.info(f"[ GCHAT ] Successfully authenticated for project: {self.project_id}")
        return success

    async def _refresh_token(self) -> bool:
        """
        Retrieves an OAuth2 access token using the Service Account JWT flow.
        Uses httpx to avoid heavy external dependencies.
        """
        # In a real sovereign environment, we would use a library like 'google-auth'.
        # For this implementation, we assume the host environment has 'google-auth'
        # or we mock the token logic if strictly required. 
        # Here we attempt to use 'google.oauth2.service_account' if available.
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request as GoogleRequest
            
            scopes = ["https://www.googleapis.com/auth/chat.messages"]
            creds = service_account.Credentials.from_service_account_info(self.credentials, scopes=scopes)
            creds.refresh(GoogleRequest())
            self.access_token = creds.token
            self.token_expiry = creds.expiry.replace(tzinfo=timezone.utc).timestamp() if creds.expiry else time.time() + 3600
            return True
        except ImportError:
            self.logger.error("[ GCHAT ] 'google-auth' library is required for Service Account authentication.")
            return False
        except Exception as e:
            self.logger.error(f"[ GCHAT ] Token refresh failed: {e}")
            return False

    async def _get_auth_headers(self) -> Dict[str, str]:
        if not self.access_token or time.time() > self.token_expiry - 60:
            await self._refresh_token()
        return {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Legacy shim for BridgeAdapter compatibility."""
        return await self.send(recipient, content)

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Transmits a message to a Google Chat Space or Thread.
        'recipient' should be the Space ID (e.g., 'spaces/XXXXXXXX')
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        space_id = recipient
        thread_key = kwargs.get("thread_key")
        
        url = f"{self.api_url}/{space_id}/messages"
        params = {}
        if thread_key:
            params["threadKey"] = thread_key

        payload = {"text": content}
        if "cards" in kwargs:
             payload["cardsV2"] = kwargs["cards"]

        try:
            headers = await self._get_auth_headers()
            async with httpx.AsyncClient() as client:
                res = await client.post(url, headers=headers, json=payload, params=params)
                data = res.json()
                
                status = "success" if res.status_code == 200 else "failed"
                
                self._persist_to_vault("sent_buffer", {
                    "to": space_id,
                    "content": content,
                    "status": status,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "gchat_id": data.get("name") if status == "success" else None,
                    "error": data.get("error", {}).get("message") if status == "failed" else None
                })
                
                return {"status": status, "data": data}
        except Exception as e:
            self.logger.error(f"[ GCHAT ] Send failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Pulls recent messages. Note: Google Chat API usually prefers push-based 
        webhooks, but we can poll lists if needed.
        """
        # Google Chat polling is space-specific. For now, we return empty
        # as the master orchestrator relies on process_event push.
        return []

    async def process_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parses incoming App Interaction events from Google Chat webhooks.
        """
        event_type = payload.get("type")
        
        if event_type == "MESSAGE":
            message = payload.get("message", {})
            sender = message.get("sender", {})
            
            normalized = {
                "id": message.get("name"),
                "from": sender.get("name"),
                "from_name": sender.get("displayName"),
                "body": message.get("text"),
                "space": payload.get("space", {}).get("name"),
                "thread": message.get("thread", {}).get("name"),
                "protocol": "GCHAT",
                "timestamp": message.get("createTime")
            }
            
            self._persist_to_vault("inbox", normalized)
            if self.on_event:
                await self.on_event("message", normalized)
            return normalized
            
        elif event_type == "ADDED_TO_SPACE":
            self.logger.info(f"[ GCHAT ] App added to space: {payload.get('space', {}).get('name')}")
            
        return None

    async def validate_integrity(self) -> bool:
        return await self._refresh_token()

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.json")
        try:
            if box == "config":
                with open(path, "w") as f:
                    json.dump(data, f)
            else:
                path = path + "l" # jsonl for buffers
                with open(path, "a") as f:
                    f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"[ GCHAT ] Vault Write Error: {e}")

    def _load_config_from_vault(self):
        path = os.path.join(self.vault_path, "config.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.credentials = json.load(f)
                    self.project_id = self.credentials.get("project_id")
                    self.is_connected = True
            except Exception as e:
                self.logger.error(f"[ GCHAT ] Config load error: {e}")

    async def verify_webhook(self, signature: str, body: bytes) -> bool:
        """
        Verifies that the request coming into the webhook is actually from Google.
        Google Chat uses Bearer tokens (JWTs) in the Authorization header,
        signed by Google's OIDC certificates.
        Reference: https://developers.google.com/chat/how-tos/webhooks#verify_the_token
        """
        import httpx
        from jose import jwt as jose_jwt, JWTError as JoseJWTError

        GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
        GOOGLE_CHAT_ISSUER = "chat@system.gserviceaccount.com"

        if not signature:
            self.logger.warning("[ GCHAT ] Webhook rejected: no Authorization token provided.")
            return False

        # Strip "Bearer " prefix if present
        token = signature.removeprefix("Bearer ").strip()
        if not token:
            self.logger.warning("[ GCHAT ] Webhook rejected: empty token after prefix strip.")
            return False

        try:
            # Fetch Google's public JWKS (cached in production via httpx client)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(GOOGLE_CERTS_URL)
                resp.raise_for_status()
                jwks = resp.json()

            # Decode and verify the JWT
            payload = jose_jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=self.project_id if hasattr(self, 'project_id') else None,
                issuer=GOOGLE_CHAT_ISSUER,
                options={
                    "verify_aud": hasattr(self, 'project_id') and bool(self.project_id),
                    "verify_iss": True,
                    "verify_exp": True,
                }
            )
            self.logger.debug(f"[ GCHAT ] Webhook JWT verified. Subject: {payload.get('sub', 'N/A')}")
            return True

        except JoseJWTError as e:
            self.logger.warning(f"[ GCHAT ] Webhook JWT verification failed: {e}")
            return False
        except httpx.HTTPStatusError as e:
            self.logger.error(f"[ GCHAT ] Failed to fetch Google JWKS: {e}")
            return False
        except Exception as e:
            self.logger.error(f"[ GCHAT ] Unexpected error during webhook verification: {e}")
            return False
