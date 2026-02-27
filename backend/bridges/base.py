
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
import logging

class BridgeAdapter(ABC):
    """
    Abstract Base Class for all sovereign bridge integrations.
    Enforces Simplicial Vault Isolation to prevent cross-bridge data leakage.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        self.bridge_id = bridge_id
        self.logger = logging.getLogger(f"Bridge_{bridge_id.upper()}")
        
        # Simplicial Vault Path: ~/.polytope/vaults/{bridge_id}
        # This directory is the ONLY place this bridge is allowed to write state.
        self.vault_path = os.path.join(vault_root, bridge_id)
        self._enforce_vault_isolation()
        
        self.is_connected = False
        self.session: Any = None

    def _enforce_vault_isolation(self):
        """
        Creates the isolated vault directory with strict permissions (rwx------).
        """
        if not os.path.exists(self.vault_path):
            try:
                os.makedirs(self.vault_path, mode=0o700, exist_ok=True)
            except OSError as e:
                self.logger.critical(f"Failed to create isolated vault: {e}")
                raise PermissionError(f"Vault isolation failed for {self.bridge_id}")

    @abstractmethod
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Initialize secure session with the manifold provider."""
        pass

    @abstractmethod
    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Transmit data through the secure bridge tunnel."""
        pass

    @abstractmethod
    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent communications for autonomous processing."""
        pass

    @abstractmethod
    async def validate_integrity(self) -> bool:
        """Verify the E2E encryption and connection status."""
        pass

    async def disconnect(self):
        """Graceful teardown of the connection."""
        self.is_connected = False
        self.session = None
