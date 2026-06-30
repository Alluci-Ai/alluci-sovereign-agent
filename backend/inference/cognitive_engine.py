from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

class CognitiveEngine(ABC):
    """
    [ PPN-035 ] The Cognitive Abstraction Layer.
    Abstract Base Class for OS-agnostic Local Cognitive Engines (LCE).
    """

    @abstractmethod
    def load_model_sync(self) -> None:
        """Synchronously loads the model weights into memory."""
        pass

    @abstractmethod
    async def ensure_loaded(self) -> None:
        """Asynchronously ensures the model is loaded."""
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        agent_id: Optional[str] = None
    ) -> str:
        """Generates a complete response natively."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_instruction: str = "",
        max_tokens: int = 1024,
        temperature: float = 0.7,
        agent_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Generates a stream of text tokens."""
        yield ""

    @abstractmethod
    async def apply_lora_adapter(self, agent_id: str) -> None:
        """
        Dynamically applies a True LoRA (PEFT) adapter 
        (specialized agent logic) to the active model.
        """
        pass
