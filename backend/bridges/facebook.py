"""
Sovereign Facebook Messenger Bridge — Meta Graph API.

Shares the same OAuth pipeline as Instagram (Facebook Page token).
Adds App Secret Proof on all API calls (required for system user tokens).
"""

import hashlib
import hmac
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .base import BridgeAdapter

GRAPH = "https://graph.facebook.com/v20.0"


class FacebookBridge(BridgeAdapter):
    """
    Production Facebook Messenger Bridge.
    Uses Page Access Token with App Secret Proof on all outbound calls.
    """

    OAUTH_AUTHORIZE_URL = "https://www.facebook.com/v20.0/dialog/oauth"
    OAUTH_TOKEN_URL     = f"{GRAPH}/oauth/access_token"

    SCOPES = [
        "pages_messaging",
        "pages_show_list",
        "pages_read_engagement",
        "pages_manage_metadata",
    ]

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.page_id: Optional[str] = None
        self.page_access_token: Optional[str] = None
        self.page_name: Optional[str] = None
        self._client_id: Optional[str] = os.getenv("FACEBOOK_CLIENT_ID")
        self._client_secret: Optional[str] = os.getenv("FACEBOOK_CLIENT_SECRET")
        self._token_expires_at: float = 0.0

    # ── App Secret Proof ──────────────────────────────────────────────────────

    def _app_secret_proof(self, token: str) -> str:
        """
        Compute appsecret_proof = HMAC-SHA256(app_secret, access_token).
        Required for system user tokens and recommended for all calls.
        Ref: https://developers.facebook.com/docs/graph-api/security/
        """
        secret = self._client_secret or ""
        return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.page_access_token = credentials.get("page_access_token")
        self.page_id           = credentials.get("page_id")
        self.page_name         = credentials.get("page_name")
        self._client_id        = credentials.get("client_id") or self._client_id
        self._client_secret    = credentials.get("client_secret") or self._client_secret
        self._token_expires_at = credentials.get("expires_at", 0.0)

        if not self.page_access_token or not self.page_id:
            self.last_error = "page_access_token and page_id required."
            return False

        try:
            proof = self._app_secret_proof(self.page_access_token)
            resp  = await self.client.get(
                f"{GRAPH}/{self.page_id}",
                params={
                    "fields":           "id,name",
                    "access_token":     self.page_access_token,
                    "appsecret_proof":  proof,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                self.page_name    = data.get("name")
                self.is_connected = True
                self.logger.info(f"[FACEBOOK] Connected — Page: {self.page_name}")
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
            "redirect_uri":  redirect_uri,
            "response_type": "code",
            "scope":         ",".join(self.SCOPES),
            "state":         state,
        }
        return self.OAUTH_AUTHORIZE_URL + "?" + urllib.parse.urlencode(params), state

    async def handle_oauth_callback(
        self, code: str, state: str = "", redirect_uri: str = ""
    ) -> Dict[str, Any]:
        """Exchange code → short-lived token → long-lived token → page tokens."""
        # Step 1: Short-lived token
        r1 = await self.client.get(
            self.OAUTH_TOKEN_URL,
            params={
                "client_id":     self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri":  redirect_uri,
                "code":          code,
            },
        )
        r1.raise_for_status()
        short_token = r1.json().get("access_token")

        # Step 2: Long-lived token
        r2 = await self.client.get(
            self.OAUTH_TOKEN_URL,
            params={
                "grant_type":        "fb_exchange_token",
                "client_id":         self._client_id,
                "client_secret":     self._client_secret,
                "fb_exchange_token": short_token,
            },
        )
        r2.raise_for_status()
        long_data  = r2.json()
        long_token = long_data["access_token"]

        # Step 3: Page tokens
        r3 = await self.client.get(
            f"{GRAPH}/me/accounts",
            params={
                "access_token":    long_token,
                "appsecret_proof": self._app_secret_proof(long_token),
            },
        )
        r3.raise_for_status()
        pages = r3.json().get("data", [])
        if not pages:
            raise ValueError("No Pages found on this Facebook account.")

        page = pages[0]
        creds = {
            "page_id":           page["id"],
            "page_name":         page.get("name"),
            "page_access_token": page["access_token"],
            "user_access_token": long_token,
            "expires_at":        time.time() + long_data.get("expires_in", 5_184_000),
            "client_id":         self._client_id,
            "client_secret":     self._client_secret,
        }
        await self._save_credentials(creds)
        await self.connect(creds)
        return creds

    async def _save_credentials(self, creds: Dict[str, Any]) -> None:
        await super()._save_credentials(creds, account_id=self.page_id or "default")

    # ── Webhook Security ──────────────────────────────────────────────────────

    def verify_signature(self, body: bytes, sig_header: str) -> bool:
        """Verify X-Hub-Signature-256 using META_APP_SECRET."""
        from ..config import settings
        secret = settings.META_APP_SECRET or self._client_secret
        if not secret:
            self.logger.error("[FACEBOOK] META_APP_SECRET not set.")
            return False
        if not sig_header or not sig_header.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, sig_header)

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Respond to Meta hub.challenge."""
        from ..config import settings
        expected = settings.META_VERIFY_TOKEN
        if not expected:
            return None
        if mode == "subscribe" and hmac.compare_digest(token or "", expected):
            return challenge
        return None

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Send a Messenger message to a PSID.
        kwargs:
            msg_type: "text" | "image" | "template"
            image_url: str
            template_type: "button" | "generic"
        """
        if not self.is_connected or not self.page_access_token:
            return {"status": "failed", "error": "Not connected"}

        proof = self._app_secret_proof(self.page_access_token)
        msg_type = kwargs.get("msg_type", "text")

        if msg_type == "image" and kwargs.get("image_url"):
            message = {
                "attachment": {
                    "type":    "image",
                    "payload": {"url": kwargs["image_url"], "is_reusable": True},
                }
            }
        else:
            message = {"text": content}

        @BridgeAdapter.resilient_request
        async def _post():
            return await self.client.post(
                f"{GRAPH}/{self.page_id}/messages",
                params={
                    "access_token":    self.page_access_token,
                    "appsecret_proof": proof,
                },
                json={
                    "recipient":      {"id": recipient},
                    "message":        message,
                    "messaging_type": "RESPONSE",
                },
            )

        try:
            resp = await _post()
            data = resp.json()
            if resp.status_code == 200:
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "message_id": data.get("message_id")}
            self.last_error = data.get("error", {}).get("message", resp.text)
            return {"status": "failed", "error": self.last_error}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    # ── Inbound ───────────────────────────────────────────────────────────────

    async def process_webhook(self, data: Dict[str, Any]) -> None:
        """Parse and dispatch Facebook Messenger webhook events (all types)."""
        try:
            for entry in data.get("entry", []):
                for event in entry.get("messaging", []):
                    sender_id = event.get("sender", {}).get("id")
                    if not sender_id or sender_id == self.page_id:
                        continue  # Skip own messages

                    msg = event.get("message", {})
                    if not msg:
                        continue

                    body, media = self._extract_content(msg)
                    await self._dispatch_inbound({
                        "id":         msg.get("mid"),
                        "from_id":    sender_id,
                        "chat_id":    sender_id,
                        "body":       body,
                        "media":      media,
                        "type":       "message",
                        "timestamp":  datetime.fromtimestamp(int(event.get("timestamp", 0)) / 1000, tz=timezone.utc).isoformat() if event.get("timestamp") else datetime.now(timezone.utc).isoformat(),
                        "account_id": entry.get("id"),
                        "protocol":   "FACEBOOK",
                    })
        except Exception as e:
            self.logger.error(f"[FACEBOOK] Webhook parse error: {e}", exc_info=True)

    def _extract_content(
        self, msg: Dict[str, Any]
    ) -> Tuple[str, Optional[Dict]]:
        """Extract body and media from a Messenger message object."""
        if msg.get("text"):
            return msg["text"], None

        attachments = msg.get("attachments", [])
        if attachments:
            att      = attachments[0]
            att_type = att.get("type", "unknown")
            payload  = att.get("payload", {})
            media = {
                "type":  att_type,
                "url":   payload.get("url"),
                "title": payload.get("title"),
                "sticker_id": payload.get("sticker_id"),
            }
            return f"[Facebook {att_type}]", media

        return "[Facebook message]", None

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def validate_integrity(self) -> bool:
        if not self.page_access_token:
            return False
        proof = self._app_secret_proof(self.page_access_token)
        resp = await self.client.get(
            f"{GRAPH}/{self.page_id}",
            params={"access_token": self.page_access_token, "appsecret_proof": proof},
        )
        return resp.status_code == 200

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({"page_id": self.page_id, "page_name": self.page_name})
        return h
