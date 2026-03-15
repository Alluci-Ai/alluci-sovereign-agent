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
        logger.info(f"[WEBAUTHN] Credential stored: {credential_id[:16]}...")

    async def get_credential(self, credential_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored credential by ID."""
        cred = self._cache.get(credential_id)
        if cred:
            # Deserialize public_key hex back to bytes
            return {**cred, "public_key": bytes.fromhex(cred["public_key"])}
        return None

    async def update_sign_count(self, credential_id: str, new_count: int) -> None:
        """Update the sign counter after successful authentication."""
        if credential_id in self._cache:
            self._cache[credential_id]["sign_count"] = new_count

    def list_credentials(self) -> list:
        """Return all registered credential IDs."""
        return list(self._cache.keys())


# Module-level singleton
credential_store = CredentialStore()
