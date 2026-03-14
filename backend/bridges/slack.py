import hashlib
import hmac
import secrets
import base64
import time
import os
import json
import httpx
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter

# Constants for Slack OAuth
SLACK_OAUTH_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_OAUTH_TOKEN_URL = "https://slack.com/api/oauth.v2.access"

class SlackBridge(BridgeAdapter):
    """
    Production Slack Bridge using the Slack Web API.
    Supports OAuth 2.0 install flow, Events API, Block Kit messages, and workspace reporting.
    """

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.api_url = "https://slack.com/api"
        self.bot_token: str = ""
        self.default_channel: str = ""
        self.workspace_id: Optional[str] = None
        self.bot_user_id: Optional[str] = None
        self.client_id: Optional[str] = os.getenv("SLACK_CLIENT_ID")
        self.client_secret: Optional[str] = os.getenv("SLACK_CLIENT_SECRET")
        self.redirect_uri: Optional[str] = os.getenv("SLACK_REDIRECT_URI")
        self._signing_secret: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._credentials: Dict[str, Any] = {}

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        from ..config import settings
        if not credentials:
            return False
            
        self._credentials = credentials
        self.bot_token = credentials.get("access_token", credentials.get("bot_token", ""))
        self.default_channel = credentials.get("default_channel", self.default_channel)
        self._refresh_token = credentials.get("refresh_token")
        self._token_expires_at = credentials.get("expires_at", 0.0)
        self._signing_secret = credentials.get("signing_secret") or settings.SLACK_SIGNING_SECRET
        
        if not self.bot_token:
            return False

        # Validate token via auth.test
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.api_url}/auth.test",
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            data = res.json()
            if data.get("ok"):
                self.is_connected = True
                self.workspace_id = data.get("team_id")
                self.bot_user_id = data.get("user_id")
                self.logger.info(f"Slack Connected. Team: {data.get('team')} User: {data.get('user')}")
                return True
            else:
                self.logger.error(f"Slack auth failed: {data.get('error')}")
                self.is_connected = False
                return False

    def verify_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """
        Verify Slack HMAC-SHA256 request signature with replay protection.
        Spec: https://api.slack.com/authentication/verifying-requests-from-slack
        """
        # 1. Replay protection — reject requests older than 5 minutes
        try:
            ts = int(timestamp)
        except (TypeError, ValueError):
            self.logger.warning("[SLACK] Invalid timestamp in signature header.")
            return False

        if abs(time.time() - ts) > 300:
            self.logger.warning(f"[SLACK] Request timestamp too old ({ts}). Possible replay attack.")
            return False

        # 2. Build the signing basestring
        signing_secret = self._signing_secret
        if not signing_secret:
            self.logger.error("[SLACK] SLACK_SIGNING_SECRET not configured — cannot verify.")
            return False

        basestring = f"v0:{timestamp}:{body.decode('utf-8')}".encode("utf-8")

        # 3. Compute HMAC-SHA256
        computed = "v0=" + hmac.new(
            signing_secret.encode("utf-8"),
            basestring,
            hashlib.sha256,
        ).hexdigest()

        # 4. Constant-time comparison prevents timing attacks
        return hmac.compare_digest(computed, signature)

    def _generate_pkce_pair(self) -> tuple[str, str]:
        """Generate PKCE code_verifier and code_challenge (S256 method)."""
        verifier = secrets.token_urlsafe(64)               # 86 chars — within 43–128 range
        digest = hashlib.sha256(verifier.encode("ascii")).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return verifier, challenge

    def build_oauth_url(self, redirect_uri: str, state: str) -> tuple[str, str]:
        """
        Build the Slack OAuth v2 authorization URL with PKCE.
        Returns (authorize_url, code_verifier).
        The caller must persist code_verifier mapped to state in Redis/session.
        """
        verifier, challenge = self._generate_pkce_pair()

        params = {
            "client_id": self.client_id or "",
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join([
                "channels:history",
                "channels:read",
                "channels:write",
                "chat:write",
                "files:write",
                "reactions:write",
                "users:read",
                "im:history",
                "im:write",
                "groups:history",
                "mpim:history",
            ]),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        url = "https://slack.com/oauth/v2/authorize?" + urllib.parse.urlencode(params)
        return url, verifier

    async def handle_oauth_callback(
        self,
        code: str,
        state: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> Dict[str, Any]:
        """
        Exchange the authorization code + PKCE verifier for an access token.
        Persists credentials to the vault and calls connect().
        """
        if not code:
            raise ValueError("Missing authorization code from Slack callback.")

        @BridgeAdapter.resilient_request
        async def exchange_token():
            return await self.client.post(
                "https://slack.com/api/oauth.v2.access",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,  # PKCE verifier
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        resp = await exchange_token()
        data = resp.json()

        if not data.get("ok"):
            raise ValueError(f"Slack token exchange failed: {data.get('error')}")

        authed_user = data.get("authed_user", {})
        creds = {
            "access_token":   data.get("access_token"),          # bot token
            "refresh_token":  data.get("refresh_token"),         # for token rotation
            "expires_at":     time.time() + data.get("expires_in", 43200),
            "signing_secret": self._signing_secret,
            "team_id":        data.get("team", {}).get("id"),
            "bot_user_id":    data.get("bot_user_id"),
            "authed_user_token": authed_user.get("access_token"),
        }

        # Persist to vault using account-specific manifold
        team_id = data.get("team", {}).get("id") or "default"
        await self._save_credentials(creds, account_id=team_id)

        self.logger.info(f"[SLACK] OAuth complete — workspace {data.get('team', {}).get('name')}")
        await self.connect(creds)
        return creds

    async def _ensure_token(self) -> None:
        """
        Checks if the bot token is approaching expiry and refreshes it.
        Uses base.py's _get_valid_token() helper which handles the HTTP exchange.
        No-op if no refresh_token is set (classic tokens never expire).
        """
        if not self._refresh_token or not self._token_expires_at:
            return  # Classic non-rotating token — skip

        updated = await self._get_valid_token(
            creds={
                "access_token":  self.bot_token,
                "refresh_token": self._refresh_token,
                "expires_at":    self._token_expires_at,
            },
            token_url="https://slack.com/api/tooling.tokens.rotate",
            client_id=self.client_id or "",
            client_secret=self.client_secret or "",
        )

        if updated["access_token"] != self.bot_token:
            self.logger.info("[SLACK] Bot token rotated successfully.")
            self.bot_token = updated["access_token"]
            self._token_expires_at = updated.get("expires_at", 0)
            if updated.get("refresh_token"):
                self._refresh_token = updated["refresh_token"]

            # Persist updated token to vault
            creds.update({
                "access_token":  self.bot_token,
                "refresh_token": self._refresh_token,
                "expires_at":    self._token_expires_at,
            })
            await self._save_credentials(creds, account_id=self.workspace_id or "default")

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        await self._ensure_token()

        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        target = recipient if recipient else self.default_channel
        if not target:
            return {"status": "failed", "error": "No recipient specified"}

        payload: Dict[str, Any] = {"channel": target, "text": content}
        if kwargs.get("blocks"):
            payload["blocks"] = kwargs["blocks"]
        if kwargs.get("thread_ts"):
            payload["thread_ts"] = kwargs["thread_ts"]

        @BridgeAdapter.resilient_request
        async def _post():
            return await self.client.post(
                f"{self.api_url}/chat.postMessage",
                headers={"Authorization": f"Bearer {self.bot_token}"},
                json=payload,
            )

        try:
            res = await _post()
            data = res.json()
            if data.get("ok"):
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "ts": data.get("ts"), "channel": data.get("channel")}
            self.last_error = data.get("error")
            return {"status": "failed", "error": data.get("error")}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def process_webhook(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Standardized entry point for Slack Events API."""
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            # Only handle channel messages (ignore bot messages, edits, etc.)
            if event.get("type") == "message" and not event.get("subtype"):
                if event.get("user") == self.bot_user_id:
                    return None # Ignore self

                normalized = {
                    "id": event.get("ts"),
                    "from": event.get("user"),
                    "body": event.get("text", ""),
                    "channel_id": event.get("channel"),
                    "protocol": "SLACK",
                    "account_id": self.workspace_id,
                    "timestamp": datetime.fromtimestamp(float(event.get("ts", "0")), timezone.utc).isoformat(),
                }
                await self._dispatch_inbound(normalized)
            return None
        return None

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Slack doesn't support easy 'fetch unread' via Web API without heavy scope. Requires Event API."""
        return []

    async def validate_integrity(self) -> bool:
        if not self.bot_token: return False
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{self.api_url}/auth.test",
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            return res.json().get("ok", False)

    def get_health(self) -> Dict[str, Any]:
        health = super().get_health()
        if self.is_connected:
            health.update({
                "workspace_id": self.workspace_id,
                "bot_user_id": self.bot_user_id,
                "default_channel": self.default_channel
            })
        return health
