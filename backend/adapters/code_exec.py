
import subprocess
import logging
import os
from ..logging_config import get_logger
from typing import Dict, Any, Optional
from .base import Adapter

_CODE_DENYLIST = [
    # Filesystem destruction
    "os.system",
    "subprocess.run",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_output",
    # Privilege escalation
    "os.setuid",
    "os.setgid",
    "ctypes.CDLL",
    # Secret access
    "__import__('os').environ",
    "open('/etc/shadow",
    "open('/root/.ssh",
    "open('/home/",
    # Network exfiltration
    "urllib.request.urlopen",
    "httpx.get",
    "httpx.post",
    "requests.get",
    "requests.post",
    # Arbitrary module loading
    "__import__",
    "importlib.import_module",
    "exec(",
    "eval(",
    "compile(",
]

class CodeExecAdapter(Adapter):
    """
    Safe Code Execution Adapter.
    Executes Python or Bash code with timeouts and resource limits.
    """
    name = "code_exec"
    description = "Execute Python or Bash code snippets safely."

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.logger = get_logger("CodeExecAdapter")

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes code and captures output.
        """
        code = args.get("code", "")
        language = args.get("language", "python")

        if not str(code).strip():
            return {"status": "error", "message": "No code provided in args['code']."}

        code = str(code)

        # Security: block dangerous patterns
        code_lower = code.lower().replace(" ", "")  # strip spaces to catch obfuscation
        for pattern in _CODE_DENYLIST:
            if pattern.lower().replace(" ", "") in code_lower:
                self.logger.warning(f"CodeExec BLOCKED: matched pattern '{pattern}'")
                return {
                    "status": "error",
                    "message": f"Code execution blocked: matched security pattern '{pattern}'.",
                }

        try:
            if language == "python":
                cmd = ["python3", "-c", code]
            elif language == "bash":
                cmd = ["bash", "-c", code]
            else:
                return {"status": "error", "message": f"Unsupported language: {language}"}

            def preexec():
                import resource
                # Max 512 MB virtual memory
                mem_limit = 512 * 1024 * 1024
                try:
                    resource.setrlimit(resource.RLIMIT_AS, (mem_limit, mem_limit))
                except Exception as e:
                    logging.debug(f"[PREEXEC] Failed to set RLIMIT_AS: {e}")
                # Max CPU time
                try:
                    resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout + 5))
                except Exception as e:
                    logging.debug(f"[PREEXEC] Failed to set RLIMIT_CPU: {e}")

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=preexec if hasattr(os, "setpgrp") else None
            )
            
            stdout, stderr = process.communicate(timeout=self.timeout)
            
            return {
                "status": "success" if process.returncode == 0 else "error",
                "return_code": process.returncode,
                "stdout": stdout,
                "stderr": stderr
            }
        except subprocess.TimeoutExpired:
            process.kill()
            return {"status": "error", "message": "Execution timed out"}
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            return {"status": "error", "message": str(e)}
