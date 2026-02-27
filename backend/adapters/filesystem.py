import os
import aiofiles
from typing import Dict, Any
from .base import Adapter
from ..engine.errors import AdapterError

class FileSystemAdapter(Adapter):
    name = "filesystem"
    description = "Read/Write files in the secure workspace."
    
    def __init__(self, workspace_root: str = "workspace"):
        self.workspace_root = os.path.abspath(workspace_root)
        if not os.path.exists(self.workspace_root):
            os.makedirs(self.workspace_root, exist_ok=True)

    def _get_secure_path(self, rel_path: str) -> str:
        """Enforces sandbox containment."""
        full_path = os.path.abspath(os.path.join(self.workspace_root, rel_path))
        if not full_path.startswith(self.workspace_root):
            raise AdapterError(f"Security Violation: Path '{rel_path}' is outside workspace.")
        return full_path

    async def execute(self, args: Dict[str, Any]) -> str:
        operation = args.get("operation")
        path = args.get("path")
        content = args.get("content", "")

        if not path:
            raise AdapterError("Missing 'path' argument.")

        secure_path = self._get_secure_path(path)

        try:
            if operation == "write":
                async with aiofiles.open(secure_path, mode='w', encoding='utf-8') as f:
                    await f.write(content)
                return f"SUCCESS: Wrote {len(content)} chars to {path}"
            
            elif operation == "read":
                if not os.path.exists(secure_path):
                    raise AdapterError(f"File not found: {path}")
                async with aiofiles.open(secure_path, mode='r', encoding='utf-8') as f:
                    data = await f.read()
                return data
            
            elif operation == "list":
                if os.path.isdir(secure_path):
                    return "\n".join(os.listdir(secure_path))
                return f"{path} is not a directory."
            
            else:
                raise AdapterError(f"Unknown operation: {operation}")
                
        except Exception as e:
            raise AdapterError(f"FileSystem Error: {str(e)}")
