from typing import Dict, Optional, Callable
from .base import Adapter
from .filesystem import FileSystemAdapter

class AdapterRegistry:
    def __init__(self):
        self._adapters: Dict[str, Adapter] = {}
        
        # Initialize default adapters
        self.register(FileSystemAdapter())
        
        # Placeholder for future adapters
        # self.register(WebSearchAdapter())
        # self.register(CodeAnalysisAdapter())

    def register(self, adapter: Adapter):
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Optional[Adapter]:
        # Handle aliases or fallbacks here if needed
        # For now, simplistic mapping: "write_file" -> "filesystem"
        
        if name in ["write_file", "read_file", "list_files"]:
            return self._adapters.get("filesystem")
            
        return self._adapters.get(name)
        
    def list_tools(self):
        return list(self._adapters.keys())
