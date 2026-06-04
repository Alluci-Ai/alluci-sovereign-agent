
import logging
from .base import BridgeAdapter
from ..verus_wallet import wallet_service
from typing import Any, Dict, List, Optional
from ..logging_config import get_logger

logger = get_logger("VerusWalletBridge")

class VerusWalletBridge(BridgeAdapter):
    """
    Bridge wrapper for VerusWalletService to provide a consistent 
    interface for both the channel registry and the wallet router.
    """
    def __init__(self, name: str, vault_root: str, vault_manager=None, **kwargs):
        super().__init__(name, vault_root, vault_manager, **kwargs)
        self.service = wallet_service
        self.sovereign_mode_active = False

    async def get_status(self) -> Dict[str, Any]:
        """Provides the status of the wallet/node (called by wallet.py)."""
        dashboard = await self.service.get_dashboard()
        return {
            "connected": dashboard.connected,
            "identity": dashboard.identity,
            "blockchain": dashboard.blockchain,
            "timestamp": dashboard.timestamp
        }

    async def get_balance(self) -> Dict[str, Any]:
        """Provides balanced (called by wallet.py)."""
        return await self.service.get_balances()

    async def send_funds(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sends funds (called by wallet.py)."""
        to = str(data.get("to", ""))
        amount = float(data.get("amount", 0.0))
        currency = str(data.get("currency", "VRSC"))
        memo = str(data.get("memo", ""))
        return await self.service.send(to, amount, currency, memo)

    async def get_mining_status(self) -> Dict[str, Any]:
        """Returns mining status (called by wallet.py)."""
        return await self.service.get_mining_status()

    async def get_node_status(self) -> Dict[str, Any]:
        """Returns low-level daemon status (called by wallet.py via get_info)."""
        try:
            info = await self.service.rpc.get_info()
            return {"active": True, "info": info}
        except Exception as e:
            return {"active": False, "error": str(e)}

    async def execute_node_action(self, action: str) -> Dict[str, Any]:
        """Executes node actions like start/stop (called by wallet.py)."""
        if action == "start_mining":
            return await self.service.start_mining()
        elif action == "stop_mining":
            return await self.service.stop_mining()
        elif action == "start_staking":
            return await self.service.start_staking()
        elif action == "stop_staking":
            return await self.service.stop_mining()
        return {"error": "Unknown action"}

    async def save_workflow_state(self, key: str, state_data: str) -> bool:
        """
        Routes storage based on Operating Mode.
        In Lite Mode: Stores in local encrypted SQLite vault.
        In Sovereign Mode: Routes to C++ VerusMCPEngine for VDXF on-chain storage.
        """
        if self.sovereign_mode_active:
            logger.info(f"Sovereign Mode: Storing state '{key}' on-chain via VDXF.")
            import json
            # Store via VerusID contentmultimap natively
            res = await self.service.update_identity_data(f"alluci.workflow.{key}@", json.dumps(state_data))
            return res.get("success", False)
        else:
            logger.info(f"Lite Mode: Storing state '{key}' in local SQLite vault.")
            if self.vault_manager:
                await self.vault_manager.store_secret(key, state_data)
                return True
            return False

    async def get_workflow_state(self, key: str) -> Optional[str]:
        if self.sovereign_mode_active:
            logger.info(f"Sovereign Mode: Retrieving state '{key}' from VDXF.")
            import json
            # Read from VerusID contentmultimap natively
            if not self.service.identity:
                logger.error("No VerusID configured. Cannot retrieve workflow state.")
                return None
            try:
                cmm = await self.service.rpc.get_content_multimap(self.service.identity, f"alluci.workflow.{key}@")
                if cmm and isinstance(cmm, list):
                    return json.loads(cmm[-1])
                return None
            except Exception as e:
                logger.error(f"Failed to retrieve workflow state: {e}")
                return None
        else:
            logger.info(f"Lite Mode: Retrieving state '{key}' from local SQLite vault.")
            if self.vault_manager:
                return await self.vault_manager.retrieve_secret(key)
            return None

    # --- BridgeAdapter Interface Implementation ---

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connects to the Verus node."""
        return await self.service.start_node()

    async def send(self, to: str, content: str, **kwargs) -> Dict[str, Any]:  # type: ignore
        """Sends a message (VDXF) or funds via the bridge."""
        # 1. Check if it's a numeric amount (send funds)
        try:
            amount = float(content)
            res = await self.service.send(to, amount)
            return {"status": "success", "txid": res.get("txid")} if res.get("success") else {"status": "failed", "error": res.get("error")}
        except ValueError:
            # 2. Otherwise treat as VDXF P2P messaging (Zero Stubs)
            res = await self.service.send_vdxf_message(to, content)
            return {"status": "success", "txid": res.get("txid")} if res.get("success") else {"status": "failed", "error": res.get("error")}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """VerusID messaging (VDXF) inbox."""
        # Production Implementation: Pull from the agent's recent message peers.
        # For this bridge, we poll the default peer if set, otherwise return empty list.
        # In a multi-agent scenario, the orchestrator handles the peer registry.
        return await self.service.fetch_vdxf_messages("AlluciPeer@")

    async def validate_integrity(self) -> bool:
        dashboard = await self.service.get_dashboard()
        return dashboard.connected

    async def mark_read(self, entry_id: str) -> bool:
        return True

    async def check_health(self) -> bool:
        return await self.validate_integrity()
