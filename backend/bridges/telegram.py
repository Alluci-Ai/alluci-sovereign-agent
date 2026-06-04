"""
Production Telegram Bot Adapter for the Polytope Sovereign OS.

Provides:
- Bot token validation via getMe on startup
- Webhook registration via setWebhook
- Inbound message parsing (text, photo, document, voice, sticker)
- Per-account last-seen tracking
- Health reporting for channel dashboard

Reference: Sovereign Spec Section 2.2
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

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.bot_token: str = ""
        self.bot_username: str = ""
        self.api_url = "https://api.telegram.org/bot"
        self.webhook_url: Optional[str] = None
        self.last_activity: Optional[datetime] = None  # type: ignore
        self.last_error: Optional[str] = None
        self.accounts: Dict[str, Dict[str, Any]] = {}  # chat_id -> info
        self._update_offset: int = 0
        self.enabled: bool = True
        self._load_accounts()

    @BridgeAdapter.resilient_request
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to Telegram via Bot Token.
        Validates the token and optionally sets up a webhook.
        """
        self.bot_token = credentials.get("bot_token", "")
        
        public_url = os.getenv("DAEMON_PUBLIC_URL")
        if public_url:
            self.webhook_url = f"{public_url.rstrip('/')}/api/webhook/telegram/{self.bot_token[:8]}"
        else:
            self.webhook_url = credentials.get("webhook_url")
        self.last_error = None

        # 1. Bot Token Validation (Sovereign Spec §2.2)
        res = await self.client.get(f"{self.api_url}{self.bot_token}/getMe")
        data = res.json()
        if not data.get("ok"):
            self.last_error = data.get("description", "Token validation failed")
            self.logger.error(f"Telegram Auth Failed: {self.last_error}")
            return False

        self.is_connected = True
        self.bot_username = data["result"].get("username", "unknown")
        self.last_activity = datetime.now(timezone.utc)
        self.logger.info(f"Telegram Connected. Bot: @{self.bot_username}")

        # 2. Auto-register Webhook (Sovereign Spec §2.2)
        if self.webhook_url:
            await self._register_webhook()
        else:
            # Clean up old webhooks if we're now in polling mode
            try:
                await self.client.get(f"{self.api_url}{self.bot_token}/deleteWebhook")
                self.logger.info("Telegram: Webhook cleared, entering long-polling mode.")
            except Exception as e:
                self.logger.warning(f"Telegram: Webhook clear failed (polling mode): {e}")
            # Start background long-polling loop
            asyncio.create_task(self._poll_loop())

        return True

    @BridgeAdapter.resilient_request
    async def _register_webhook(self):
        """Register or update the webhook URL with Telegram."""
        res = await self.client.post(
            f"{self.api_url}{self.bot_token}/setWebhook",
            json={"url": self.webhook_url, "drop_pending_updates": False}
        )
        data = res.json()
        if data.get("ok"):
            self.logger.info(f"Telegram webhook registered: {self.webhook_url}")
        else:
            self.last_error = f"Webhook registration failed: {data.get('description')}"
            self.logger.warning(self.last_error)

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Transmit text message via Telegram."""
        return await self.send(recipient, content)

    @BridgeAdapter.resilient_request
    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Sovereign send method (Telegram)."""
        if not self.is_connected or not self.bot_token:
            return {"ok": False, "error": "Bot not connected"}
        
        self.last_activity = datetime.now(timezone.utc).isoformat()  # type: ignore
        url = f"{self.api_url}{self.bot_token}/sendMessage"
        payload = {
            "chat_id": recipient,
            "text": content,
            "parse_mode": "Markdown",
        }
        
        # Merge extra kwargs (Sovereign Spec §2.3)
        payload.update(kwargs)

        resp = await self.client.post(url, json=payload)
        res = resp.json()
        if not res.get("ok"):
            self.last_error = f"API Error: {res.get('description')}"
            return {"status": "failed", "error": self.last_error}
        
        return {"status": "success", "id": res["result"]["message_id"]}

    @BridgeAdapter.resilient_request
    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch unread updates in long-polling mode."""
        if not self.is_connected or self.webhook_url:
            return []

        res = await self.client.post(
            f"{self.api_url}{self.bot_token}/getUpdates",
            json={"limit": limit, "offset": self._update_offset, "timeout": 30},
            timeout=35.0
        )
        data = res.json()
        if not data.get("ok"): return []

        messages = []
        for item in data.get("result", []):
            self._update_offset = item["update_id"] + 1
            msg = item.get("message") or item.get("edited_message")
            if msg:
                parsed = self._parse_inbound(msg)
                messages.append(parsed)
                self._track_account(msg)
        
        if messages:
            self.last_activity = datetime.now(timezone.utc).isoformat()  # type: ignore
        return messages

    async def _poll_loop(self):
        """Background loop for Telegram long-polling."""
        while self.is_connected and not self.webhook_url:
            try:
                res = await self.client.post(
                    f"{self.api_url}{self.bot_token}/getUpdates",
                    json={
                        "offset": self._update_offset,
                        "timeout": 30,
                        "allowed_updates": ["message", "callback_query"]
                    },
                    timeout=35.0
                )
                data = res.json()
                if data.get("ok"):
                    for update in data["result"]:
                        self._update_offset = update["update_id"] + 1
                        await self._handle_update(update)
            except Exception as e:
                self.logger.error(f"Telegram poll error: {e}")
                await asyncio.sleep(5)

    async def validate_integrity(self) -> bool:
        """Verify the connection by fetching bot details."""
        if not self.bot_token: return False
        try:
            res = await self.client.get(f"{self.api_url}{self.bot_token}/getMe")
            return res.json().get("ok", False)
        except Exception as e:
            self.last_error = f"Integrity check failed: {e}"
            return False

    async def disconnect(self):
        """Clean up webhook and shutdown."""
        if self.is_connected and self.webhook_url:
            try:
                await self.client.get(f"{self.api_url}{self.bot_token}/deleteWebhook")
            except Exception as e:
                self.logger.warning(f"Telegram: Webhook delete failed on disconnect: {e}")
        await super().disconnect()  # type: ignore

    def _parse_inbound(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        """Inbound message parsing: text, photo, document, voice, sticker."""
        parsed: Dict[str, Any] = {
            "id": str(msg.get("message_id")),
            "from_id": str(msg.get("from", {}).get("id", "")),
            "chat_id": str(msg.get("chat", {}).get("id", "")),
            "timestamp": datetime.fromtimestamp(msg.get("date", 0), tz=timezone.utc).isoformat(),
            "protocol": "TELEGRAM",
            "type": "text",
            "body": ""
        }

        if "text" in msg:
            parsed["body"] = msg["text"]
            parsed["type"] = "text"
        elif "photo" in msg:
            parsed["type"] = "photo"
            parsed["body"] = msg.get("caption", "[Photo]")
            parsed["file_id"] = msg["photo"][-1]["file_id"]
        elif "document" in msg:
            parsed["type"] = "document"
            parsed["body"] = msg.get("caption", f"[Document: {msg['document'].get('file_name', 'unnamed')}]")
            parsed["file_id"] = msg["document"]["file_id"]
        elif "voice" in msg:
            parsed["type"] = "voice"
            parsed["body"] = "[Voice Message]"
            parsed["file_id"] = msg["voice"]["file_id"]
        elif "sticker" in msg:
            parsed["type"] = "sticker"
            parsed["body"] = msg["sticker"].get("emoji", "[Sticker]")
            parsed["file_id"] = msg["sticker"]["file_id"]
        
        return parsed

    def _track_account(self, msg: Dict[str, Any]):
        """Track connected accounts with last-seen timestamps."""
        chat_id = str(msg.get("chat", {}).get("id", ""))
        sender = msg.get("from", {})
        self.accounts[chat_id] = {
            "chat_id": chat_id,
            "username": sender.get("username"),
            "first_name": sender.get("first_name"),
            "last_name": sender.get("last_name"),
            "last_seen": datetime.now(timezone.utc).isoformat()
        }
        self.last_activity = datetime.now(timezone.utc).isoformat()  # type: ignore
        self._save_accounts()

    async def _handle_update(self, update: Dict[str, Any]):
        """Unified entry point for incoming updates."""
        msg = update.get("message") or update.get("edited_message")
        if msg:
            parsed = self._parse_inbound(msg)
            self._track_account(msg)
            await self._dispatch_inbound(parsed)
            
        cbq = update.get("callback_query")
        if cbq:
            # Handle callback button clicks
            text = cbq.get("data", "")
            msg = cbq.get("message", {})
            parsed = {
                "id": cbq["id"],
                "from_id": str(cbq["from"]["id"]),
                "chat_id": str(msg.get("chat", {}).get("id")),
                "body": text,
                "type": "callback",
                "protocol": "TELEGRAM"
            }
            await self._dispatch_inbound(parsed)

    async def process_webhook(self, update: Dict[str, Any]):
        """Entry point for incoming webhook updates."""
        await self._handle_update(update)

    def get_health(self) -> Dict[str, Any]:
        """Health reporting (standardized + telegram specific)."""
        health = super().get_health()
        health.update({
            "bot_username": self.bot_username,
            "account_count": len(self.accounts),
            "webhook_active": bool(self.webhook_url),
        })
        return health

    def _load_accounts(self):
        path = os.path.join(self.vault_path, "accounts.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.accounts = json.load(f)
            except Exception as e:
                self.logger.error(f"Telegram: Failed to load accounts: {e}")
                self.accounts = {}

    def _save_accounts(self):
        path = os.path.join(self.vault_path, "accounts.json")
        try:
            with open(path, "w") as f:
                json.dump(self.accounts, f)
        except Exception as e:
            self.logger.error(f"Telegram: Failed to save accounts: {e}")

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
