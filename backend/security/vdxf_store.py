
import hashlib
import logging
import time
from typing import Any, Dict, Optional
from backend.security.verus_rpc import verus_rpc
from backend.config import settings

logger = logging.getLogger("VDXFStore")

class VDXFStore:
    """
    Implements the 3-Tier Storage Model:
    Tier 1: On-Chain Hash Anchoring (alluci.vault.manifest@)
    Tier 2: Local Encrypted Cache (Fernet via VaultManager)
    Tier 3: In-Memory Hot Cache
    """
    def __init__(self, identity: str):
        self.identity = identity
        self.memory_cache: Dict[str, Any] = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_expiry: Dict[str, float] = {}
        self.vdxf_manifest_key = "alluci.vault.manifest@"

    def _get_hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    async def anchor_vault_hash(self, vault_data: str) -> bool:
        """
        Tier 1: Updates the on-chain manifest hash via updateidentity.
        This anchors the integrity of the local vault to the blockchain.
        """
        if not settings.VERUS_AUTH_ENABLED:
            return False

        try:
            vault_hash = self._get_hash(vault_data)
            identity_data = await verus_rpc.get_identity(self.identity)
            
            # Prepare the updateidentity payload
            # In a real VerusID, we'd append/update the contentmultimap
            manifest = {
                "version": 3,
                "keys_hash": f"sha256:{vault_hash}",
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "schema_version": 1
            }
            
            # Update the identity object's contentmultimap
            # Note: This requires the verusd node to have the primary address's private key
            identity_data["identity"]["contentmultimap"][self.vdxf_manifest_key] = [manifest]
            
            txid = await verus_rpc.update_identity(identity_data["identity"])
            logger.info(f"Vault hash anchored on-chain. TXID: {txid}")
            return True
        except Exception as e:
            logger.error(f"Failed to anchor vault hash: {str(e)}")
            return False

    async def verify_integrity(self, local_vault_data: str) -> bool:
        """
        Compares the local vault hash against the on-chain anchor.
        """
        if not settings.VERUS_AUTH_ENABLED:
            return True

        try:
            on_chain_data = await verus_rpc.get_content_multimap(self.identity, self.vdxf_manifest_key)
            if not on_chain_data:
                logger.warning("No on-chain manifest found. Integrity check skipped.")
                return True
            
            on_chain_hash = on_chain_data[0].get("keys_hash", "").replace("sha256:", "")
            local_hash = self._get_hash(local_vault_data)
            
            if on_chain_hash == local_hash:
                logger.info("Vault integrity verified against blockchain.")
                return True
            else:
                logger.error("VAULT INTEGRITY BREACH: Local hash does not match on-chain anchor!")
                return False
        except Exception as e:
            logger.error(f"Integrity check failed: {str(e)}")
            return False

    def get_from_memory(self, key: str) -> Optional[Any]:
        """Tier 3: Hot Cache read."""
        if key in self.memory_cache:
            if time.time() < self.cache_expiry.get(key, 0):
                return self.memory_cache[key]
            else:
                del self.memory_cache[key]
        return None

    def set_memory(self, key: str, value: Any):
        """Tier 3: Hot Cache write."""
        self.memory_cache[key] = value
        self.cache_expiry[key] = time.time() + self.cache_ttl
