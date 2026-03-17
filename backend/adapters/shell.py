
import subprocess
import logging
from ..logging_config import get_logger
from typing import Dict, Any
from .base import Adapter

logger = get_logger("Adapters.Shell")

class ShellAdapter(Adapter):
    @property
    def name(self) -> str:
        return "shell"

    SHELL_DENYLIST = {
        "rm", "mkfs", "dd", "format", "shred", "fdisk", "parted",
        "shutdown", "reboot", "halt", "poweroff", "init", "systemctl",
        "chmod", "chown", "passwd", "useradd", "userdel", "groupadd",
        "visudo", "mv", "cp", "wget", "curl"
    }

    async def execute(self, args: Dict[str, Any]) -> Any:
        command = args.get("command", "")
        if not command:
            return "No command provided."
        
        # 1. Security Check: Denylist
        cmd_base = command.split()[0].split("/")[-1] if command else ""
        if cmd_base in self.SHELL_DENYLIST:
            return f"Error: Command '{cmd_base}' is denylisted for security."
        
        # 2. Resource Limits & Timeout (Max 120s)
        timeout = min(args.get("timeout", 30), 120)
        
        def preexec():
            # Import inside preexec for isolation if needed
            import resource
            # CPU time limit (soft, hard) in seconds
            resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 5))
            # Memory limit (soft, hard) in bytes (e.g., 512MB)
            mem_limit = 512 * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))

        try:
            # P1-005: Resource Limits implemented via preexec_fn and timeout
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=preexec if hasattr(os, "setpgrp") else None
            )
            stdout, stderr = process.communicate(timeout=timeout)
            
            if process.returncode == 0:
                return stdout or "Command executed successfully (no output)."
            else:
                return f"Error ({process.returncode}): {stderr}"
        except subprocess.TimeoutExpired:
            process.kill()
            return f"Command timed out after {timeout} seconds."
        except Exception as e:
            return f"Shell execution failed: {str(e)}"
