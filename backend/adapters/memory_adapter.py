
import logging
from ..logging_config import get_logger
from typing import Dict, Any
from .base import Adapter

logger = get_logger("Adapters.Memory")

class MemoryAdapter(Adapter):
    def __init__(self, memory_manager):
        self.memory = memory_manager

    @property
    def name(self) -> str:
        return "memory"

    async def execute(self, args: Dict[str, Any]) -> Any:
        action = args.get("action", "search")
        query = args.get("query")
        content = args.get("content")
        metadata = args.get("metadata")
        
        if not self.memory:
            return "Memory manager not initialized."

        if action == "search":
            return await self.memory.search(query)
        elif action == "store":
            return await self.memory.store(content, metadata)
        else:
            return f"Unknown memory action: {action}"
