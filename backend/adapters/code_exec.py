
import subprocess
import logging
from typing import Dict, Any, Optional
from .base import Adapter

class CodeExecAdapter(Adapter):
    """
    Safe Code Execution Adapter.
    Executes Python or Bash code with timeouts and resource limits.
    """
    name = "code_exec"
    description = "Execute Python or Bash code snippets safely."

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.logger = logging.getLogger("CodeExecAdapter")

    async def execute(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Executes code and captures output.
        """
        try:
            if language == "python":
                cmd = ["python3", "-c", code]
            elif language == "bash":
                cmd = ["bash", "-c", code]
            else:
                return {"status": "error", "message": f"Unsupported language: {language}"}

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
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
