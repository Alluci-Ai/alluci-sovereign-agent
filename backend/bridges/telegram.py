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
        self.enabled: bool = True
        self._load_accounts()

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to Telegram via Bot Token.
        Validates the token and optionally sets up a webhook.
        """
        self.bot_token = credentials.get("bot_token", "")
        self.webhook_url = credentials.get("webhook_url")
        self.last_error = None

        try:
            async with httpx.AsyncClient() as client:
                # 1. Bot Token Validation (OpenClaw §2.2)
                res = await client.get(f"{self.api_url}{self.bot_token}/getMe")
                data = res.json()
                if not data.get("ok"):
                    self.last_error = data.get("description", "Token validation failed")
                    self.logger.error(f"Telegram Auth Failed: {self.last_error}")
                    return False

                self.is_connected = True
                self.bot_username = data["result"].get("username", "unknown")
                self.last_activity = datetime.now(timezone.utc)
                self.logger.info(f"Telegram Connected. Bot: @{self.bot_username}")

                # 2. Auto-register Webhook (OpenClaw §2.2)
                if self.webhook_url:
                    await self._register_webhook(client)
                else:
                    # Clean up old webhooks if we're now in polling mode
                    try:
                        await client.get(f"{self.api_url}{self.bot_token}/deleteWebhook")
                        self.logger.info("Telegram: Webhook cleared, entering long-polling mode.")
                    except: pass

                return True
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
        """Transmit text message via Telegram."""
        return await self.send(recipient, content)

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Sovereign send method (Telegram)."""
        if not self.is_connected or not self.bot_token:
            return {"ok": False, "error": "Bot not connected"}
        
        self.last_activity = datetime.now(timezone.utc)
        url = f"{self.api_url}{self.bot_token}/sendMessage"
        payload = {
            "chat_id": recipient,
            "text": content,
            "parse_mode": "Markdown",
        }
        
        # Merge extra kwargs (OpenClaw §2.3)
        payload.update(kwargs)

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload)
                res = resp.json()
                if not res.get("ok"):
                    self.last_error = f"API Error: {res.get('description')}"
                    return {"status": "failed", "error": self.last_error}
                
                return {"status": "success", "id": res["result"]["message_id"]}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch unread updates in long-polling mode."""
        if not self.is_connected or self.webhook_url:
            return []

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                res = await client.post(
                    f"{self.api_url}{self.bot_token}/getUpdates",
                    json={"limit": limit, "offset": self._update_offset, "timeout": 30}
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
                    self.last_activity = datetime.now(timezone.utc)
                return messages
        except Exception as e:
            self.last_error = str(e)
            return []

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
        self.last_activity = datetime.now(timezone.utc)
        self._save_accounts()

    def process_webhook(self, update: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Entry point for incoming webhook updates."""
        msg = update.get("message") or update.get("edited_message")
        if not msg: return None
        
        parsed = self._parse_inbound(msg)
        self._track_account(msg)
        return parsed

    async def validate_integrity(self) -> bool:
        """Verify the connection by fetching bot details."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.api_url}{self.bot_token}/getMe")
                return res.json().get("ok", False)
        except: return False

    async def disconnect(self):
        """Clean up webhook and shutdown."""
        if self.is_connected and self.webhook_url:
            async with httpx.AsyncClient() as client:
                try:
                    await client.get(f"{self.api_url}{self.bot_token}/deleteWebhook")
                except: pass
        await super().disconnect()

    def get_health(self) -> Dict[str, Any]:
        """Health reporting (connection state, last activity, error)."""
        return {
            "channel": "telegram",
            "connected": self.is_connected,
            "bot_username": self.bot_username,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "last_error": self.last_error,
            "account_count": len(self.accounts),
            "webhook_active": bool(self.webhook_url),
            "accounts": list(self.accounts.values())
        }

    def _load_accounts(self):
        path = os.path.join(self.vault_path, "accounts.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    self.accounts = json.load(f)
            except: self.accounts = {}

    def _save_accounts(self):
        path = os.path.join(self.vault_path, "accounts.json")
        try:
            with open(path, "w") as f:
                json.dump(self.accounts, f)
        except: pass

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
