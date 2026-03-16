"""
Sovereign Instagram Bridge — Meta Graph API (Instagram Messaging).

OAuth Flow:
  1. build_oauth_url()         → redirect user to Instagram
  2. handle_oauth_callback()   → exchange code → short-lived token → long-lived token → page token
  3. connect()                 → validate stored credentials

Inbound:
  - Webhook POSTs verified via X-Hub-Signature-256 (META_APP_SECRET)
  - Text, image, sticker, story_mention, share all normalised

Outbound:
  - Text messages via /{page_id}/messages
  - Image replies via attachment_upload flow
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .base import BridgeAdapter

GRAPH = "https://graph.facebook.com/v20.0"


class InstagramBridge(BridgeAdapter):
    """
    Production Instagram Bridge using Meta Graph API.
    Requires a Facebook Page connected to an Instagram Business/Creator account.
    """

    OAUTH_AUTHORIZE_URL = "https://www.facebook.com/v20.0/dialog/oauth"
    OAUTH_TOKEN_URL     = f"{GRAPH}/oauth/access_token"
    LONG_LIVED_URL      = f"{GRAPH}/oauth/access_token"

    SCOPES = [
        "instagram_basic",
        "instagram_manage_messages",
        "pages_messaging",
        "pages_show_list",
        "pages_manage_metadata",
    ]

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.page_id: Optional[str] = None
        self.page_access_token: Optional[str] = None
        self.instagram_account_id: Optional[str] = None
        self._user_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._client_id: Optional[str] = os.getenv("INSTAGRAM_CLIENT_ID")
        self._client_secret: Optional[str] = os.getenv("INSTAGRAM_CLIENT_SECRET")

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect using stored credentials.
        credentials must contain page_access_token and page_id.
        """
        self.page_access_token = credentials.get("page_access_token")
        self.page_id           = credentials.get("page_id")
        self.instagram_account_id = credentials.get("instagram_account_id")
        self._user_token       = credentials.get("user_access_token")
        self._token_expires_at = credentials.get("expires_at", 0.0)
        self._client_id        = credentials.get("client_id") or self._client_id
        self._client_secret    = credentials.get("client_secret") or self._client_secret

        if not self.page_access_token or not self.page_id:
            self.last_error = "page_access_token and page_id required."
            return False

        # Validate by fetching Page info
        try:
            resp = await self.client.get(
                f"{GRAPH}/{self.page_id}",
                params={
                    "fields":       "id,name,instagram_business_account",
                    "access_token": self.page_access_token,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if not self.instagram_account_id:
                    igba = data.get("instagram_business_account", {})
                    self.instagram_account_id = igba.get("id")
                self.is_connected = True
                self.logger.info(
                    f"[INSTAGRAM] Connected — Page: {data.get('name')} "
                    f"(IG account: {self.instagram_account_id})"
                )
                return True
            self.last_error = resp.text
            self.logger.error(f"[INSTAGRAM] Connect validation failed: {resp.text}")
            return False
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"[INSTAGRAM] Connect error: {e}")
            return False

    # ── OAuth PKCE Flow ───────────────────────────────────────────────────────

    def build_oauth_url(self, redirect_uri: str, state: str) -> Tuple[str, str]:
        """
        Build Facebook/Instagram OAuth URL.
        Returns (authorize_url, state).
        Instagram uses standard code flow — no PKCE required by Meta,
        but state parameter provides CSRF protection.
        """
        params = {
            "client_id":     self._client_id or "",
            "redirect_uri":  redirect_uri,
            "response_type": "code",
            "scope":         ",".join(self.SCOPES),
            "state":         state,
        }
        url = self.OAUTH_AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)
        return url, state

    async def handle_oauth_callback(
        self, code: str, state: str = "", redirect_uri: str = ""
    ) -> Dict[str, Any]:
        """
        Full token exchange pipeline:
        1. code → short-lived user token
        2. short-lived → long-lived user token (60 days)
        3. long-lived user token → page access token
        4. Store credentials and call connect()
        """
        if not code:
            raise ValueError("Missing authorization code.")

        # Step 1: Exchange code for short-lived user token
        resp = await self.client.get(
            self.OAUTH_TOKEN_URL,
            params={
                "client_id":     self._client_id,
                "client_secret": self._client_secret,
                "redirect_uri":  redirect_uri,
                "code":          code,
            },
        )
        resp.raise_for_status()
        short_data = resp.json()
        short_token = short_data.get("access_token")
        if not short_token:
            raise ValueError(f"Token exchange failed: {short_data}")

        # Step 2: Exchange short-lived → long-lived (60 days)
        long_resp = await self.client.get(
            self.LONG_LIVED_URL,
            params={
                "grant_type":        "fb_exchange_token",
                "client_id":         self._client_id,
                "client_secret":     self._client_secret,
                "fb_exchange_token": short_token,
            },
        )
        long_resp.raise_for_status()
        long_data   = long_resp.json()
        long_token  = long_data.get("access_token")
        expires_in  = long_data.get("expires_in", 5_184_000)  # 60 days default

        # Step 3: Get Pages and their access tokens
        pages_resp = await self.client.get(
            f"{GRAPH}/me/accounts",
            params={"access_token": long_token},
        )
        pages_resp.raise_for_status()
        pages = pages_resp.json().get("data", [])

        if not pages:
            raise ValueError(
                "No Facebook Pages found. Ensure the account manages at least one Page."
            )

        # Use first page (or match by page_id if pre-configured)
        page = pages[0]
        creds = {
            "user_access_token": long_token,
            "expires_at":        time.time() + expires_in,
            "page_id":           page["id"],
            "page_name":         page.get("name"),
            "page_access_token": page["access_token"],  # never-expiring page token
            "client_id":         self._client_id,
            "client_secret":     self._client_secret,
        }
        await self._save_credentials(creds)
        self.logger.info(f"[INSTAGRAM] OAuth complete — Page: {page.get('name')}")
        await self.connect(creds)
        return creds

    async def _save_credentials(self, creds: Dict[str, Any]) -> None:
        await super()._save_credentials(creds, account_id=self.page_id or "default")

    # ── Webhook Security ──────────────────────────────────────────────────────

    def verify_signature(self, body: bytes, signature_header: str) -> bool:
        """Verify X-Hub-Signature-256 using META_APP_SECRET."""
        from ..config import settings
        secret = settings.META_APP_SECRET or self._client_secret
        if not secret:
            self.logger.error("[INSTAGRAM] META_APP_SECRET not set — rejecting webhook.")
            return False
        if not signature_header or not signature_header.startswith("sha256="):
            return False
        expected = "sha256=" + hmac.new(
            secret.encode(), body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header)

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Respond to Meta hub.challenge verification."""
        from ..config import settings
        expected = settings.META_VERIFY_TOKEN
        if not expected:
            self.logger.error("[INSTAGRAM] META_VERIFY_TOKEN not set.")
            return None
        if mode == "subscribe" and hmac.compare_digest(token or "", expected):
            return challenge
        return None

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Send a message to an Instagram user (PSID).
        kwargs:
            msg_type: "text" | "image" | "generic_template"
            image_url: str  (for msg_type="image")
            attachment_id: str (pre-uploaded attachment)
        """
        if not self.is_connected or not self.page_access_token:
            return {"status": "failed", "error": "Not connected"}

        msg_type = kwargs.get("msg_type", "text")

        if msg_type == "image" and kwargs.get("image_url"):
            message = {
                "attachment": {
                    "type": "image",
                    "payload": {
                        "url":         kwargs["image_url"],
                        "is_reusable": True,
                    },
                }
            }
        elif msg_type == "image" and kwargs.get("attachment_id"):
            message = {
                "attachment": {
                    "type":    "image",
                    "payload": {"attachment_id": kwargs["attachment_id"]},
                }
            }
        else:
            message = {"text": content}

        @BridgeAdapter.resilient_request
        async def _post():
            return await self.client.post(
                f"{GRAPH}/{self.page_id}/messages",
                params={"access_token": self.page_access_token},
                json={
                    "recipient": {"id": recipient},
                    "message":   message,
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
        """Parse and dispatch Instagram Messenger webhook events."""
        try:
            for entry in data.get("entry", []):
                for event in entry.get("messaging", []):
                    sender_id = event.get("sender", {}).get("id")
                    msg       = event.get("message", {})
                    if not msg or not sender_id:
                        continue

                    # Determine body and media info
                    body, media = self._extract_message_content(msg)
                    msg_type = "story_mention" if "story" in msg or msg.get("reply_to", {}).get("story") else "message"

                    await self._dispatch_inbound({
                        "id":         msg.get("mid"),
                        "from_id":    sender_id,
                        "chat_id":    sender_id,
                        "body":       body,
                        "media":      media,
                        "type":       msg_type,
                        "timestamp":  datetime.fromtimestamp(int(event.get("timestamp", 0)) / 1000, tz=timezone.utc).isoformat() if event.get("timestamp") else datetime.now(timezone.utc).isoformat(),
                        "account_id": self.page_id,
                        "protocol":   "INSTAGRAM",
                    })
        except Exception as e:
            self.logger.error(f"[INSTAGRAM] Webhook parse error: {e}", exc_info=True)

    def _extract_message_content(
        self, msg: Dict[str, Any]
    ) -> Tuple[str, Optional[Dict]]:
        """Return (body_text, media_info) from a Messenger message object."""
        if msg.get("text"):
            return msg["text"], None

        attachments = msg.get("attachments", [])
        if attachments:
            att = attachments[0]
            att_type = att.get("type", "unknown")
            payload  = att.get("payload", {})
            media = {
                "type":  att_type,
                "url":   payload.get("url"),
                "title": payload.get("title"),
            }
            return f"[Instagram {att_type}]", media

        if msg.get("sticker_id"):
            return "[Instagram sticker]", {"type": "sticker", "id": msg["sticker_id"]}

        return "[Instagram message]", None

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []  # Push-only via webhooks

    async def validate_integrity(self) -> bool:
        if not self.page_access_token:
            return False
        resp = await self.client.get(
            f"{GRAPH}/{self.page_id}",
            params={"access_token": self.page_access_token},
        )
        return resp.status_code == 200

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "page_id":               self.page_id,
            "instagram_account_id":  self.instagram_account_id,
            "sig_verification":      True,
        })
        return h
