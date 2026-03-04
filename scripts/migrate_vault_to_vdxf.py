
import asyncio
import logging
from backend.security.vault import VaultManager
from backend.security.vdxf_store import VDXFStore
from backend.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VaultMigration")

async def run_migration():
    if not settings.VERUS_AUTH_ENABLED or not settings.VERUS_ID_IDENTITY:
        logger.error("VerusID integration not enabled in settings. Set VERUS_AUTH_ENABLED=True and VERUS_ID_IDENTITY.")
        return

    logger.info(f"Starting migration from local vault to VDXF on-chain anchor for identity: {settings.VERUS_ID_IDENTITY}")
    
    # Initialize components
    vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    vdxf = VDXFStore(settings.VERUS_ID_IDENTITY)
    
    # 1. Collect all local secrets
    active_vaults = vault.get_active_vaults()
    logger.info(f"Found {len(active_vaults)} active vault files: {active_vaults}")
    
    if not active_vaults:
        logger.warning("No secrets found to migrate.")
        return

    # 2. Verify current integrity
    vault_data = vault._get_full_vault_state()
    logger.info("Computing aggregate vault hash...")
    
    # 3. Anchor the current state to the blockchain
    logger.info("Anchoring current vault state to Verus blockchain (Tier 1)...")
    success = await vdxf.anchor_vault_hash(vault_data)
    
    if success:
        logger.info("MIGRATION_SUCCESSFUL: Vault integrity anchored on-chain.")
        
        # 4. Verify round-trip
        verified = await vdxf.verify_integrity(vault_data)
        if verified:
            logger.info("VERIFICATION_SUCCESSFUL: Local data matches on-chain anchor.")
        else:
            logger.error("VERIFICATION_FAILED: On-chain hash does not match local data after anchoring!")
    else:
        logger.error("MIGRATION_FAILED: Could not anchor hash on-chain (Daemon reachable? Wallet funded?)")

if __name__ == "__main__":
    asyncio.run(run_migration())
