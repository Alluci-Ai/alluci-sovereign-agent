from typing import Dict, Optional
from .base import Adapter
from .filesystem import FileSystemAdapter
from .bridge_actualization import BridgeActualizationAdapter

class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, Adapter] = {}
        
        # Initialize default adapters
        self.register(FileSystemAdapter())
        self.register(BridgeActualizationAdapter())
        
        # Placeholder for future adapters
        # self.register(WebSearchAdapter())
        # self.register(CodeAnalysisAdapter())

    def register(self, adapter: Adapter):
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Optional[Adapter]:
        # Handle aliases or fallbacks here if needed
        
        if name in ["write_file", "read_file", "list_files"]:
            return self._adapters.get("filesystem")
            
        if name in ["send_slack", "send_imessage", "send_whatsapp", "send_email", "bridge_actualization"]:
            return self._adapters.get("bridge_actualization")
            
        return self._adapters.get(name)
        
    def list_tools(self):
        return list(self._adapters.keys())
