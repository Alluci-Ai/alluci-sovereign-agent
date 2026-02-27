
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BridgeAdapter(ABC):
    """
    Abstract Base Class for all sovereign bridge integrations.
    Bridges must handle their own local isolation and credential decryption.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        self.bridge_id = bridge_id
        self.vault_root = vault_root

    @abstractmethod
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Initialize secure session with the manifold provider."""
        pass

    @abstractmethod
    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Transmit data through the secure bridge tunnel."""
        pass

    @abstractmethod
    async def fetch_unread(self) -> List[Dict[str, Any]]:
        """Retrieve recent communications for autonomous processing."""
        pass

    @abstractmethod
    async def validate_integrity(self) -> bool:
        """Verify the E2E encryption and isolation status of the bridge."""
        pass
