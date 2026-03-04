import httpx
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from .base import BridgeAdapter

class TelegramBridge(BridgeAdapter):
    """
    Production stub for Telegram Bot API.
    Operates within the Simplicial Vault security context.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.bot_token: str = ""
        self.api_url = "https://api.telegram.org/bot"

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to Telegram via Bot Token.
        """
        self.bot_token = credentials.get("bot_token", "")
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.api_url}{self.bot_token}/getMe")
                data = res.json()
                if data.get("ok"):
                    self.is_connected = True
                    self.logger.info(f"Telegram Connected. Bot: {data['result']['username']}")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Telegram connection failed: {e}")
            return False

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        timestamp = datetime.now().isoformat()
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}{self.bot_token}/sendMessage",
                    json={
                        "chat_id": recipient,
                        "text": content
                    }
                )
                data = res.json()
                status = "success" if data.get("ok") else "failed"
                
                self._persist_to_vault("sent", {
                    "chat_id": recipient,
                    "content": content,
                    "status": status,
                    "timestamp": timestamp,
                    "error": data.get("description")
                })
                
                return {"status": status, "response": data}
        except Exception as e:
            self.logger.error(f"Telegram send_message failed: {e}")
            self._persist_to_vault("sent", {"chat_id": recipient, "content": content, "status": "exception", "error": str(e)})
            return {"status": "failed", "error": f"Bridge communication error: {type(e).__name__}"}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.is_connected:
            return []
            
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(f"{self.api_url}{self.bot_token}/getUpdates", json={"limit": limit})
                data = res.json()
                if not data.get("ok"):
                    return []
                
                messages = []
                for item in data.get("result", []):
                    if "message" in item:
                        msg = item["message"]
                        m = {
                            "id": str(msg.get("message_id")),
                            "from": str(msg.get("from", {}).get("id")),
                            "body": msg.get("text", ""),
                            "timestamp": datetime.fromtimestamp(msg.get("date")).isoformat(),
                            "protocol": "TELEGRAM"
                        }
                        messages.append(m)
                        self._persist_to_vault("inbox", m)
                return messages
        except Exception:
            return []

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
