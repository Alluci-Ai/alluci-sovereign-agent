from typing import Dict, Optional, Callable
from .base import Adapter
from .filesystem import FileSystemAdapter
from .bridge_actualization import BridgeActualizationAdapter
from .shell import ShellAdapter
from .web_search import WebSearchAdapter
from .web_fetch import WebFetchAdapter
from .code_exec import CodeExecAdapter
from .screen_capture import ScreenCaptureAdapter
from .doc_ingest import DocumentIngestAdapter

class AdapterRegistry:
    def __init__(self, vault_root: Optional[str] = None, memory_manager = None, on_inbound: Callable = None):  # type: ignore
        self._adapters: Dict[str, Adapter] = {}
        
        # Initialize default adapters
        self.register(FileSystemAdapter())
        self.register(BridgeActualizationAdapter(vault_root=vault_root, on_inbound=on_inbound))  # type: ignore
        self.register(ShellAdapter())
        self.register(WebSearchAdapter())
        self.register(WebFetchAdapter())
        self.register(CodeExecAdapter())
        self.register(ScreenCaptureAdapter())
        if memory_manager:
            self.register(DocumentIngestAdapter(memory_manager))
        # MemoryAdapter is initialized with the global memory instance in app.py

    def register(self, adapter: Adapter):
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Optional[Adapter]:
        # Handle aliases or fallbacks here if needed
        
        if name in ["write_file", "read_file", "list_files"]:
            return self._adapters.get("filesystem")
            
        if name in ["send_slack", "send_imessage", "send_whatsapp", "send_email", "bridge_actualization"]:
            return self._adapters.get("bridge_actualization")
            
        if name in ["web_search", "search"]:
            return self._adapters.get("web_search")
            
        if name in ["web_fetch", "fetch"]:
            return self._adapters.get("web_fetch")

        if name in ["code_exec", "execute"]:
            return self._adapters.get("code_exec")
            
        if name in ["screen_capture", "screenshot"]:
            return self._adapters.get("screen_capture")

        if name in ["doc_ingest", "ingest"]:
            return self._adapters.get("doc_ingest")
            
        if name in ["memory_search", "memory_store", "memory"]:
            return self._adapters.get("memory")
            
        return self._adapters.get(name)
        
    def list_tools(self):
        return list(self._adapters.keys())
