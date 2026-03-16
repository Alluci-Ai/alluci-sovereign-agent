"""
Sovereign X (Twitter) Bridge — X API v2 with OAuth 2.0 PKCE.

OAuth Flow:
  PKCE: build_oauth_url() → /api/oauth/x/callback → handle_oauth_callback()

Polling:
  Mentions polling (every 15 minutes — free tier allows 1 call/15m on /mentions)
  DM polling (every 15 minutes via /dm_conversations)

Rate Limits:
  All requests track x-rate-limit-remaining; on 429 the bridge backs off
  until x-rate-limit-reset.

Refresh:
  OAuth 2.0 refresh_token used automatically. X tokens expire in 2 hours.
"""

import asyncio
import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .base import BridgeAdapter

X_API = "https://api.twitter.com/2"
X_AUTH = "https://twitter.com/i/oauth2"


class XBridge(BridgeAdapter):
    """
    Production X/Twitter Bridge.
    PKCE OAuth 2.0, automatic token refresh, rate-limit-aware polling,
    tweet posting, DM sending, and mention/DM inbox polling.
    """

    SCOPES = [
        "tweet.read", "tweet.write",
        "users.read",
        "dm.read", "dm.write",
        "offline.access",
    ]

    MENTION_INTERVAL = 900    # 15 minutes
    DM_INTERVAL      = 900    # 15 minutes

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self._access_token:   Optional[str] = None
        self._refresh_token:  Optional[str] = None
        self._expires_at:     float = 0.0
        self._client_id:      Optional[str] = os.getenv("TWITTER_CLIENT_ID")
        self._client_secret:  Optional[str] = os.getenv("TWITTER_CLIENT_SECRET")
        self._my_user_id:     Optional[str] = None
        self._my_username:    Optional[str] = None
        self._last_mention_id: Optional[str] = None
        self._last_dm_event_id: Optional[str] = None

        # Rate limit state per endpoint
        self._rate_limits: Dict[str, float] = {}   # endpoint → reset_timestamp
        self._poll_task: Optional[asyncio.Task] = None

    # ── PKCE ──────────────────────────────────────────────────────────────────

    def _pkce_pair(self) -> Tuple[str, str]:
        verifier  = secrets.token_urlsafe(64)
        digest    = hashlib.sha256(verifier.encode()).digest()
        challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
        return verifier, challenge

    def build_oauth_url(self, redirect_uri: str, state: str) -> Tuple[str, str]:
        """Returns (authorize_url, code_verifier). Caller persists verifier by state."""
        verifier, challenge = self._pkce_pair()
        params = {
            "response_type":         "code",
            "client_id":             self._client_id or "",
            "redirect_uri":          redirect_uri,
            "scope":                 " ".join(self.SCOPES),
            "state":                 state,
            "code_challenge":        challenge,
            "code_challenge_method": "S256",
        }
        url = f"{X_AUTH}/authorize?" + urllib.parse.urlencode(params)
        return url, verifier

    async def handle_oauth_callback(
        self, code: str, state: str = "", code_verifier: str = "", redirect_uri: str = ""
    ) -> Dict[str, Any]:
        """Exchange PKCE code for tokens and connect."""
        if not code or not code_verifier:
            raise ValueError("Missing code or code_verifier.")

        # X uses HTTP Basic auth for the token endpoint
        credentials_b64 = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()

        resp = await self.client.post(
            f"{X_AUTH}/token",
            headers={
                "Authorization":  f"Basic {credentials_b64}",
                "Content-Type":   "application/x-www-form-urlencoded",
            },
            content=urllib.parse.urlencode({
                "code":            code,
                "grant_type":      "authorization_code",
                "redirect_uri":    redirect_uri,
                "code_verifier":   code_verifier,
            }),
        )
        resp.raise_for_status()
        data = resp.json()

        creds = {
            "access_token":  data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "expires_at":    time.time() + data.get("expires_in", 7200),
            "client_id":     self._client_id,
            "client_secret": self._client_secret,
        }
        await self._save_credentials(creds)
        await self.connect(creds)
        return creds

    async def _save_credentials(self, creds: Dict[str, Any]) -> None:
        await super()._save_credentials(creds, account_id=self._my_user_id or "default")

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self._access_token  = credentials.get("access_token")
        self._refresh_token = credentials.get("refresh_token")
        self._expires_at    = credentials.get("expires_at", 0.0)
        self._client_id     = credentials.get("client_id") or self._client_id
        self._client_secret = credentials.get("client_secret") or self._client_secret

        if not self._access_token:
            return False

        await self._ensure_token()

        try:
            resp = await self._get(f"{X_API}/users/me", params={"user.fields": "id,username"})
            if resp.status_code == 200:
                user = resp.json().get("data", {})
                self._my_user_id  = user.get("id")
                self._my_username = user.get("username")
                self.is_connected = True
                self.logger.info(f"[X] Connected as @{self._my_username}")

                # Start polling
                if self._poll_task and not self._poll_task.done():
                    self._poll_task.cancel()
                self._poll_task = asyncio.create_task(self._poll_loop())
                return True

            self.last_error = resp.text
            return False
        except Exception as e:
            self.last_error = str(e)
            return False

    # ── Token Refresh ─────────────────────────────────────────────────────────

    async def _ensure_token(self) -> None:
        """Refresh the access token if it is within 60 seconds of expiry."""
        if not self._refresh_token:
            return
        if time.time() < self._expires_at - 60:
            return

        self.logger.info("[X] Access token expiring — refreshing.")
        credentials_b64 = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()

        try:
            resp = await self.client.post(
                f"{X_AUTH}/token",
                headers={
                    "Authorization": f"Basic {credentials_b64}",
                    "Content-Type":  "application/x-www-form-urlencoded",
                },
                content=urllib.parse.urlencode({
                    "grant_type":    "refresh_token",
                    "refresh_token": self._refresh_token,
                }),
            )
            resp.raise_for_status()
            data = resp.json()
            self._access_token  = data["access_token"]
            self._refresh_token = data.get("refresh_token", self._refresh_token)
            self._expires_at    = time.time() + data.get("expires_in", 7200)
            self.logger.info("[X] Token refreshed successfully.")

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

        except Exception as e:
            self.logger.error(f"[X] Token refresh failed: {e}")

    # ── Rate Limit Aware HTTP ─────────────────────────────────────────────────

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        """GET with automatic rate limit backoff."""
        await self._ensure_token()
        endpoint_key = url.split("?")[0]

        # Back off if we know this endpoint is rate-limited
        reset_ts = self._rate_limits.get(endpoint_key, 0)
        if reset_ts > time.time():
            wait = reset_ts - time.time() + 1
            self.logger.warning(f"[X] Rate limit active on {endpoint_key} — waiting {wait:.0f}s.")
            await asyncio.sleep(wait)

        resp = await self.client.get(
            url,
            headers={"Authorization": f"Bearer {self._access_token}"},
            **kwargs,
        )

        if resp.status_code == 429:
            reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 900))
            self._rate_limits[endpoint_key] = float(reset)
            self.logger.warning(f"[X] 429 on {endpoint_key}. Reset at {reset}.")

        # Update rate limit state from response headers
        remaining = resp.headers.get("x-rate-limit-remaining")
        if remaining is not None and int(remaining) == 0:
            reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 900))
            self._rate_limits[endpoint_key] = float(reset)

        return resp

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Post a tweet or send a DM.
        If recipient is a numeric user ID → DM.
        If recipient is empty → public tweet.
        kwargs:
            in_reply_to_tweet_id (str): reply to a tweet
            media_ids (list[str]):      attach uploaded media
        """
        await self._ensure_token()
        if not self.is_connected:
            return {"status": "failed", "error": "Not connected"}

        if recipient and recipient.isdigit():
            return await self._send_dm(recipient, content)
        return await self._post_tweet(content, **kwargs)

    async def _post_tweet(self, content: str, **kwargs) -> Dict[str, Any]:
        """Post a public tweet."""
        body: Dict[str, Any] = {"text": content}
        if kwargs.get("in_reply_to_tweet_id"):
            body["reply"] = {"in_reply_to_tweet_id": kwargs["in_reply_to_tweet_id"]}
        if kwargs.get("media_ids"):
            body["media"] = {"media_ids": kwargs["media_ids"]}

        resp = await self.client.post(
            f"{X_API}/tweets",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type":  "application/json",
            },
            json=body,
        )
        if resp.status_code == 201:
            self.last_activity = datetime.now(timezone.utc).isoformat()
            return {"status": "success", "id": resp.json()["data"]["id"], "type": "tweet"}
        self.last_error = resp.text
        return {"status": "failed", "error": resp.text}

    async def _send_dm(self, recipient_id: str, content: str) -> Dict[str, Any]:
        """Send a Direct Message."""
        resp = await self.client.post(
            f"{X_API}/dm_conversations/with/{recipient_id}/messages",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type":  "application/json",
            },
            json={"text": content},
        )
        if resp.status_code == 201:
            self.last_activity = datetime.now(timezone.utc).isoformat()
            return {"status": "success", "type": "dm"}
        return {"status": "failed", "error": resp.text}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    # ── Polling ───────────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        """Poll mentions and DMs on separate 15-minute intervals."""
        mention_due = time.time()
        dm_due      = time.time() + 60  # offset DM poll by 60s

        while self.is_connected:
            now = time.time()
            try:
                if now >= mention_due:
                    await self._poll_mentions()
                    mention_due = now + self.MENTION_INTERVAL

                if now >= dm_due:
                    await self._poll_dms()
                    dm_due = now + self.DM_INTERVAL

            except asyncio.CancelledError:
                return
            except Exception as e:
                self.logger.error(f"[X] Poll loop error: {e}")

            await asyncio.sleep(30)  # Check every 30s whether a poll is due

    async def _poll_mentions(self) -> None:
        """Fetch new @mentions since _last_mention_id."""
        if not self._my_user_id:
            return

        params: Dict[str, Any] = {
            "max_results":  10,
            "tweet.fields": "id,text,author_id,created_at,in_reply_to_user_id",
            "expansions":   "author_id",
            "user.fields":  "username",
        }
        if self._last_mention_id:
            params["since_id"] = self._last_mention_id

        resp = await self._get(f"{X_API}/users/{self._my_user_id}/mentions", params=params)
        if resp.status_code != 200:
            return

        data     = resp.json()
        tweets   = data.get("data", [])
        users    = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

        for tweet in reversed(tweets):   # oldest first
            author_id = tweet.get("author_id", "")
            author    = users.get(author_id, {})
            await self._dispatch_inbound({
                "id":        tweet["id"],
                "from_id":   author_id,
                "chat_id":   tweet["id"], # Mentions are essentially their own chat context
                "username":  author.get("username", ""),
                "body":      tweet["text"],
                "type":      "mention",
                "protocol":  "X",
                "timestamp": tweet.get("created_at"),
            })
            self._last_mention_id = tweet["id"]

        if tweets:
            self.last_activity = datetime.now(timezone.utc).isoformat()

    async def _poll_dms(self) -> None:
        """Fetch new DM events."""
        params: Dict[str, Any] = {
            "max_results":  20,
            "event.fields": "id,text,sender_id,created_at,attachments",
        }
        if self._last_dm_event_id:
            params["since_id"] = self._last_dm_event_id

        resp = await self._get(f"{X_API}/dm_events", params=params)
        if resp.status_code != 200:
            return

        events = resp.json().get("data", [])
        for event in reversed(events):
            sender_id = event.get("sender_id", "")
            if sender_id == self._my_user_id:
                continue  # Skip own messages
            await self._dispatch_inbound({
                "id":        event["id"],
                "from_id":   sender_id,
                "chat_id":   sender_id,
                "body":      event.get("text", ""),
                "type":      "dm",
                "protocol":  "X",
                "timestamp": event.get("created_at"),
            })
            self._last_dm_event_id = event["id"]

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []  # Push via _poll_loop

    async def validate_integrity(self) -> bool:
        resp = await self._get(f"{X_API}/users/me")
        return resp.status_code == 200

    async def disconnect(self) -> None:
        self.is_connected = False
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        await super().disconnect()

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "username":         self._my_username,
            "token_expires_at": self._expires_at,
            "rate_limits":      {k: v - time.time() for k, v in self._rate_limits.items()},
            "last_mention_id":  self._last_mention_id,
        })
        return h
