from typing import Dict, Any, List
import asyncio
import httpx
import json
from .base import BridgeAdapter

class WhatsAppBridge(BridgeAdapter):
    """
    Sovereign WhatsApp Bridge.
    Uses direct Cloud API (preferred).
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.access_token = None
        self.phone_number_id = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.access_token = credentials.get("access_token")
        self.phone_number_id = credentials.get("phone_number_id")
        
        if self.access_token and self.phone_number_id:
            try:
                # Validate token via phone_number_id endpoint
                async with httpx.AsyncClient() as client:
                    resp = await client.get(
                        f"https://graph.facebook.com/v20.0/{self.phone_number_id}",
                        params={"access_token": self.access_token}
                    )
                    if resp.status_code == 200:
                        self.is_connected = True
                        self.logger.info("WhatsApp Cloud API session established.")
                        return True
                    else:
                        self.logger.error(f"WhatsApp API verification failed: {resp.text}")
                        return False
            except Exception as e:
                self.logger.error(f"WhatsApp Cloud API connect error: {e}")
                return False
                
        # If no credentials, we stay disconnected
        return False

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not self.access_token:
            return {"status": "failed", "error": "Not connected"}
            
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": content}
        }
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.access_token}"}
                )
                if resp.status_code == 200:
                    self.last_activity = str(int(asyncio.get_event_loop().time()))
                    return {"status": "success", "id": resp.json().get("messages", [{}])[0].get("id")}
                
                self.last_error = resp.text
                return {"status": "failed", "error": resp.text}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Cloud API doesn't support fetching. Requires webhooks."""
        return []

    async def process_webhook(self, data: Dict[str, Any]):
        """Standardized entry point for WhatsApp Cloud API webhooks."""
        try:
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    # Process incoming messages
                    for msg in value.get("messages", []):
                        sender = msg.get("from")
                        body = ""
                        if msg.get("type") == "text":
                            body = msg.get("text", {}).get("body", "")
                        else:
                            body = f"[WhatsApp {msg.get('type','message')}]"

                        await self._dispatch_inbound({
                            "from": sender,
                            "body": body,
                            "id": msg.get("id"),
                            "timestamp": msg.get("timestamp"),
                            "account_id": self.phone_number_id,
                            "raw": msg
                        })
                    
                    # Track message status updates (read receipts etc.)
                    for status in value.get("statuses", []):
                        self.logger.debug(f"WhatsApp message {status.get('id')} status: {status.get('status')}")

        except Exception as e:
            self.logger.error(f"WhatsApp webhook parse failed: {e}")

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        """Health reporting for WhatsApp."""
        health = super().get_health()
        if self.is_connected:
            health.update({
                "phone_number_id": self.phone_number_id,
                "api_version": "v20.0"
            })
        return health
