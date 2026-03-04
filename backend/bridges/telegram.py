"""
Production Telegram Bot Adapter for the Polytope Sovereign OS.

Provides:
- Bot token validation via getMe on startup
- Webhook registration via setWebhook
- Inbound message parsing (text, photo, document, voice, sticker)
- Per-account last-seen tracking
- Health reporting for channel dashboard

Reference: OpenClaw Section 2.2
"""

import httpx
import os
import json
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter


class TelegramBridge(BridgeAdapter):
    """
    Full Telegram Bot API adapter with webhook support,
    inbound parsing, and health reporting.
    """

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.bot_token: str = ""
        self.bot_username: str = ""
        self.api_url = "https://api.telegram.org/bot"
        self.webhook_url: Optional[str] = None
        self.last_activity: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.accounts: Dict[str, Dict[str, Any]] = {}  # chat_id -> info
        self._update_offset: int = 0
        self._polling_task: Optional[asyncio.Task] = None
        self.enabled: bool = True

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to Telegram via Bot Token.
        Validates the token and optionally sets up a webhook.
        """
        self.bot_token = credentials.get("bot_token", "")
        self.webhook_url = credentials.get("webhook_url")

        try:
            async with httpx.AsyncClient() as client:
                # Validate token via getMe
                res = await client.get(f"{self.api_url}{self.bot_token}/getMe")
                data = res.json()
                if data.get("ok"):
                    self.is_connected = True
                    self.bot_username = data["result"].get("username", "unknown")
                    self.last_activity = datetime.now(timezone.utc)
                    self.logger.info(f"Telegram Connected. Bot: @{self.bot_username}")

                    # Register webhook if URL provided
                    if self.webhook_url:
                        await self._register_webhook(client)

                    return True
                else:
                    self.last_error = data.get("description", "Token validation failed")
                    return False
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Telegram connection failed: {e}")
            return False

    async def _register_webhook(self, client: httpx.AsyncClient):
        """Register or update the webhook URL with Telegram."""
        try:
            res = await client.post(
                f"{self.api_url}{self.bot_token}/setWebhook",
                json={"url": self.webhook_url, "drop_pending_updates": False}
            )
            data = res.json()
            if data.get("ok"):
                self.logger.info(f"Telegram webhook registered: {self.webhook_url}")
            else:
                self.last_error = f"Webhook registration failed: {data.get('description')}"
                self.logger.warning(self.last_error)
        except Exception as e:
            self.last_error = f"Webhook registration error: {e}"
            self.logger.error(self.last_error)

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Send a text message to a chat. Supports Markdown formatting."""
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}{self.bot_token}/sendMessage",
                    json={
                        "chat_id": recipient,
                        "text": content,
                        "parse_mode": "Markdown",
                    }
                )
                data = res.json()
                status = "success" if data.get("ok") else "failed"

                if status == "success":
                    self.last_activity = datetime.now(timezone.utc)

                self._persist_to_vault("sent", {
                    "chat_id": recipient,
                    "content": content,
                    "status": status,
                    "timestamp": timestamp,
                    "error": data.get("description"),
                })

                return {"status": status, "response": data}
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"Telegram send_message failed: {e}")
            self._persist_to_vault("sent", {
                "chat_id": recipient, "content": content,
                "status": "exception", "error": str(e),
            })
            return {"status": "failed", "error": f"Bridge communication error: {type(e).__name__}"}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch new messages via getUpdates (long-polling mode)."""
        if not self.is_connected:
            return []

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                res = await client.post(
                    f"{self.api_url}{self.bot_token}/getUpdates",
                    json={"limit": limit, "offset": self._update_offset, "timeout": 30}
                )
                data = res.json()
                if not data.get("ok"):
                    return []

                messages = []
                for item in data.get("result", []):
                    self._update_offset = item["update_id"] + 1

                    msg = item.get("message") or item.get("edited_message")
                    if not msg:
                        continue

                    parsed = self._parse_inbound(msg)
                    messages.append(parsed)

                    # Track account (chat)
                    chat_id = str(msg.get("chat", {}).get("id", ""))
                    self.accounts[chat_id] = {
                        "chat_id": chat_id,
                        "username": msg.get("from", {}).get("username"),
                        "first_name": msg.get("from", {}).get("first_name"),
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                    }

                    self._persist_to_vault("inbox", parsed)

                if messages:
                    self.last_activity = datetime.now(timezone.utc)

                return messages
        except Exception as e:
            self.last_error = str(e)
            return []

    def _parse_inbound(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a Telegram message into a normalized format, supporting multiple types."""
        parsed: Dict[str, Any] = {
            "id": str(msg.get("message_id")),
            "from": str(msg.get("from", {}).get("id", "")),
            "from_username": msg.get("from", {}).get("username"),
            "chat_id": str(msg.get("chat", {}).get("id", "")),
            "timestamp": datetime.fromtimestamp(
                msg.get("date", 0), tz=timezone.utc
            ).isoformat(),
            "protocol": "TELEGRAM",
            "type": "text",
            "body": "",
        }

        if msg.get("text"):
            parsed["body"] = msg["text"]
            parsed["type"] = "text"
        elif msg.get("photo"):
            parsed["type"] = "photo"
            parsed["body"] = msg.get("caption", "")
            parsed["file_id"] = msg["photo"][-1].get("file_id")
        elif msg.get("document"):
            parsed["type"] = "document"
            parsed["body"] = msg.get("caption", "")
            parsed["file_name"] = msg["document"].get("file_name")
            parsed["file_id"] = msg["document"].get("file_id")
        elif msg.get("voice"):
            parsed["type"] = "voice"
            parsed["file_id"] = msg["voice"].get("file_id")
            parsed["duration"] = msg["voice"].get("duration")
        elif msg.get("sticker"):
            parsed["type"] = "sticker"
            parsed["emoji"] = msg["sticker"].get("emoji")
            parsed["file_id"] = msg["sticker"].get("file_id")

        return parsed

    async def process_webhook(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an incoming webhook update from Telegram."""
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            return None

        parsed = self._parse_inbound(msg)
        self.last_activity = datetime.now(timezone.utc)

        chat_id = str(msg.get("chat", {}).get("id", ""))
        self.accounts[chat_id] = {
            "chat_id": chat_id,
            "username": msg.get("from", {}).get("username"),
            "first_name": msg.get("from", {}).get("first_name"),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }

        self._persist_to_vault("inbox", parsed)
        return parsed

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        """Return health report for channel dashboard."""
        return {
            "channel": "telegram",
            "connected": self.is_connected,
            "enabled": self.enabled,
            "bot_username": self.bot_username,
            "webhook_url": self.webhook_url,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "last_error": self.last_error,
            "account_count": len(self.accounts),
            "accounts": list(self.accounts.values()),
        }

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
