import secrets
import time
import logging
from ..logging_config import get_logger
from typing import Dict, Any, Optional
from backend.security.vault import VaultManager

logger = get_logger("QRSyncHandler")

class QRSyncHandler:
    """
    Manages short-lived pairing sessions for mobile-to-daemon token exchange.
    Used for bridges requiring manual pairing or biometric-proxying.
    """
    def __init__(self, vault: VaultManager, redis_client: Optional[Any] = None):
        self.vault = vault
        self.redis_client = redis_client
        # Memory fallback for active sync challenges if Redis is unavailable
        self._active_sessions: Dict[str, float] = {}
        self.ttl = 300 # 5 minutes

    async def create_sync_challenge(self) -> str:
        """Generates a unique sync ID for a QR code."""
        sync_id = secrets.token_urlsafe(24)
        if self.redis_client:
            try:
                await self.redis_client.setex(f"qr_sync:{sync_id}", self.ttl, str(time.time()))
            except Exception as e:
                logger.error(f"Redis setex failed in QR sync: {e}")
                self._active_sessions[sync_id] = time.time()
        else:
            self._active_sessions[sync_id] = time.time()
        return sync_id

    async def complete_sync(self, bridge_id: str, account_id: str, sync_id: str, payload: Dict[str, Any]) -> bool:
        """
        Validates the sync_id and persists the mobile-provided payload.
        """
        # 1. Validate Session
        timestamp = None
        if self.redis_client:
            try:
                res = await self.redis_client.get(f"qr_sync:{sync_id}")
                if res:
                    timestamp = float(res)
            except Exception as e:
                logger.error(f"Redis get failed in QR sync: {e}")
                timestamp = self._active_sessions.get(sync_id)
        else:
            timestamp = self._active_sessions.get(sync_id)

        if not timestamp:
            logger.warning(f"QR Sync attempt with invalid ID: {sync_id}")
            return False
            
        if time.time() - timestamp > self.ttl:
            logger.warning(f"QR Sync attempt with expired ID: {sync_id}")
            if self.redis_client:
                await self.redis_client.delete(f"qr_sync:{sync_id}")
            elif sync_id in self._active_sessions:
                del self._active_sessions[sync_id]
            return False

        # 2. Store Payload (Credentials)
        try:
            await self.vault.store_connection_secret(bridge_id, account_id, payload)
            logger.info(f"QR Sync completed successfully for {bridge_id}:{account_id}")
            
            # 3. Cleanup
            if self.redis_client:
                await self.redis_client.delete(f"qr_sync:{sync_id}")
            elif sync_id in self._active_sessions:
                del self._active_sessions[sync_id]
            return True
            
        except Exception as e:
            logger.error(f"Failed to store QR synced credentials: {e}")
            return False
            
    def cleanup_expired(self):
        """Housekeeping to remove stale sessions (only impacts memory fallback)."""
        now = time.time()
        expired = [sid for sid, ts in self._active_sessions.items() if now - ts > self.ttl]
        for sid in expired:
            del self._active_sessions[sid]
