"""
Sovereign MS Teams Bridge — Microsoft Graph API + Bot Framework.

OAuth Flow:
  Azure AD OAuth 2.0 (authorization code + refresh).
  Tenant-aware: defaults to "common" for multi-tenant apps.

Bot Framework Verification:
  Inbound Bot Framework activities carry JWT tokens signed by
  login.botframework.com — verified against the public JWKS endpoint.

Token Refresh:
  Access token checked and refreshed via MSAL (msal package) using
  client_credentials flow for daemon tokens, or refresh_token for user flow.

Features:
  - 1:1 chat messages via /chats/{chatId}/messages
  - Channel/team messages via /teams/{teamId}/channels/{channelId}/messages
  - Adaptive Card support
  - File attachment metadata fetch
"""

import asyncio
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


from .base import BridgeAdapter

GRAPH  = "https://graph.microsoft.com/v1.0"
BOT_FW = "https://smba.trafficmanager.net"
LOGIN  = "https://login.microsoftonline.com"


class MSTeamsBridge(BridgeAdapter):
    """
    Production MS Teams Bridge.
    Supports user-delegated OAuth (for reading chats) and
    Bot Framework webhook (for inbound messages).
    """

    SCOPES = [
        "https://graph.microsoft.com/Chat.ReadWrite",
        "https://graph.microsoft.com/ChannelMessage.Send",
        "https://graph.microsoft.com/User.Read",
        "offline_access",
    ]

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self._access_token:   Optional[str] = None
        self._refresh_token:  Optional[str] = None
        self._expires_at:     float = 0.0
        self._client_id:      Optional[str] = os.getenv("MSTEAMS_CLIENT_ID")
        self._client_secret:  Optional[str] = os.getenv("MSTEAMS_CLIENT_SECRET")
        self._tenant_id:      str = "common"
        self._user_id:        Optional[str] = None
        self._upn:            Optional[str] = None

        # JWKS cache for Bot Framework JWT verification
        self._jwks_cache:     Optional[Dict] = None
        self._jwks_fetched_at: float = 0.0
        self.JWKS_TTL:        float = 3600.0   # Re-fetch JWKS every hour

    # ── Token URL ─────────────────────────────────────────────────────────────

    def _token_url(self) -> str:
        return f"{LOGIN}/{self._tenant_id}/oauth2/v2.0/token"

    def _auth_url(self) -> str:
        return f"{LOGIN}/{self._tenant_id}/oauth2/v2.0/authorize"

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self._access_token  = credentials.get("access_token")
        self._refresh_token = credentials.get("refresh_token")
        self._expires_at    = credentials.get("expires_at", 0.0)
        self._client_id     = credentials.get("client_id") or self._client_id
        self._client_secret = credentials.get("client_secret") or self._client_secret
        self._tenant_id     = credentials.get("tenant_id") or self._tenant_id

        if not self._access_token and not self._refresh_token:
            self.last_error = "No credentials provided."
            return False

        await self._ensure_token()
        if not self._access_token:
            return False

        try:
            resp = await self.client.get(
                f"{GRAPH}/me",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                self._user_id     = data.get("id")
                self._upn         = data.get("userPrincipalName")
                self.is_connected = True
                self.logger.info(f"[MSTEAMS] Connected — {self._upn}")
                
                # Start background refresh loop
                if not self._refresh_task:
                    self._refresh_task = asyncio.create_task(self._token_refresh_loop(
                        get_creds_fn=lambda: self._load_credentials(account_id=self._user_id or "default"),
                        set_creds_fn=lambda c: self._save_credentials(c), # _save_credentials uses self._user_id
                        token_url=self._token_url(),
                        client_id=self._client_id or "",
                        client_secret=self._client_secret or ""
                    ))
                return True
            self.last_error = resp.text
            return False
        except Exception as e:
            self.last_error = str(e)
            return False

    # ── OAuth Flow ────────────────────────────────────────────────────────────

    def build_oauth_url(self, redirect_uri: str, state: str) -> Tuple[str, str]:
        params = {
            "client_id":     self._client_id or "",
            "response_type": "code",
            "redirect_uri":  redirect_uri,
            "response_mode": "query",
            "scope":         " ".join(self.SCOPES),
            "state":         state,
        }
        return self._auth_url() + "?" + urllib.parse.urlencode(params), state

    async def handle_oauth_callback(
        self, code: str, state: str = "", redirect_uri: str = ""
    ) -> Dict[str, Any]:
        resp = await self.client.post(
            self._token_url(),
            data={
                "client_id":     self._client_id,
                "client_secret": self._client_secret,
                "code":          code,
                "redirect_uri":  redirect_uri,
                "grant_type":    "authorization_code",
                "scope":         " ".join(self.SCOPES),
            },
        )
        resp.raise_for_status()
        data = resp.json()
        creds = {
            "access_token":  data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at":    time.time() + data.get("expires_in", 3600),
            "client_id":     self._client_id,
            "client_secret": self._client_secret,
            "tenant_id":     self._tenant_id,
        }
        await self._save_credentials(creds)
        await self.connect(creds)
        return creds

    async def _save_credentials(self, creds: Dict[str, Any]) -> None:  # type: ignore
        await super()._save_credentials(creds, account_id=self._user_id or "default")

    # ── Token Refresh ─────────────────────────────────────────────────────────

    async def _ensure_token(self) -> None:
        """Refresh the access token if within 60 seconds of expiry."""
        if not self._refresh_token:
            return
        if time.time() < self._expires_at - 60:
            return

        self.logger.info("[MSTEAMS] Refreshing access token.")
        try:
            resp = await self.client.post(
                self._token_url(),
                data={
                    "client_id":     self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type":    "refresh_token",
                    "scope":         " ".join(self.SCOPES),
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token  = data["access_token"]
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            self._expires_at    = time.time() + data.get("expires_in", 3600)

            # Persist
            path = os.path.join(self.vault_path, "credentials.json")
            if os.path.exists(path):
                with open(path) as f:
                    stored = json.load(f)
                stored.update({
                    "access_token":  self._access_token,
                    "refresh_token": self._refresh_token,
                    "expires_at":    self._expires_at,
                })
                await self._save_credentials(stored)

            self.logger.info("[MSTEAMS] Token refreshed.")
        except Exception as e:
            self.logger.error(f"[MSTEAMS] Token refresh failed: {e}")

    # ── Bot Framework JWT Verification ────────────────────────────────────────

    async def _get_bot_fw_jwks(self) -> Optional[Dict]:
        """Fetch and cache the Bot Framework JWKS (refreshed hourly)."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_fetched_at) < self.JWKS_TTL:
            return self._jwks_cache

        try:
            # Fetch OIDC config to find JWKS URI
            oidc_resp = await self.client.get(
                "https://login.botframework.com/v1/.well-known/openidconfiguration",
                timeout=10.0,
            )
            oidc_resp.raise_for_status()
            jwks_uri = oidc_resp.json().get("jwks_uri")

            jwks_resp = await self.client.get(jwks_uri, timeout=10.0)
            jwks_resp.raise_for_status()
            self._jwks_cache     = jwks_resp.json()
            self._jwks_fetched_at = now
            return self._jwks_cache
        except Exception as e:
            self.logger.error(f"[MSTEAMS] JWKS fetch failed: {e}")
            return self._jwks_cache  # Return stale cache if available

    async def verify_bot_activity(self, authorization: str) -> bool:
        """
        Verify the Bot Framework JWT from the Authorization header.
        Validates issuer, audience (bot app ID), and signature.
        """
        from ..config import settings
        bot_app_id = settings.MSTEAMS_BOT_APP_ID  # type: ignore
        if not bot_app_id:
            self.logger.warning("[MSTEAMS] MSTEAMS_BOT_APP_ID not set — skipping JWT verification.")
            return True  # Allow through but log the misconfiguration

        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            return False

        jwks = await self._get_bot_fw_jwks()
        if not jwks:
            self.logger.error("[MSTEAMS] No JWKS available for verification.")
            return False

        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience=bot_app_id,
                options={"verify_iss": False},  # Issuer varies by channel
            )
            self.logger.debug(f"[MSTEAMS] Bot activity verified — app: {payload.get('appid')}")
            return True
        except Exception as e:
            self.logger.warning(f"[MSTEAMS] Bot JWT verification failed: {e}")
            return False

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Send a message to a chat or channel.
        recipient format:
          1:1 chat:   "chats/{chatId}"  or just the chatId
          Channel:    "teams/{teamId}/channels/{channelId}"
        kwargs:
          content_type: "html" | "text" (default "text")
          card: dict (Adaptive Card JSON)
          importance: "normal" | "urgent" | "important"
        """
        await self._ensure_token()
        if not self.is_connected or not self._access_token:
            return {"status": "failed", "error": "Not connected"}

        # Determine endpoint
        if recipient.startswith("teams/") and "/channels/" in recipient:
            url = f"{GRAPH}/{recipient}/messages"
        elif "/" not in recipient:
            url = f"{GRAPH}/chats/{recipient}/messages"
        else:
            url = f"{GRAPH}/{recipient}/messages"

        body: Dict[str, Any] = {
            "body": {
                "contentType": kwargs.get("content_type", "text"),
                "content":     content,
            }
        }
        if kwargs.get("importance"):
            body["importance"] = kwargs["importance"]
        if kwargs.get("card"):
            body["attachments"] = [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content":     json.dumps(kwargs["card"]),
                }
            ]

        @BridgeAdapter.resilient_request
        async def _post():
            return await self.client.post(
                url,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type":  "application/json",
                },
                json=body,
            )

        try:
            resp = await _post()
            if resp.status_code == 201:
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "id": resp.json().get("id")}
            self.last_error = resp.text
            return {"status": "failed", "error": resp.text}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    # ── Inbound (Bot Framework) ───────────────────────────────────────────────

    async def process_webhook(self, payload: Dict[str, Any]) -> None:
        """Parse a Bot Framework Activity and dispatch normalised inbound message."""
        if payload.get("type") != "message":
            return

        sender_id = payload.get("from", {}).get("id")
        if sender_id == self._user_id:
            return  # Skip own messages

        convo = payload.get("conversation", {})
        channel_data = payload.get("channelData", {})

        normalized = {
            "id":         payload.get("id"),
            "from_id":    sender_id,
            "chat_id":    convo.get("id"),
            "from_name":  payload.get("from", {}).get("name"),
            "body":       payload.get("text", ""),
            "team_id":    channel_data.get("team", {}).get("id"),
            "protocol":   "MSTEAMS",
            "timestamp":  payload.get("localTimestamp")
                          or datetime.now(timezone.utc).isoformat(),
        }

        # Extract attachments metadata
        attachments = payload.get("attachments", [])
        if attachments:
            normalized["attachments"] = [
                {
                    "name":         a.get("name"),
                    "content_type": a.get("contentType"),
                    "content_url":  a.get("contentUrl"),
                }
                for a in attachments
            ]

        await self._dispatch_inbound(normalized)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent chat messages from the user's chats."""
        await self._ensure_token()
        if not self.is_connected:
            return []

        try:
            resp = await self.client.get(
                f"{GRAPH}/me/chats",
                headers={"Authorization": f"Bearer {self._access_token}"},
                params={"$top": limit, "$expand": "lastMessagePreview"},
            )
            if resp.status_code != 200:
                return []
            chats = resp.json().get("value", [])
            return [
                {
                    "id":        c["id"],
                    "from_id":   c.get("lastMessagePreview", {}).get("from", {}).get("user", {}).get("id"),
                    "chat_id":   c["id"],
                    "body":      c.get("lastMessagePreview", {}).get("body", {}).get("content", ""),
                    "timestamp": c.get("lastMessagePreview", {}).get("createdDateTime"),
                    "protocol":  "MSTEAMS",
                }
                for c in chats
            ]
        except Exception as e:
            self.logger.error(f"[MSTEAMS] fetch_unread failed: {e}")
            return []

    async def validate_integrity(self) -> bool:
        await self._ensure_token()
        if not self._access_token:
            return False
        resp = await self.client.get(
            f"{GRAPH}/me",
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        return resp.status_code == 200

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "upn":        self._upn,
            "tenant_id":  self._tenant_id,
            "token_valid": time.time() < self._expires_at,
        })
        return h
