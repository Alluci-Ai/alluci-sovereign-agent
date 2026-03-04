import httpx
import os
import json
import urllib.parse
from datetime import datetime
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

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.api_url = "https://slack.com/api"
        self.bot_token: str = ""
        self.default_channel: str = ""
        self.workspace_id: Optional[str] = None
        self.bot_user_id: Optional[str] = None
        # OAuth client credentials are expected from environment or vault
        self.client_id: Optional[str] = os.getenv("SLACK_CLIENT_ID")
        self.client_secret: Optional[str] = os.getenv("SLACK_CLIENT_SECRET")
        self.redirect_uri: Optional[str] = os.getenv("SLACK_REDIRECT_URI")
        # Load persisted token if present
        self._load_token_from_vault()

    # ---------------------------------------------------------------------
    # OAuth 2.0 Install Flow
    # ---------------------------------------------------------------------
    def generate_install_url(self, state: str = "state") -> str:
        """Return the Slack App install URL with required scopes.
        The caller can embed this URL in a UI for the admin to click.
        """
        if not self.client_id or not self.redirect_uri:
            raise RuntimeError("Slack client_id or redirect_uri not configured")
        scopes = [
            "channels:read",
            "chat:write",
            "chat:write.public",
            "commands",
            "incoming-webhook",
            "app_mentions:read",
            "im:read",
            "im:write",
        ]
        params = {
            "client_id": self.client_id,
            "scope": ",".join(scopes),
            "redirect_uri": self.redirect_uri,
            "state": state,
        }
        return f"{SLACK_OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """Exchange the temporary `code` from the OAuth redirect for a bot token.
        Persists the token to the bridge vault for later use.
        """
        if not self.client_id or not self.client_secret or not self.redirect_uri:
            raise RuntimeError("Slack OAuth credentials not configured")
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(SLACK_OAUTH_TOKEN_URL, data=payload)
            data = resp.json()
            if not data.get("ok"):
                self.logger.error(f"Slack OAuth exchange failed: {data.get('error')}")
                return {"status": "failed", "error": data.get("error")}
            # Store relevant fields
            self.bot_token = data["access_token"]
            self.workspace_id = data.get("team", {}).get("id")
            self.bot_user_id = data.get("authed_user", {}).get("id")
            # Persist token securely
            self._persist_token_to_vault({
                "access_token": self.bot_token,
                "team_id": self.workspace_id,
                "bot_user_id": self.bot_user_id,
                "scope": data.get("scope"),
                "token_type": data.get("token_type"),
            })
            self.is_connected = True
            self.logger.info(f"Slack OAuth succeeded for workspace {self.workspace_id}")
            return {"status": "success", "team_id": self.workspace_id}

    def _persist_token_to_vault(self, token_data: Dict[str, Any]):
        """Write the OAuth token JSON to the bridge vault (plain JSON for now)."""
        path = os.path.join(self.vault_path, "slack_token.json")
        try:
            with open(path, "w") as f:
                json.dump(token_data, f)
        except Exception as e:
            self.logger.error(f"Failed to persist Slack token: {e}")

    def _load_token_from_vault(self):
        """Load persisted token if it exists; set connection state accordingly."""
        path = os.path.join(self.vault_path, "slack_token.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    self.bot_token = data.get("access_token", "")
                    self.workspace_id = data.get("team_id")
                    self.bot_user_id = data.get("bot_user_id")
                    self.is_connected = bool(self.bot_token)
            except Exception as e:
                self.logger.error(f"Failed to load Slack token: {e}")

    # ---------------------------------------------------------------------
    # Connection (legacy credentials fallback)
    # ---------------------------------------------------------------------
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect using explicit credentials or previously stored OAuth token.
        Expected credentials: {"bot_token": "xoxb-...", "default_channel": "C12345"}
        """
        # Prefer explicit credentials if provided
        if credentials:
            self.bot_token = credentials.get("bot_token", self.bot_token)
            self.default_channel = credentials.get("default_channel", self.default_channel)
        # If we still lack a token, attempt to load from vault (already done in __init__)
        if not self.bot_token:
            self.logger.error("Slack token missing; OAuth flow required.")
            return False
        # Validate token via auth.test
        try:
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
                    self.logger.info(f"Slack Connected. Bot ID: {data.get('bot_id')} User: {data.get('user')}")
                    return True
                else:
                    self.logger.error(f"Slack auth failed: {data.get('error')}")
                    return False
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    # ---------------------------------------------------------------------
    # Message Sending (Block Kit support)
    # ---------------------------------------------------------------------
    async def send_message(self, recipient: str, content: str, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Send a message to a Slack channel/user.
        If `blocks` is provided, it will be sent as a Block Kit payload for rich formatting.
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        target = recipient if recipient else self.default_channel
        if not target:
            return {"status": "failed", "error": "No recipient specified"}

        payload: Dict[str, Any] = {"channel": target, "text": content}
        if blocks:
            payload["blocks"] = blocks

        timestamp = datetime.now().isoformat()
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}/chat.postMessage",
                    headers={"Authorization": f"Bearer {self.bot_token}"},
                    json=payload,
                )
                data = res.json()
                status = "success" if data.get("ok") else "failed"
                # Vault Persistence
                self._persist_to_vault("sent", {
                    "channel": target,
                    "content": content,
                    "blocks": blocks,
                    "status": status,
                    "slack_ts": data.get("ts"),
                    "timestamp": timestamp,
                    "error": data.get("error"),
                })
                if status == "success":
                    return {"status": "success", "ts": data.get("ts")}
                else:
                    return {"status": "failed", "error": data.get("error")}
        except Exception as e:
            self._persist_to_vault("sent", {
                "channel": target,
                "content": content,
                "blocks": blocks,
                "status": "exception",
                "timestamp": timestamp,
                "error": str(e),
            })
            self.logger.error(f"Slack send_message failed: {e}")
            return {"status": "failed", "error": f"Bridge communication error: {type(e).__name__}"}

    # ---------------------------------------------------------------------
    # Events API handling
    # ---------------------------------------------------------------------
    async def process_event(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an incoming Slack Events API payload.
        Returns a dict for URL verification challenges or None for regular events.
        """
        # URL verification challenge
        if payload.get("type") == "url_verification":
            return {"challenge": payload.get("challenge")}

        # Event callbacks
        if payload.get("type") == "event_callback":
            event = payload.get("event", {})
            # Only handle channel messages (ignore bot messages, edits, etc.)
            if event.get("type") == "message" and not event.get("subtype"):
                normalized = {
                    "id": event.get("ts"),
                    "from": event.get("user"),
                    "from_name": event.get("username", ""),
                    "body": event.get("text", ""),
                    "channel_id": event.get("channel"),
                    "protocol": "SLACK",
                    "account_id": self.workspace_id,
                    "timestamp": datetime.fromtimestamp(float(event.get("ts", "0"))).isoformat(),
                }
                self._persist_to_vault("inbox", normalized)
                if self.on_event:
                    await self.on_event("message", normalized)
            return None
        return None

    # ---------------------------------------------------------------------
    # Workspace / Health Reporting
    # ---------------------------------------------------------------------
    async def get_workspace_info(self) -> Dict[str, Any]:
        """Retrieve basic workspace information (team name, id, channel count)."""
        if not self.is_connected:
            return {}
        async with httpx.AsyncClient() as client:
            # Team info
            team_res = await client.get(
                f"{self.api_url}/team.info",
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            team_data = team_res.json().get("team", {})
            # Channel list (public channels for count)
            chan_res = await client.get(
                f"{self.api_url}/conversations.list",
                params={"types": "public_channel", "limit": 1000},
                headers={"Authorization": f"Bearer {self.bot_token}"},
            )
            chan_data = chan_res.json().get("channels", [])
            return {
                "team_id": team_data.get("id"),
                "team_name": team_data.get("name"),
                "channel_count": len(chan_data),
            }

    def get_health(self) -> Dict[str, Any]:
        """Return health report for the Slack channel dashboard, including workspace count."""
        health = {
            "channel": "slack",
            "connected": self.is_connected,
            "enabled": self.enabled,
            "workspace_id": self.workspace_id,
            "bot_user_id": self.bot_user_id,
            "default_channel": self.default_channel,
            "last_error": self.last_error,
        }
        try:
            info = asyncio.get_event_loop().run_until_complete(self.get_workspace_info())
            health.update(info)
        except Exception as e:
            self.logger.debug(f"Workspace info fetch failed: {e}")
        return health

    # ---------------------------------------------------------------------
    # Utility persistence (unchanged)
    # ---------------------------------------------------------------------
    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        """Writes structured data to the isolated bridge vault."""
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
