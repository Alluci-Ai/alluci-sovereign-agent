
import hashlib
import logging
from ..logging_config import get_logger
import time
from typing import Any, Dict, Optional
from cachetools import TTLCache
from backend.security.verus_rpc import verus_rpc
from backend.config import settings

logger = get_logger("VDXFStore")

class VDXFStore:
    """
    Implements the 3-Tier Storage Model:
    Tier 1: On-Chain Hash Anchoring (alluci.vault.manifest@)
    Tier 2: Local Encrypted Cache (Fernet via VaultManager)
    Tier 3: In-Memory Hot Cache
    """
    def __init__(self, identity: str):
        self.identity = identity
        self.memory_cache = TTLCache(maxsize=1000, ttl=300)  # Tier 3 Hot Cache
        self.on_chain_cache = TTLCache(maxsize=10, ttl=900)  # 15 minute cache for blockchain reads
        self.vdxf_manifest_key = "alluci.vault.manifest@"

    def _get_hash(self, data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    async def anchor_vault_hash(self, vault_data: str) -> Optional[str]:
        """
        Tier 1: Updates the on-chain manifest hash via updateidentity.
        This anchors the integrity of the local vault to the blockchain.
        Returns TXID if successful, None otherwise.
        """
        if settings.VERUS_INTEGRATION_MODE != "full":
            return None

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
            # Update cache to prevent false alarms on next read
            self.on_chain_cache[self.vdxf_manifest_key] = vault_hash
            return txid
        except Exception as e:
            logger.error(f"Failed to anchor vault hash: {str(e)}")
            return None

    async def anchor_audit_batch(self, batch_data: str) -> Optional[str]:
        """
        Anchors a batch of audit logs to the Verus blockchain.
        Returns TXID if successful, None otherwise.
        """
        if settings.VERUS_INTEGRATION_MODE != "full":
            return None

        try:
            batch_hash = self._get_hash(batch_data)
            identity_data = await verus_rpc.get_identity(self.identity)
            
            manifest = {
                "version": 1,
                "audit_hash": f"sha256:{batch_hash}",
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            
            vdxf_audit_key = "alluci.audit.ledger@"
            if "contentmultimap" not in identity_data["identity"]:
                identity_data["identity"]["contentmultimap"] = {}
                
            identity_data["identity"]["contentmultimap"][vdxf_audit_key] = [manifest]
            
            txid = await verus_rpc.update_identity(identity_data["identity"])
            logger.info(f"Audit batch hash anchored on-chain. TXID: {txid}")
            return txid
        except Exception as e:
            logger.error(f"Failed to anchor audit batch hash: {str(e)}")
            return None

    async def verify_integrity(self, local_vault_data: str) -> bool:
        """
        Compares the local vault hash against the on-chain anchor.
        """
        if settings.VERUS_INTEGRATION_MODE == "off":
            return True

        try:
            local_hash = self._get_hash(local_vault_data)

            # Check robust TTL Cache first (prevents boot spam)
            if self.vdxf_manifest_key in self.on_chain_cache:
                on_chain_hash = self.on_chain_cache[self.vdxf_manifest_key]
            else:
                on_chain_data = await verus_rpc.get_content_multimap(self.identity, self.vdxf_manifest_key)
                if not on_chain_data:
                    logger.warning("No on-chain manifest found. Integrity check skipped.")
                    return True
                on_chain_hash = on_chain_data[0].get("keys_hash", "").replace("sha256:", "")  # type: ignore
                self.on_chain_cache[self.vdxf_manifest_key] = on_chain_hash
            
            if on_chain_hash == local_hash:
                logger.info("Vault integrity verified against blockchain.")
                return True
            else:
                logger.error("VAULT INTEGRITY BREACH: Local hash does not match on-chain anchor!")
                return False
        except Exception as e:
            logger.warning(f"Integrity check skipped due to network/RPC failure: {str(e)}")
            return True

    def get_from_memory(self, key: str) -> Optional[Any]:
        """Tier 3: Hot Cache read."""
        return self.memory_cache.get(key)

    def set_memory(self, key: str, value: Any):
        """Tier 3: Hot Cache write."""
        self.memory_cache[key] = value
