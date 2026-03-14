"""
Sovereign Google Chat Bridge — Service Account + REST API.

Authentication:
  Service Account JSON → JWT signed by the SA private key → Bearer token.
  No user OAuth required. The SA must be added to each Space as a member.

Webhook Verification:
  Inbound App interactions carry a Bearer JWT signed by:
    chat@system.gserviceaccount.com (RS256)
  JWKS fetched from Google's OIDC endpoint, cached for 1 hour.

Features:
  - Send text and Card v2 messages to Spaces
  - Reply in threads
  - Handle MESSAGE, CARD_CLICKED, SLASH_COMMAND, ADDED_TO_SPACE events
  - process_event() dispatches normalised inbound dict
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .base import BridgeAdapter

CHAT_API = "https://chat.googleapis.com/v1"
GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_CHAT_ISSUER = "chat@system.gserviceaccount.com"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


class GoogleChatBridge(BridgeAdapter):
    """
    Production Google Chat Bridge.
    Uses Service Account JWT authentication with async token refresh
    and cached JWKS verification.
    """

    JWKS_TTL    = 3600.0   # Refresh JWKS cache every hour
    TOKEN_SLACK = 60.0     # Refresh access token 60s before expiry

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self._sa_credentials: Optional[Dict] = None
        self._access_token:   Optional[str] = None
        self._token_expires:  float = 0.0
        self._project_id:     Optional[str] = None

        # JWKS cache
        self._jwks_cache:      Optional[Dict] = None
        self._jwks_fetched_at: float = 0.0

        # Load service account from vault on init
        self._load_sa_from_vault()

    # ── Vault Helpers ─────────────────────────────────────────────────────────

    def _load_sa_from_vault(self) -> None:
        path = os.path.join(self.vault_path, "service_account.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self._sa_credentials = json.load(f)
                self._project_id = self._sa_credentials.get("project_id")
                self.logger.debug("[GCHAT] Service account loaded from vault.")
            except Exception as e:
                self.logger.error(f"[GCHAT] Failed to load SA from vault: {e}")

    def _save_sa_to_vault(self, sa: Dict) -> None:
        path = os.path.join(self.vault_path, "service_account.json")
        with open(path, "w") as f:
            json.dump(sa, f)
        os.chmod(path, 0o600)

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect using Service Account JSON credentials.
        credentials may be:
          - A full SA JSON dict (type="service_account")
          - {"service_account_file": "/path/to/sa.json"}
        """
        from ..config import settings

        if credentials.get("type") == "service_account":
            self._sa_credentials = credentials
        elif credentials.get("service_account_file"):
            with open(credentials["service_account_file"]) as f:
                self._sa_credentials = json.load(f)
        elif settings.GOOGLE_CHAT_SERVICE_ACCOUNT_FILE:
            with open(settings.GOOGLE_CHAT_SERVICE_ACCOUNT_FILE) as f:
                self._sa_credentials = json.load(f)
        elif self._sa_credentials:
            pass  # Already loaded from vault
        else:
            self.last_error = "No service account credentials provided."
            return False

        self._project_id = self._sa_credentials.get("project_id")
        self._save_sa_to_vault(self._sa_credentials)

        success = await self._refresh_access_token()
        if success:
            self.is_connected = True
            self.logger.info(f"[GCHAT] Connected — project: {self._project_id}")
        return success

    # ── Async Token Refresh ───────────────────────────────────────────────────

    async def _refresh_access_token(self) -> bool:
        """
        Mint a short-lived access token by signing a JWT with the SA private key.
        Fully async — no blocking requests library calls.
        """
        if self._access_token and time.time() < self._token_expires - self.TOKEN_SLACK:
            return True

        if not self._sa_credentials:
            return False

        try:
            import base64
            import json as _json
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding

            now    = int(time.time())
            expiry = now + 3600

            # JWT header + claims
            header = base64.urlsafe_b64encode(
                _json.dumps({"alg": "RS256", "typ": "JWT"}).encode()
            ).rstrip(b"=")
            claims = base64.urlsafe_b64encode(
                _json.dumps({
                    "iss":   self._sa_credentials["client_email"],
                    "scope": "https://www.googleapis.com/auth/chat.messages",
                    "aud":   GOOGLE_TOKEN_URL,
                    "iat":   now,
                    "exp":   expiry,
                }).encode()
            ).rstrip(b"=")

            # Sign with RSA private key from service account
            private_key = serialization.load_pem_private_key(
                self._sa_credentials["private_key"].encode(),
                password=None,
            )
            signing_input = header + b"." + claims
            signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
            sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=")
            jwt_token = (signing_input + b"." + sig_b64).decode()

            # Exchange JWT for access token
            resp = await self.client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                    "assertion":  jwt_token,
                },
            )
            resp.raise_for_status()
            token_data = resp.json()
            self._access_token  = token_data["access_token"]
            self._token_expires = time.time() + token_data.get("expires_in", 3600)
            return True

        except Exception as e:
            self.logger.error(f"[GCHAT] Token refresh failed: {e}")
            return False

    # ── JWKS Cache ────────────────────────────────────────────────────────────

    async def _get_jwks(self) -> Optional[Dict]:
        """Fetch Google's JWKS with 1-hour cache to avoid rate limits."""
        now = time.time()
        if self._jwks_cache and (now - self._jwks_fetched_at) < self.JWKS_TTL:
            return self._jwks_cache
        try:
            resp = await self.client.get(GOOGLE_CERTS_URL, timeout=10.0)
            resp.raise_for_status()
            self._jwks_cache      = resp.json()
            self._jwks_fetched_at = now
            return self._jwks_cache
        except Exception as e:
            self.logger.error(f"[GCHAT] JWKS fetch failed: {e}")
            return self._jwks_cache  # Return stale cache

    # ── Webhook Verification ──────────────────────────────────────────────────

    async def verify_webhook(self, authorization: str, body: bytes = b"") -> bool:
        """
        Verify a Google Chat app interaction via OIDC JWT.
        The Authorization header carries: Bearer <JWT>
        """
        from ..config import settings

        token = authorization.removeprefix("Bearer ").strip()
        if not token:
            return False

        audience = settings.GOOGLE_CHAT_AUDIENCE or self._project_id

        jwks = await self._get_jwks()
        if not jwks:
            self.logger.error("[GCHAT] No JWKS available.")
            return False

        try:
            from jose import jwt as jose_jwt
            payload = jose_jwt.decode(
                token, jwks,
                algorithms=["RS256"],
                audience=audience,
                issuer=GOOGLE_CHAT_ISSUER,
                options={
                    "verify_aud": bool(audience),
                    "verify_iss": True,
                    "verify_exp": True,
                },
            )
            self.logger.debug(f"[GCHAT] JWT verified. Sub: {payload.get('sub')}")
            return True
        except Exception as e:
            self.logger.warning(f"[GCHAT] Webhook JWT verification failed: {e}")
            return False

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Send a message to a Google Chat Space.
        recipient: space resource name, e.g. "spaces/XXXXXXXX"
        kwargs:
            thread_key (str): Reply in a named thread
            card (dict):      Card v2 JSON payload
        """
        if not await self._refresh_access_token():
            return {"status": "failed", "error": "Token unavailable"}

        url    = f"{CHAT_API}/{recipient}/messages"
        params = {}
        if kwargs.get("thread_key"):
            params["messageReplyOption"] = "REPLY_MESSAGE_FALLBACK_TO_NEW_THREAD"

        payload: Dict[str, Any] = {}
        if content:
            payload["text"] = content
        if kwargs.get("card"):
            payload["cardsV2"] = [
                {
                    "cardId": "alluci-card",
                    "card":   kwargs["card"],
                }
            ]
        if kwargs.get("thread_key"):
            payload["thread"] = {"threadKey": kwargs["thread_key"]}

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type":  "application/json",
        }

        @BridgeAdapter.resilient_request
        async def _post():
            return await self.client.post(url, headers=headers, json=payload, params=params)

        try:
            resp = await _post()
            data = resp.json()
            if resp.status_code == 200:
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "name": data.get("name")}
            self.last_error = data.get("error", {}).get("message", resp.text)
            return {"status": "failed", "error": self.last_error}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    # ── Inbound Event Processing ──────────────────────────────────────────────

    async def process_event(
        self, payload: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse Google Chat App interaction events:
        MESSAGE, CARD_CLICKED, SLASH_COMMAND, ADDED_TO_SPACE, REMOVED_FROM_SPACE.
        """
        event_type = payload.get("type", "")
        space      = payload.get("space", {})

        if event_type == "MESSAGE":
            msg    = payload.get("message", {})
            sender = msg.get("sender", {})

            # Check for slash commands
            slash = msg.get("slashCommand", {})
            body  = msg.get("text", "")
            if slash:
                body = f"/{slash.get('commandName', '')} {body}".strip()

            normalized = {
                "id":          msg.get("name"),
                "from":        sender.get("name"),
                "from_name":   sender.get("displayName"),
                "body":        body,
                "space":       space.get("name"),
                "thread":      msg.get("thread", {}).get("name"),
                "protocol":    "GCHAT",
                "timestamp":   msg.get("createTime"),
                "slash_command": slash.get("commandName") if slash else None,
            }
            await self._dispatch_inbound(normalized)
            return normalized

        elif event_type == "CARD_CLICKED":
            action  = payload.get("action", {})
            msg     = payload.get("message", {})
            self.logger.info(
                f"[GCHAT] Card clicked: {action.get('actionMethodName')} "
                f"in space {space.get('name')}"
            )
            normalized = {
                "id":        msg.get("name"),
                "from":      payload.get("user", {}).get("name"),
                "body":      f"[Card Action: {action.get('actionMethodName')}]",
                "space":     space.get("name"),
                "protocol":  "GCHAT",
                "type":      "card_click",
                "action":    action,
                "timestamp": str(int(time.time())),
            }
            await self._dispatch_inbound(normalized)
            return normalized

        elif event_type == "ADDED_TO_SPACE":
            self.logger.info(f"[GCHAT] App added to space: {space.get('name')}")

        elif event_type == "REMOVED_FROM_SPACE":
            self.logger.info(f"[GCHAT] App removed from space: {space.get('name')}")

        return None

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []  # Push-only via app interactions

    async def validate_integrity(self) -> bool:
        return await self._refresh_access_token()

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "project_id":   self._project_id,
            "token_valid":  bool(self._access_token and time.time() < self._token_expires),
            "jwks_cached":  bool(self._jwks_cache),
            "jwks_age_s":   int(time.time() - self._jwks_fetched_at) if self._jwks_cache else None,
        })
        return h
