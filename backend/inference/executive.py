from abc import ABC, abstractmethod
from typing import Literal, Dict, Any

class ExecutiveRouter(ABC):
    """
    [ Polytope Manifold v4.5 ]
    Abstract Neural Interface Layer.
    Decouples the Agent Harness (tools, memory, bridges) from the underlying LLM weights.
    Provides dynamic mapping to local models (Gemma 4) or 3rd-party APIs based on
    privacy and capability requirements.
    """

    @abstractmethod
    async def get_response(
        self, 
        prompt: str, 
        complexity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM", 
        privacy_level: Literal["PUBLIC", "SENSITIVE", "AIRGAPPED"] = "PUBLIC",
        psi: float = 0.0
    ) -> str:
        """
        Execute an inference request. The implementation must route the request
        to the appropriate model based on the complexity and privacy constraints.
        """
        pass

    @abstractmethod
    def evaluate_privacy_constraint(self, privacy_level: str, is_cloud_provider: bool) -> bool:
        """
        Returns True if the provider is allowed under the current privacy level.
        SENSITIVE and AIRGAPPED strict local execution.
        """
        pass

    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """
        Return the health status of the connected inference endpoints.
        """
        pass
