from typing import Dict, Any, List, Optional
import logging
from .base import BridgeAdapter

try:
    from pyicloud import PyiCloudService
except ImportError:
    PyiCloudService = None

class ICloudBridge(BridgeAdapter):
    """
    Sovereign iCloud Bridge wrapping pyicloud for end-to-end file/data access.
    Implements Token modal with optional App-Specific Passwords and 2FA via WebSocket.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.api: Optional[PyiCloudService] = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        apple_id = credentials.get("apple_id")
        password = credentials.get("app_specific_password") or credentials.get("password")
        
        if not PyiCloudService:
            self.logger.error("pyicloud library not installed.")
            return False

        try:
            self.api = PyiCloudService(apple_id, password)
            
            if self.api.requires_2fa:
                self.logger.info(f"iCloud 2FA required for {apple_id}")
                if self.on_event:
                    asyncio.create_task(self.on_event("bridge.status", {
                        "bridge_id": self.bridge_id,
                        "status": "2FA_REQUIRED",
                        "apple_id": apple_id
                    }))
                return False 
            
            self.is_connected = True
            self.session = {"apple_id": apple_id}
            self.logger.info(f"iCloud Session anchored for {apple_id}")
            return True
        except Exception as e:
            self.logger.error(f"iCloud connect failed: {e}")
            return False

    async def submit_2fa(self, code: str) -> Dict[str, Any]:
        """Handles inline UI prompt for Apple's 6-digit verification code."""
        if not self.api:
            return {"status": "FAILED", "error": "No active session"}
            
        try:
            result = self.api.validate_2fa_code(code)
            if result:
                self.is_connected = True
                self.logger.info("iCloud 2FA Validation Successful.")
                if self.on_event:
                    asyncio.create_task(self.on_event("bridge.status", {
                        "bridge_id": self.bridge_id,
                        "status": "CONNECTED"
                    }))
                return {"status": "SUCCESS"}
            else:
                return {"status": "FAILED", "error": "Invalid 2FA code"}
        except Exception as e:
            self.logger.error(f"iCloud 2FA submission error: {e}")
            return {"status": "FAILED", "error": str(e)}

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        return {"status": "failed", "error": "Messaging not supported for iCloud (use iMessage bridge)"}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieves recent file changes or mentions from iCloud Drive if connected.
        """
        if not self.is_connected or not self.api:
            return []
            
        try:
            # Placeholder for actual file discovery logic
            # e.g., self.api.drive.ls()
            return []
        except Exception as e:
            self.logger.warning(f"iCloud fetch failed: {e}")
            return []

    async def validate_integrity(self) -> bool:
        if not self.api:
            return False
        # Simple check to see if authenticated session is still valid
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        health = super().get_health()
        if self.is_connected:
            health.update({
                "apple_id": self.session.get("apple_id"),
                "status_message": "Operational",
                "requires_2fa": self.api.requires_2fa if self.api else False
            })
        return health
