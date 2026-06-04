import asyncio
import json
import hashlib
from typing import Optional
from sqlmodel import Session, select

from ..logging_config import get_logger
from ..database import engine as db_engine
from ..models import AuditLog
from ..config import settings
from .vdxf_store import VDXFStore

logger = get_logger("AuditVerifier")

class AuditVerifier:
    """
    Verifier Daemon (The Auditor) and Tamper-Alert Protocol.
    Periodically checks the local SQLite audit ledger against the Verus blockchain
    VDXF anchors. If a mismatch is detected, triggers a Tamper Alert.
    """
    def __init__(self, vault, interval_minutes: int = 15):
        self.vault = vault
        self.interval_seconds = interval_minutes * 60
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            return
        self._running = True
        logger.info(f"[AUDITOR] Starting Audit Verifier Daemon (Interval: {self.interval_seconds}s)")
        self._task = asyncio.create_task(self._verification_loop())

    async def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[AUDITOR] Stopped Audit Verifier Daemon.")

    async def _verification_loop(self):
        while self._running:
            try:
                await self.verify_ledger()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[AUDITOR] Loop error: {e}")
            
            try:
                await asyncio.sleep(self.interval_seconds)
            except asyncio.CancelledError:
                break

    async def verify_ledger(self):
        """
        1. Reads the most recently anchored batch of logs.
        2. Recomputes their integrity hash locally.
        3. Fetches the on-chain hash using the TXID/VDXF key.
        4. Compares them. Raises Tamper Alert if they differ.
        """
        if not settings.VERUS_AUTH_ENABLED or not settings.VERUS_ID_IDENTITY:
            logger.debug("[AUDITOR] Verus auth disabled. Skipping verification.")
            return

        # Find the most recent anchored batch (group by verus_txid)
        with Session(db_engine) as session:
            # We just get the latest verus_txid that is not null
            latest_anchored = session.exec(
                select(AuditLog).where(AuditLog.verus_txid != None).order_by(AuditLog.id.desc()).limit(1)  # type: ignore
            ).first()

            if not latest_anchored:
                logger.debug("[AUDITOR] No anchored logs found to verify.")
                return

            txid = latest_anchored.verus_txid
            
            # Now fetch all logs that share this txid to recompute the batch hash
            batch_records = session.exec(
                select(AuditLog).where(AuditLog.verus_txid == txid).order_by(AuditLog.id)  # type: ignore
            ).all()

            # The batch data must match exactly how we serialized it during anchoring
            batch_data = json.dumps([r.model_dump(exclude={"verus_txid", "vdxf_key", "anchored_timestamp"}) for r in batch_records], default=str)
            local_hash = hashlib.sha256(batch_data.encode()).hexdigest()

        # Fetch on-chain hash
        try:
            from .verus_rpc import verus_rpc
            on_chain_data = await verus_rpc.get_content_multimap(settings.VERUS_ID_IDENTITY, "alluci.audit.ledger@")
            if not isinstance(on_chain_data, list):
                logger.warning(f"[AUDITOR] On-chain data not found for identity {settings.VERUS_ID_IDENTITY}.")
                return

            on_chain_hash = on_chain_data[0].get("audit_hash", "").replace("sha256:", "")

            if local_hash == on_chain_hash:
                logger.info(f"[AUDITOR] Ledger integrity verified. TXID: {txid} matches local hash.")
            else:
            if txid is not None:
                await self._trigger_tamper_alert(txid, local_hash, on_chain_hash)
        except Exception as e:
            logger.error(f"[AUDITOR] Failed to verify on-chain ledger: {e}")

    async def _trigger_tamper_alert(self, txid: str, local_hash: str, on_chain_hash: str):
        """
        TAMPER ALERT PROTOCOL
        Triggered when local SQLite hash does not match the immutable Verus blockchain hash.
        """
        logger.critical("!!! TAMPER ALERT !!! LOCAL AUDIT LEDGER HAS BEEN COMPROMISED !!!")
        logger.critical(f"TXID: {txid} | Local Hash: {local_hash} | On-Chain Hash: {on_chain_hash}")
        
        # 1. Lock the vault (freezes all keys and stops memory access)
        if self.vault:
            self.vault.lock_vault()
            logger.critical("[AUDITOR] Vault locked due to tamper alert.")

        # 2. Log the breach
        with Session(db_engine) as session:
            breach_log = AuditLog(
                event_id="TAMPER_ALERT",
                event="security.tamper_detected",
                details=f"Hash mismatch for TXID {txid}",
                status="CRITICAL",
                integrity_hash="tamper"
            )
            session.add(breach_log)
            session.commit()
