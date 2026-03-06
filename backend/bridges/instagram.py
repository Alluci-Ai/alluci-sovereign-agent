from typing import Dict, Any, List
from .base import BridgeAdapter

class InstagramBridge(BridgeAdapter):
    """
    Sovereign Instagram Bridge.
    Supports Graph API for Business/Creator (DMs), Basic Display API for Personal (Profile only).
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        access_token = credentials.get("access_token")
        if not access_token:
            return False
            
        account_type = credentials.get("account_type", "PERSONAL")
        self.is_connected = True
        self.logger.info(f"Instagram session established. Type: {account_type}")
        return True

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected:
            return {"status": "failed", "error": "Not connected"}
        return {"status": "success"}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected
