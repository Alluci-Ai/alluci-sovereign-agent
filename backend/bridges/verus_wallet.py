
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
        to = data.get("to")
        amount = data.get("amount")
        currency = data.get("currency", "VRSC")
        memo = data.get("memo", "")
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
        return {"status": "ERROR", "message": f"Unknown action: {action}"}

    # --- BridgeAdapter Interface Implementation ---

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connects to the Verus node."""
        return await self.service.start_node()

    async def send(self, to: str, content: str, **kwargs) -> Dict[str, Any]:
        """Sends a message (VDXF) or funds via the bridge."""
        # For now, treat content as amount if numeric
        try:
            amount = float(content)
            res = await self.service.send(to, amount)
            return {"status": "success", "txid": res.get("txid")} if res.get("success") else {"status": "failed", "error": res.get("error")}
        except ValueError:
            return {"status": "failed", "error": "VerusID VDXF messaging is not yet fully implemented."}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """VerusID messaging (VDXF) inbox."""
        return []

    async def validate_integrity(self) -> bool:
        dashboard = await self.service.get_dashboard()
        return dashboard.connected

    async def mark_read(self, entry_id: str) -> bool:
        return True

    async def check_health(self) -> bool:
        return await self.validate_integrity()
