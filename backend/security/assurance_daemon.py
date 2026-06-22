import asyncio
import logging
from typing import Dict, Any
from ..logging_config import get_logger

logger = get_logger("AssuranceDaemon")

class AssuranceDaemon:
    """
    Background worker that handles blockchain verifications asynchronously.
    This ensures Vault decryption is instantaneous and never blocked by network calls.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AssuranceDaemon, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.queue = asyncio.Queue()
        self.worker_task = None

    async def start(self):
        if self.worker_task is None:
            self.worker_task = asyncio.create_task(self._worker())
            logger.info("Assurance Daemon started.")

    async def stop(self):
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
            logger.info("Assurance Daemon stopped.")

    def enqueue_verification(self, bridge_id: str, vdxf_store: Any, vault_aggregate: str):
        """Queue a verification check to be run in the background."""
        self.queue.put_nowait({
            "type": "verify",
            "bridge_id": bridge_id,
            "vdxf": vdxf_store,
            "aggregate": vault_aggregate
        })

    def enqueue_anchor(self, vdxf_store: Any, vault_aggregate: str):
        """Queue an anchoring operation to be run in the background."""
        self.queue.put_nowait({
            "type": "anchor",
            "vdxf": vdxf_store,
            "aggregate": vault_aggregate
        })

    async def _worker(self):
        while True:
            try:
                task = await self.queue.get()
                
                if task["type"] == "verify":
                    vdxf = task["vdxf"]
                    is_valid = await vdxf.verify_integrity(task["aggregate"])
                    if not is_valid:
                        bridge_id = task["bridge_id"]
                        logger.critical(
                            f"[SECURITY] BACKGROUND VDXF INTEGRITY CHECK FAILED for bridge '{bridge_id}'. "
                            f"Vault data has been tampered with! "
                            f"ACTION REQUIRED: Audit your local filesystem and rotate keys immediately."
                        )
                        # Future: emit WebSocket alert to frontend
                        
                elif task["type"] == "anchor":
                    vdxf = task["vdxf"]
                    await vdxf.anchor_vault_hash(task["aggregate"])
                
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Assurance Daemon Error: {e}")

assurance_daemon = AssuranceDaemon()
