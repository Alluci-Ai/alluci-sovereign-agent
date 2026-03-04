"""
Production WhatsApp Adapter for the Polytope Sovereign OS.

Supports two modes:
1. Meta Graph API (Business): access_token + phone_number_id
2. Webhook inbound parsing for receiving messages

Provides:
- Connection validation against Meta Graph API
- Webhook inbound queue for received messages
- Health reporting for channel dashboard
- Per-account tracking

Reference: OpenClaw Section 2.1
"""

import httpx
import os
import json
from collections import deque
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter


class WhatsAppBridge(BridgeAdapter):
    """
    WhatsApp Business API adapter with webhook support,
    inbound queue, and health reporting.
    """

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.api_url = "https://graph.facebook.com/v18.0"
        self.access_token: str = ""
        self.phone_number_id: str = ""
        self.verify_token: str = ""  # for webhook verification
        self.last_activity: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self.accounts: Dict[str, Dict[str, Any]] = {}  # phone -> info
        self._inbound_queue: deque = deque(maxlen=1000)
        self.enabled: bool = True
        self.connection_state: str = "IDLE"  # IDLE, CONNECTED, DISCONNECTED, ERROR

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to WhatsApp Business API.
        Expected credentials: {"access_token": "EAA...", "phone_number_id": "123...", "verify_token": "..."}
        """
        self.access_token = credentials.get("access_token", "")
        self.phone_number_id = credentials.get("phone_number_id", "")
        self.verify_token = credentials.get("verify_token", "")

        if not self.access_token or not self.phone_number_id:
            self.connection_state = "ERROR"
            self.last_error = "Missing access_token or phone_number_id"
            return False

        try:
            async with httpx.AsyncClient() as client:
                # Verify token by checking the phone number
                res = await client.get(
                    f"{self.api_url}/{self.phone_number_id}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                data = res.json()

                if "id" in data:
                    self.is_connected = True
                    self.connection_state = "CONNECTED"
                    self.last_activity = datetime.now(timezone.utc)
                    display_name = data.get("verified_name", data.get("display_phone_number", "Unknown"))
                    self.logger.info(f"WhatsApp Connected. Phone: {display_name}")
                    return True
                else:
                    self.connection_state = "ERROR"
                    self.last_error = data.get("error", {}).get("message", "Verification failed")
                    self.logger.warning(f"WhatsApp connection failed: {self.last_error}")
                    return False

        except Exception as e:
            self.connection_state = "ERROR"
            self.last_error = str(e)
            self.logger.error(f"WhatsApp connection failed: {e}")
            return False

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Send a text message via WhatsApp Business API."""
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}/{self.phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json={
                        "messaging_product": "whatsapp",
                        "to": recipient,
                        "type": "text",
                        "text": {"body": content},
                    }
                )
                data = res.json()
                status = "success" if "messages" in data else "failed"

                if status == "success":
                    self.last_activity = datetime.now(timezone.utc)

                self._persist_to_vault("sent", {
                    "to": recipient,
                    "content": content,
                    "status": status,
                    "timestamp": timestamp,
                    "meta_id": data.get("messages", [{}])[0].get("id") if status == "success" else None,
                    "error": data.get("error"),
                })

                return {"status": status, "response": data}
        except Exception as e:
            self.last_error = str(e)
            self.logger.error(f"WhatsApp send_message failed: {e}")
            self._persist_to_vault("sent", {
                "to": recipient, "content": content,
                "status": "exception", "timestamp": timestamp, "error": str(e),
            })
            return {"status": "failed", "error": f"Bridge communication error: {type(e).__name__}"}

    async def send_template(self, recipient: str, template_name: str, language: str = "en_US",
                            components: list = None) -> Dict[str, Any]:
        """Send a pre-approved template message."""
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        payload: Dict[str, Any] = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
            },
        }
        if components:
            payload["template"]["components"] = components

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}/{self.phone_number_id}/messages",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    json=payload,
                )
                data = res.json()
                return {"status": "success" if "messages" in data else "failed", "response": data}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return queued inbound messages (from webhook processing)."""
        messages = []
        while self._inbound_queue and len(messages) < limit:
            messages.append(self._inbound_queue.popleft())
        return messages

    def process_webhook_event(self, body: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process an incoming webhook payload from Meta.
        Parses messages and adds them to the inbound queue.
        """
        parsed_messages = []

        entries = body.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                # Map contacts
                contact_map = {}
                for c in contacts:
                    contact_map[c.get("wa_id", "")] = {
                        "name": c.get("profile", {}).get("name", ""),
                        "wa_id": c.get("wa_id", ""),
                    }

                for msg in messages:
                    parsed = self._parse_inbound(msg, contact_map)
                    parsed_messages.append(parsed)
                    self._inbound_queue.append(parsed)

                    # Track account
                    phone = msg.get("from", "")
                    self.accounts[phone] = {
                        "phone": phone,
                        "name": contact_map.get(phone, {}).get("name"),
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                    }

                    self._persist_to_vault("inbox", parsed)

        if parsed_messages:
            self.last_activity = datetime.now(timezone.utc)

        return parsed_messages

    def _parse_inbound(self, msg: Dict[str, Any], contact_map: Dict = None) -> Dict[str, Any]:
        """Parse a WhatsApp webhook message into normalized format."""
        contact_map = contact_map or {}
        phone = msg.get("from", "")

        parsed: Dict[str, Any] = {
            "id": msg.get("id", ""),
            "from": phone,
            "from_name": contact_map.get(phone, {}).get("name"),
            "timestamp": msg.get("timestamp", ""),
            "protocol": "WHATSAPP",
            "type": msg.get("type", "text"),
            "body": "",
        }

        msg_type = msg.get("type", "text")
        if msg_type == "text":
            parsed["body"] = msg.get("text", {}).get("body", "")
        elif msg_type == "image":
            parsed["body"] = msg.get("image", {}).get("caption", "")
            parsed["media_id"] = msg.get("image", {}).get("id")
            parsed["mime_type"] = msg.get("image", {}).get("mime_type")
        elif msg_type == "document":
            parsed["body"] = msg.get("document", {}).get("caption", "")
            parsed["media_id"] = msg.get("document", {}).get("id")
            parsed["file_name"] = msg.get("document", {}).get("filename")
        elif msg_type == "audio":
            parsed["media_id"] = msg.get("audio", {}).get("id")
            parsed["mime_type"] = msg.get("audio", {}).get("mime_type")
        elif msg_type == "location":
            loc = msg.get("location", {})
            parsed["latitude"] = loc.get("latitude")
            parsed["longitude"] = loc.get("longitude")
            parsed["body"] = loc.get("name", f"{loc.get('latitude')},{loc.get('longitude')}")
        elif msg_type == "reaction":
            parsed["emoji"] = msg.get("reaction", {}).get("emoji")
            parsed["reacted_message_id"] = msg.get("reaction", {}).get("message_id")

        return parsed

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Handle Meta webhook verification (GET request)."""
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        """Return health report for channel dashboard."""
        return {
            "channel": "whatsapp",
            "connected": self.is_connected,
            "enabled": self.enabled,
            "connection_state": self.connection_state,
            "phone_number_id": self.phone_number_id[:6] + "****" if self.phone_number_id else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "last_error": self.last_error,
            "account_count": len(self.accounts),
            "inbound_queue_size": len(self._inbound_queue),
            "accounts": list(self.accounts.values()),
        }

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
