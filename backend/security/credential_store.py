"""
WebAuthn Credential Store — persists registered passkey public keys.
Backed by the database (CredentialRecord model) with in-memory cache.
"""
import json
import logging
from typing import Optional, Dict, Any
from ..logging_config import get_logger

logger = get_logger("CredentialStore")


class CredentialStore:
    """
    Stores registered WebAuthn credential public keys so they can be
    retrieved during authentication assertion verification.
    """

    def __init__(self):
        # In-memory cache: credential_id -> credential_data dict
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def load_from_vault(self):
        """Initializes the cache from the vault if available."""
        from .. import services
        if services.vault:
            try:
                creds = await services.vault.retrieve_secret("webauthn_credentials")
                if creds:
                    self._cache = creds
                    logger.info(f"[WEBAUTHN] Loaded {len(creds)} credentials from vault.")
            except Exception as e:
                logger.error(f"Failed to load credentials from vault: {e}")

    async def _persist(self):
        """Persists the current cache to the vault."""
        from .. import services
        if services.vault:
            try:
                await services.vault.store_secret("webauthn_credentials", self._cache)
            except Exception as e:
                logger.error(f"Failed to persist credentials to vault: {e}")

    async def store_credential(
        self,
        credential_id: str,
        public_key: bytes,
        sign_count: int,
        user_handle: str = "sovereign_admin",
    ) -> None:
        """Persist a newly registered credential."""
        self._cache[credential_id] = {
            "credential_id": credential_id,
            "public_key": public_key.hex(),
            "sign_count": sign_count,
            "user_handle": user_handle,
        }
        await self._persist()
        logger.info(f"[WEBAUTHN] Credential stored and vaulted: {credential_id[:16]}...")

    async def get_credential(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored credential by ID."""
        if not self._cache:
            await self.load_from_vault()
            
        cred = self._cache.get(credential_id)
        if cred:
            # Deserialize public_key hex back to bytes
            return {**cred, "public_key": bytes.fromhex(cred["public_key"])}
        return None

    async def update_sign_count(self, credential_id: str, new_count: int) -> None:
        """Update the sign counter after successful authentication."""
        if credential_id in self._cache:
            self._cache[credential_id]["sign_count"] = new_count
            await self._persist()

    async def list_credentials(self) -> list:
        """Return all registered credential IDs, ensuring cache is loaded."""
        if not self._cache:
            await self.load_from_vault()
        return list(self._cache.keys())


# Module-level singleton
credential_store = CredentialStore()
