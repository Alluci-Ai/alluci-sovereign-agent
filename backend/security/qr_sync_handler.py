import secrets
import time
import logging
from typing import Dict, Any, Optional
from backend.security.vault import VaultManager

logger = logging.getLogger("QRSyncHandler")

class QRSyncHandler:
    """
    Manages short-lived pairing sessions for mobile-to-daemon token exchange.
    Used for bridges requiring manual pairing or biometric-proxying.
    """
    def __init__(self, vault: VaultManager):
        self.vault = vault
        # In-memory storage of active sync challenges (sync_id -> timestamp)
        # In a multi-node setup, this should move to Redis.
        self._active_sessions: Dict[str, float] = {}
        self.ttl = 300 # 5 minutes

    def create_sync_challenge(self) -> str:
        """Generates a unique sync ID for a QR code."""
        sync_id = secrets.token_urlsafe(24)
        self._active_sessions[sync_id] = time.time()
        return sync_id

    async def complete_sync(self, bridge_id: str, account_id: str, sync_id: str, payload: Dict[str, Any]) -> bool:
        """
        Validates the sync_id and persists the mobile-provided payload.
        """
        # 1. Validate Session
        timestamp = self._active_sessions.get(sync_id)
        if not timestamp:
            logger.warning(f"QR Sync attempt with invalid ID: {sync_id}")
            return False
            
        if time.time() - timestamp > self.ttl:
            logger.warning(f"QR Sync attempt with expired ID: {sync_id}")
            del self._active_sessions[sync_id]
            return False

        # 2. Store Payload (Credentials)
        try:
            await self.vault.store_connection_secret(bridge_id, account_id, payload)
            logger.info(f"QR Sync completed successfully for {bridge_id}:{account_id}")
            
            # 3. Cleanup
            del self._active_sessions[sync_id]
            return True
            
        except Exception as e:
            logger.error(f"Failed to store QR synced credentials: {e}")
            return False
            
    def cleanup_expired(self):
        """Housekeeping to remove stale sessions."""
        now = time.time()
        expired = [sid for sid, ts in self._active_sessions.items() if now - ts > self.ttl]
        for sid in expired:
            del self._active_sessions[sid]
