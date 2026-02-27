import httpx
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from .base import BridgeAdapter

class SignalBridge(BridgeAdapter):
    """
    Production stub for Signal via signal-cli REST API.
    Operates within the Simplicial Vault security context.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.api_url = "http://localhost:8080/v2/api"
        self.phone_number: str = ""

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to a local signal-cli REST server.
        Expected credentials: {"phone_number": "+1234567890", "api_url": "optional"}
        """
        self.phone_number = credentials.get("phone_number", "")
        if credentials.get("api_url"):
             self.api_url = credentials.get("api_url")
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self.api_url}/about")
                if res.status_code == 200:
                    self.is_connected = True
                    self.logger.info(f"Signal Connected via signal-cli. Number: {self.phone_number}")
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Signal connection failed: {e}")
            return False

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        timestamp = datetime.now().isoformat()
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}/send",
                    json={
                        "message": content,
                        "number": self.phone_number,
                        "recipients": [recipient]
                    }
                )
                data = res.json()
                status = "success" if res.status_code in (200, 201) else "failed"
                
                self._persist_to_vault("sent", {
                    "recipient": recipient,
                    "content": content,
                    "status": status,
                    "timestamp": timestamp,
                    "error": data.get("error") if status == "failed" else None
                })
                
                return {"status": status, "response": data}
        except Exception as e:
            self._persist_to_vault("sent", {"recipient": recipient, "content": content, "status": "exception", "error": str(e)})
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        # Fetch operations here usually rely on webhooks pointing to localhost.
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
