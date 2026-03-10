
import subprocess
import logging
from typing import Dict, Any
from .base import Adapter

logger = logging.getLogger("Adapters.Shell")

class ShellAdapter(Adapter):
    @property
    def name(self) -> str:
        return "shell"

    async def execute(self, args: Dict[str, Any]) -> Any:
        command = args.get("command")
        if not command:
            return "No command provided."
        
        timeout = args.get("timeout", 30)
        
        try:
            # P1-005: Resource Limits — use subprocess with timeout
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = process.communicate(timeout=timeout)
            
            if process.returncode == 0:
                return stdout
            else:
                return f"Error ({process.returncode}): {stderr}"
        except subprocess.TimeoutExpired:
            process.kill()
            return f"Command timed out after {timeout} seconds."
        except Exception as e:
            return f"Shell execution failed: {str(e)}"
