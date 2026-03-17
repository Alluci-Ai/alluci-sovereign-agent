
import subprocess
import logging
import os
from ..logging_config import get_logger
from typing import Dict, Any
from .base import Adapter

logger = get_logger("Adapters.Shell")

# Commands blocked when they appear as the FIRST word (direct invocation)
SHELL_DENYLIST_FIRST_WORD = {
    "mkfs", "fdisk", "parted", "shred",
    "shutdown", "reboot", "halt", "poweroff", "init",
    "useradd", "userdel", "groupadd", "visudo",
    "passwd",
}

# Patterns blocked anywhere in the command string (substring match, case-insensitive)
SHELL_DENYLIST_PATTERNS = [
    "rm -rf /",
    "rm -rf ~",
    "rm -fr /",
    "rm -fr ~",
    "rm --no-preserve-root",
    "> /dev/sda",
    "> /dev/nvme",
    "dd if=/dev/zero",
    "dd if=/dev/urandom of=/dev/",
    ":(){ :|:& };:",
    ":(){",
    "fork bomb",
    "wget -O- | sh",
    "wget -O- | bash",
    "curl -s | sh",
    "curl -s | bash",
    "curl | sh",
    "curl | bash",
    "chmod -R 777 /",
    "chmod 777 /",
    "echo '' > /etc/passwd",
    "cat /etc/shadow",
    "cat ~/.polytope",
    "cat ~/.ssh/id",
    "> /etc/",
    "truncate -s 0 /etc/",
    # Interpreter-wrapped dangerous commands
    "bash -c \"rm",
    "bash -c 'rm",
    "sh -c \"rm",
    "sh -c 'rm",
    "python3 -c \"import os",
    "python -c \"import os",
    "perl -e \"system",
    "ruby -e \"system",
]

class ShellAdapter(Adapter):
    @property
    def name(self) -> str:
        return "shell"

    async def execute(self, args: Dict[str, Any]) -> Any:
        command = args.get("command", "")
        if not command:
            return "No command provided."

        command = str(command).strip()
        
        # Security Check 1: First-word blocklist
        cmd_base = command.split()[0].split("/")[-1] if command.split() else ""
        if cmd_base in SHELL_DENYLIST_FIRST_WORD:
            logger.warning(f"ShellAdapter BLOCKED first-word: '{cmd_base}'")
            return f"Error: Command '{cmd_base}' is blocked by security policy."

        # Security Check 2: Substring pattern blocklist (catches interpreter wrapping)
        cmd_lower = command.lower()
        for pattern in SHELL_DENYLIST_PATTERNS:
            if pattern.lower() in cmd_lower:
                logger.warning(f"ShellAdapter BLOCKED pattern: '{pattern}'")
                return f"Error: Command matches blocked pattern: '{pattern}'"
        
        # 3. Resource Limits & Timeout (Max 120s)
        timeout = min(int(args.get("timeout", 30)), 120)
        
        def preexec():
            # Import inside preexec for isolation if needed
            import resource
            try:
                # CPU time limit (soft, hard) in seconds
                resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 5))
                # Memory limit (soft, hard) in bytes (e.g., 512MB)
                mem_limit = 512 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
            except Exception as e:
                logging.debug(f"[PREEXEC] Failed to set resource limits: {e}")

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
