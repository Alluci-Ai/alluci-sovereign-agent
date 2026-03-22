"""
Sovereign WeChat Bridge — WeCom (Enterprise WeChat / 企业微信) Corporate API.

This bridge uses the officially supported WeCom API, not personal WeChat
(itchat/itchat-uos is deprecated and blocked outside China).

WeCom Setup:
  1. Register at work.weixin.qq.com
  2. Create an Application under "应用管理"
  3. Note: Corp ID (企业ID), Agent ID (AgentId), Agent Secret (Secret)
  4. Set callback URL for message receiving
  5. Enable message encryption in the app settings

Message Receiving:
  WeCom uses XML-encoded messages with optional AES encryption.
  Inbound verification uses:
    - Signature: SHA1(token + timestamp + nonce + echostr)
    - Encryption: AES-256-CBC with EncodingAESKey

OAuth for Web:
  WeCom web OAuth for user identity scanning.
"""

import asyncio
import hashlib
import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx

from .base import BridgeAdapter, UnofficialBridgeMixin

WECOM_API = "https://qyapi.weixin.qq.com/cgi-bin"


class WeChatBridge(BridgeAdapter, UnofficialBridgeMixin):
    """
    Production WeChat / WeCom Corporate Bridge.
    Uses WeCom (企业微信) Application API for enterprise messaging.
    """

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self._corp_id:      Optional[str] = os.getenv("WECOM_CORP_ID")
        self._corp_secret:  Optional[str] = os.getenv("WECOM_CORP_SECRET")
        self._agent_id:     Optional[str] = os.getenv("WECOM_AGENT_ID")
        self._token:        Optional[str] = os.getenv("WECOM_TOKEN")
        self._aes_key:      Optional[str] = os.getenv("WECOM_ENCODING_AES_KEY")
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # ── Connection ────────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect using WeCom Corp credentials.
        """
        self.validate_official_gate("WECHAT/WECOM")
        self._corp_id     = credentials.get("corp_id")     or self._corp_id
        self._corp_secret = credentials.get("corp_secret") or self._corp_secret
        self._agent_id    = credentials.get("agent_id")    or self._agent_id
        self._token       = credentials.get("token")       or self._token
        self._aes_key     = credentials.get("encoding_aes_key") or self._aes_key

        if not (self._corp_id and self._corp_secret and self._agent_id):
            self.last_error = "corp_id, corp_secret, and agent_id required."
            return False

        success = await self._fetch_access_token()
        if success:
            self.is_connected = True
            self.logger.info(f"[WECHAT/WECOM] Connected — Corp: {self._corp_id}")
        return success

    # ── Access Token ──────────────────────────────────────────────────────────

    async def _fetch_access_token(self) -> bool:
        """Fetch WeCom access token (valid 7200s, cached with 60s safety margin)."""
        if self._access_token and time.time() < self._token_expires_at - 60:
            return True

        try:
            resp = await self.client.get(
                f"{WECOM_API}/gettoken",
                params={
                    "corpid":     self._corp_id,
                    "corpsecret": self._corp_secret,
                },
            )
            data = resp.json()
            if data.get("errcode") == 0:
                self._access_token     = data["access_token"]
                self._token_expires_at = time.time() + data.get("expires_in", 7200)
                self.logger.debug("[WECHAT/WECOM] Access token refreshed.")
                return True
            self.last_error = f"Token error {data.get('errcode')}: {data.get('errmsg')}"
            self.logger.error(f"[WECHAT/WECOM] {self.last_error}")
            return False
        except Exception as e:
            self.last_error = str(e)
            return False

    async def _ensure_token(self) -> bool:
        return await self._fetch_access_token()

    # ── Webhook Verification ──────────────────────────────────────────────────

    def verify_callback(
        self, msg_signature: str, timestamp: str, nonce: str, echostr: str = ""
    ) -> Optional[str]:
        """
        Verify WeCom GET callback request (used during webhook URL configuration).
        Returns echostr if valid, None otherwise.
        WeCom signature = SHA1(sort([token, timestamp, nonce]).join(''))
        """
        if not self._token:
            self.logger.error("[WECHAT/WECOM] WECOM_TOKEN not configured.")
            return None

        parts = sorted([self._token, timestamp, nonce])
        computed = hashlib.sha1("".join(parts).encode("utf-8")).hexdigest()

        if computed == msg_signature:
            return echostr
        self.logger.warning("[WECHAT/WECOM] Callback signature mismatch.")
        return None

    def _decrypt_message(self, encrypted: str) -> Optional[str]:
        """
        Decrypt AES-256-CBC encrypted WeCom message body.
        Returns decrypted XML string.
        """
        if not self._aes_key:
            return None
        try:
            import base64
            from Crypto.Cipher import AES
            # WeCom uses base64(key + "=") — pad to 44 chars
            key = base64.b64decode(self._aes_key + "=")
            iv  = key[:16]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(base64.b64decode(encrypted))
            # Remove PKCS7 padding
            pad = decrypted[-1]
            decrypted = decrypted[:-pad]
            # First 20 bytes: random + 4-byte length prefix + content
            content_length = int.from_bytes(decrypted[16:20], "big")
            return decrypted[20: 20 + content_length].decode("utf-8")
        except Exception as e:
            self.logger.error(f"[WECHAT/WECOM] Decryption failed: {e}")
            return None

    # ── QR Auth for Web OAuth ─────────────────────────────────────────────────

    async def init_qr(self) -> Dict[str, Any]:
        """
        Generate WeCom web OAuth QR URL for user identity verification.
        Used for connecting personal WeChat users to WeCom via scan.
        """
        if not (self._corp_id and self._agent_id):
            return {"status": "error", "error": "Corp credentials not configured."}

        from ..config import settings
        daemon_url  = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
        redirect_uri = urllib.parse.quote(f"{daemon_url}/api/oauth/wechat/callback")

        qr_url = (
            f"https://open.work.weixin.qq.com/wwopen/sso/qrConnect"
            f"?appid={self._corp_id}"
            f"&agentid={self._agent_id}"
            f"&redirect_uri={redirect_uri}"
            f"&state=wechat_login"
        )

        if self.on_event:
            asyncio.create_task(self.on_event("bridge.status", {
                "bridge_id": self.bridge_id,
                "status":    "QR_READY",
                "qr_url":    qr_url,
            }))

        return {"status": "ok", "qr_url": qr_url, "corp_id": self._corp_id}

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Send a WeCom application message.
        recipient: WeCom user ID (touser), department ID (toparty), or tag (totag)
        kwargs:
            msg_type: "text" (default) | "markdown" | "textcard" | "image"
            toparty: department IDs (str, pipe-separated)
            totag: tag IDs (str, pipe-separated)
            title: for textcard
            url: for textcard
        """
        if not await self._ensure_token():
            return {"status": "failed", "error": "Token unavailable"}

        msg_type = kwargs.get("msg_type", "text")

        if msg_type == "markdown":
            message_body = {"content": content}
        elif msg_type == "textcard":
            message_body = {
                "title":       kwargs.get("title", "Alluci"),
                "description": content,
                "url":         kwargs.get("url", ""),
                "btntxt":      kwargs.get("btntxt", "View"),
            }
        else:
            message_body = {"content": content}

        payload = {
            "touser":   recipient if not kwargs.get("toparty") else "",
            "toparty":  kwargs.get("toparty", ""),
            "totag":    kwargs.get("totag", ""),
            "msgtype":  msg_type,
            "agentid":  int(self._agent_id),
            msg_type:   message_body,
            "safe":     0,
        }

        @BridgeAdapter.resilient_request
        async def _post():
            return await self.client.post(
                f"{WECOM_API}/message/send",
                params={"access_token": self._access_token},
                json=payload,
            )

        try:
            resp = await _post()
            data = resp.json()
            if data.get("errcode") == 0:
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "msgid": data.get("msgid")}
            self.last_error = f"Error {data.get('errcode')}: {data.get('errmsg')}"
            return {"status": "failed", "error": self.last_error}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    # ── Inbound Webhook ───────────────────────────────────────────────────────

    async def process_webhook(self, payload: Dict[str, Any]) -> None:
        """
        Parse WeCom inbound message POST.
        payload must contain "xml" key with parsed XML dict,
        or "raw_xml" key with raw XML string.
        """
        try:
            raw_xml = payload.get("raw_xml") or ""
            if not raw_xml:
                return

            root = ET.fromstring(raw_xml)

            # Handle encrypted messages
            encrypt_node = root.find("Encrypt")
            if encrypt_node is not None and self._aes_key:
                decrypted = self._decrypt_message(encrypt_node.text or "")
                if decrypted:
                    root = ET.fromstring(decrypted)

            msg_type = self._xml_text(root, "MsgType")
            from_user = self._xml_text(root, "FromUserName")
            body = ""
            media: Optional[Dict] = None

            if msg_type == "text":
                body = self._xml_text(root, "Content")
            elif msg_type in ("image", "voice", "video", "shortvideo"):
                media = {
                    "type":     msg_type,
                    "media_id": self._xml_text(root, "MediaId"),
                    "format":   self._xml_text(root, "Format"),
                }
                body = f"[WeCom {msg_type}]"
            elif msg_type == "location":
                body = (
                    f"[Location] lat={self._xml_text(root, 'Location_X')} "
                    f"lng={self._xml_text(root, 'Location_Y')}"
                )
            elif msg_type == "event":
                event = self._xml_text(root, "Event")
                body = f"[Event: {event}]"

            await self._dispatch_inbound({
                "id":         self._xml_text(root, "MsgId"),
                "from":       from_user,
                "body":       body,
                "media":      media,
                "type":       msg_type,
                "protocol":   "WECOM",
                "timestamp":  self._xml_text(root, "CreateTime"),
                "account_id": self._agent_id,
            })
        except Exception as e:
            self.logger.error(f"[WECHAT/WECOM] Webhook parse error: {e}", exc_info=True)

    @staticmethod
    def _xml_text(root: ET.Element, tag: str) -> str:
        node = root.find(tag)
        return (node.text or "").strip() if node is not None else ""

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []  # Push via webhooks

    async def validate_integrity(self) -> bool:
        return await self._ensure_token()

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "corp_id":    self._corp_id,
            "agent_id":   self._agent_id,
            "token_valid": bool(self._access_token and time.time() < self._token_expires_at),
        })
        return h
