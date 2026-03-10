from typing import Dict, Any, List, Optional
from .base import BridgeAdapter
import logging
import asyncio

try:
    import itchat
    from itchat.content import TEXT, PICTURE, MAP, CARD, SHARING, RECORDING, ATTACHMENT, VIDEO, FRIENDS
except ImportError:
    itchat = None

class WeChatBridge(BridgeAdapter):
    """
    Sovereign WeChat Bridge using itchat-uos for Unified Operating System support.
    Implements QRSyncModal flows.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.instance = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        if not itchat:
            self.logger.error("itchat-uos library not installed.")
            return False
            
        # For WeChat, we usually need the QR scan first.
        # This method might be called after a successful QR init.
        self.is_connected = True
        return True

    async def init_qr(self) -> Dict[str, Any]:
        """Provides the QR code and UUID during setup for QRSyncModal."""
        if not itchat:
            return {"status": "error", "error": "itchat-uos missing"}
            
        try:
            # We use itchat's get_QRuuid and get_QR to provide the URL
            uuid = itchat.get_QRuuid()
            if not uuid:
                return {"status": "error", "error": "Failed to get QR UUID"}
                
            qr_url = f"https://login.weixin.qq.com/qrcode/{uuid}"
            self.logger.info(f"WeChat QR Generated: {uuid}")
            if self.on_event:
                asyncio.create_task(self.on_event("bridge.status", {
                    "bridge_id": self.bridge_id,
                    "status": "QR_READY",
                    "qr_url": qr_url,
                    "uuid": uuid
                }))
            return {"qr_url": qr_url, "uuid": uuid}
        except Exception as e:
            self.logger.error(f"WeChat QR Init failed: {e}")
            return {"status": "error", "error": str(e)}

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not itchat:
            return {"status": "failed", "error": "Not connected"}
            
        try:
            res = itchat.send(content, toUserName=recipient)
            if res and res.get('BaseResponse', {}).get('Ret') == 0:
                return {"status": "success"}
            return {"status": "failed", "error": str(res)}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        # itchat is usually event-driven via @itchat.msg_register
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        health = super().get_health()
        if self.is_connected:
            health.update({
                "platform": "itchat-uos (WeChat)",
                "status_message": "Operational"
            })
        return health
