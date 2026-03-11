import pyotp
import asyncio
from typing import Dict, Any, List
from .base import BridgeAdapter

class IWatchBridge(BridgeAdapter):
    """
    HTTP-receiver adapter for Apple Watch pairing and HealthKit ingestion.
    Validates a 6-digit TOTP pairing code from the Swift companion app.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Loads the pre-shared TOTP secret from credentials.
        """
        self.totp_secret = credentials.get("totp_secret")
        self.is_connected = bool(self.totp_secret)
        return self.is_connected
        
    async def submit_pairing_code(self, code: str) -> Dict[str, Any]:
        """
        Validates the 6-digit pairing code presented on the Watch screen.
        The backend must have already generated and stored the base32 secret.
        """
        self.logger.info(f"Received Watch pairing attempt with code: {code}")
        
        # In production, the backend orchestrator generates the secret and stores it
        # in the vault prior to the user entering the code from the watch.
        if not hasattr(self, "pending_totp_secret") or not self.pending_totp_secret:
            return {"status": "FAILED", "error": "No pending pairing session active."}
            
        totp = pyotp.TOTP(self.pending_totp_secret)
        
        # Verify the code with a small window of leniency (±1 interval = ±30s)
        if totp.verify(code, valid_window=1):
            self.totp_secret = self.pending_totp_secret
            self.is_connected = True
            self.pending_totp_secret = None
            return {
                "status": "SUCCESS", 
                "paired": True, 
                "credentials": {"totp_secret": self.totp_secret}
            }
        else:
            return {"status": "FAILED", "error": "Invalid or expired pairing code."}

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        return {"status": "failed", "error": "Not supported for iWatch"}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def get_health(self) -> Dict[str, Any]:
        health = super().get_health()
        if self.is_connected:
            health.update({
                "mode": "HealthKit Ingestion (TOTP Secured)",
                "paired": True
            })
        return health
