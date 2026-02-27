from abc import ABC, abstractmethod
from typing import Dict, Any

class Adapter(ABC):
    """
    Interface for executable task adapters.
    """
    name: str = "base"
    description: str = "Abstract base adapter"

    @abstractmethod
    async def execute(self, args: Dict[str, Any]) -> Any:
        """
        Execute the adapter logic.
        Must be async.
        """
        pass
