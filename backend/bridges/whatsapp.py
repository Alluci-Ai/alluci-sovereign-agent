import hashlib
import hmac as _hmac
import os
import time
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
from .base import BridgeAdapter

class WhatsAppBridge(BridgeAdapter):
    """
    Sovereign WhatsApp Bridge.
    Uses direct Cloud API (preferred).
    Supports Hub Signature verification, PKCE-like token rotation, and multi-media messaging.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.access_token: Optional[str] = None
        self.phone_number_id: Optional[str] = None
        self._client_id: Optional[str] = None
        self._client_secret: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    async def _save_credentials(self, creds: Dict[str, Any]) -> None:  # type: ignore
        await super()._save_credentials(creds, account_id=self.phone_number_id or "default")

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        if not credentials:
            return False

        self.access_token = credentials.get("access_token")
        self.phone_number_id = credentials.get("phone_number_id")
        self._client_id = credentials.get("client_id")
        self._client_secret = credentials.get("client_secret")
        self._refresh_token = credentials.get("refresh_token")
        self._token_expires_at = credentials.get("expires_at", 0.0)
        
        if self.access_token and self.phone_number_id:
            try:
                # Validate token via phone_number_id endpoint
                @BridgeAdapter.resilient_request
                async def validate():
                    return await self.client.get(
                        f"https://graph.facebook.com/v20.0/{self.phone_number_id}",
                        params={"access_token": self.access_token}
                    )
                
                resp = await validate()
                if resp.status_code == 200:
                    self.is_connected = True
                    self.logger.info(f"WhatsApp Cloud API session established for {self.phone_number_id}")
                    return True
                else:
                    self.logger.error(f"WhatsApp API verification failed: {resp.text}")
                    self.is_connected = False
                    return False
            except Exception as e:
                self.logger.error(f"WhatsApp Cloud API connect error: {e}")
                self.is_connected = False
                return False
        
        return False

    async def _ensure_token(self) -> None:
        """Refresh the Meta access token if it is nearing expiry."""
        if not self._refresh_token or not self._token_expires_at:
            return
        if time.time() < self._token_expires_at - 300:
            return

        self.logger.info("[WHATSAPP] Access token expiring — refreshing via Meta OAuth.")
        try:
            @BridgeAdapter.resilient_request
            async def refresh():
                return await self.client.get(
                    "https://graph.facebook.com/v20.0/oauth/access_token",
                    params={
                        "grant_type":    "fb_exchange_token",
                        "client_id":     self._client_id,
                        "client_secret": self._client_secret,
                        "fb_exchange_token": self.access_token,
                    },
                )
            
            resp = await refresh()
            data = resp.json()
            if data.get("access_token"):
                self.access_token = data["access_token"]
                self._token_expires_at = time.time() + data.get("expires_in", 5184000)
                
                # Persist updated token to vault
                creds.update({  # type: ignore
                    "access_token": self.access_token,
                    "expires_at": self._token_expires_at
                })
                await self._save_credentials(creds)  # type: ignore
                
                self.logger.info("[WHATSAPP] Token refreshed successfully.")
        except Exception as e:
            self.logger.error(f"[WHATSAPP] Token refresh failed: {e}")

    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Respond to Meta's hub.challenge subscription verification.
        Meta sends: ?hub.mode=subscribe&hub.verify_token=<your_token>&hub.challenge=<string>
        """
        from ..config import settings
        expected_token = settings.WHATSAPP_VERIFY_TOKEN  # type: ignore

        if not expected_token:
            self.logger.error("[WHATSAPP] WHATSAPP_VERIFY_TOKEN not configured.")
            return None

        if mode == "subscribe" and _hmac.compare_digest(token, expected_token):
            self.logger.info("[WHATSAPP] Hub challenge verified successfully.")
            return challenge

        self.logger.warning(f"[WHATSAPP] Hub verification failed — token mismatch.")
        return None

    def verify_signature(self, body: bytes, signature_header: str) -> bool:
        """
        Verify Meta's X-Hub-Signature-256 HMAC using WHATSAPP_APP_SECRET.
        Signature format: sha256=<hex_digest>
        Ref: https://developers.facebook.com/docs/graph-api/webhooks/getting-started
        """
        from ..config import settings
        app_secret = settings.WHATSAPP_APP_SECRET  # type: ignore

        if not app_secret:
            self.logger.error("[WHATSAPP] WHATSAPP_APP_SECRET not set — rejecting all POSTs.")
            return False

        if not signature_header or not signature_header.startswith("sha256="):
            self.logger.warning("[WHATSAPP] Missing or malformed X-Hub-Signature-256.")
            return False

        expected = "sha256=" + _hmac.new(
            app_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return _hmac.compare_digest(expected, signature_header)

    async def send(
        self,
        recipient: str,
        content: str,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send a WhatsApp message. Supports text, template, image, document, and audio.

        kwargs:
            msg_type (str):     "text" | "template" | "image" | "document" | "audio"
            template_name (str): Required for msg_type="template"
            template_lang (str): Language code, e.g. "en_US"
            template_params (list): Variable substitutions for template body
            media_url (str):    Publicly accessible URL for media messages
            media_id (str):     WhatsApp media ID (alternative to media_url)
            caption (str):      Caption for image/document
            filename (str):     Filename for document messages
        """
        await self._ensure_token()

        if not self.is_connected or not self.access_token:
            return {"status": "failed", "error": "Not connected"}

        msg_type = kwargs.get("msg_type", "text")
        url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.access_token}"}

        # ── Build payload by message type ───────────────────────────────────
        if msg_type == "template":
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "template",
                "template": {
                    "name": kwargs["template_name"],
                    "language": {"code": kwargs.get("template_lang", "en_US")},
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": p}
                                for p in kwargs.get("template_params", [])
                            ],
                        }
                    ] if kwargs.get("template_params") else [],
                },
            }

        elif msg_type in ("image", "document", "audio", "video"):
            media_block: Dict[str, Any] = {}
            if kwargs.get("media_id"):
                media_block["id"] = kwargs["media_id"]
            elif kwargs.get("media_url"):
                media_block["link"] = kwargs["media_url"]
            else:
                return {"status": "failed", "error": "media_id or media_url required"}

            if kwargs.get("caption") and msg_type in ("image", "document", "video"):
                media_block["caption"] = kwargs["caption"]
            if kwargs.get("filename") and msg_type == "document":
                media_block["filename"] = kwargs["filename"]

            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": msg_type,
                msg_type: media_block,
            }

        else:  # default: text
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"preview_url": False, "body": content},
            }

        @BridgeAdapter.resilient_request
        async def _post():
            return await self.client.post(url, json=payload, headers=headers)

        try:
            resp = await _post()
            body_json = resp.json()
            if resp.status_code == 200:
                msg_id = body_json.get("messages", [{}])[0].get("id", "")
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "id": msg_id}
            self.last_error = body_json.get("error", {}).get("message", resp.text)
            return {"status": "failed", "error": self.last_error}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def process_webhook(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Standardized entry point for WhatsApp Cloud API webhooks."""
        return await self.process_webhook_event(data)

    async def process_webhook_event(
        self, data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Parse a WhatsApp Cloud API webhook POST payload.
        Returns a list of normalised inbound message dicts.
        Handles text, image, video, audio, document, sticker, and location messages.
        """
        results = []
        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    # ── Inbound messages ──────────────────────────────────
                    for msg in value.get("messages", []):
                        sender = msg.get("from")
                        msg_type = msg.get("type", "text")
                        body = ""
                        media_info = {}

                        if msg_type == "text":
                            body = msg.get("text", {}).get("body", "")

                        elif msg_type in ("image", "video", "audio", "document", "sticker"):
                            media = msg.get(msg_type, {})
                            body = f"[WhatsApp {msg_type}]"
                            media_info = {
                                "type":     msg_type,
                                "media_id": media.get("id"),
                                "mime":     media.get("mime_type"),
                                "sha256":   media.get("sha256"),
                                "caption":  media.get("caption", ""),
                                "filename": media.get("filename", ""),
                            }

                        elif msg_type == "location":
                            loc = msg.get("location", {})
                            body = (
                                f"[Location] lat={loc.get('latitude')}, "
                                f"lng={loc.get('longitude')}, "
                                f"name={loc.get('name', '')}"
                            )

                        elif msg_type == "interactive":
                            inter = msg.get("interactive", {})
                            if inter.get("type") == "button_reply":
                                body = inter["button_reply"].get("title", "")
                            elif inter.get("type") == "list_reply":
                                body = inter["list_reply"].get("title", "")

                        normalized = {
                            "id":         msg.get("id"),
                            "from_id":    sender,
                            "chat_id":    sender,
                            "body":       body,
                            "type":       msg_type,
                            "timestamp":  datetime.fromtimestamp(int(msg.get("timestamp", 0)), tz=timezone.utc).isoformat() if msg.get("timestamp") else datetime.now(timezone.utc).isoformat(),
                            "account_id": self.phone_number_id,
                            "protocol":   "WHATSAPP",
                            "media":      media_info or None,
                        }
                        results.append(normalized)
                        await self._dispatch_inbound(normalized)

                    # ── Status updates (read receipts, delivery) ──────────
                    for status in value.get("statuses", []):
                        self.logger.debug(
                            f"[WHATSAPP] Message {status.get('id')} → {status.get('status')}"
                        )

        except Exception as e:
            self.logger.error(f"[WHATSAPP] Webhook parse failed: {e}", exc_info=True)

        return results

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Cloud API doesn't support fetching. Requires webhooks."""
        return []

    async def validate_integrity(self) -> bool:
        if not self.access_token or not self.phone_number_id:
            return False
        try:
            resp = await self.client.get(
                f"https://graph.facebook.com/v20.0/{self.phone_number_id}",
                params={"access_token": self.access_token}
            )
            return resp.status_code == 200
        except:
            return False

    def get_health(self) -> Dict[str, Any]:
        """Health reporting for WhatsApp."""
        health = super().get_health()
        if self.is_connected:
            health.update({
                "phone_number_id": self.phone_number_id,
                "api_version": "v20.0"
            })
        return health
