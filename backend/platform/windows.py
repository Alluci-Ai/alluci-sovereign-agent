import os
import sys
import subprocess
from ..logging_config import get_logger
import platform
from typing import Dict, Any

logger = get_logger("WindowsPlatform")

class WindowsPlatform:
    """
    Handles Windows-specific platform integrations, primarily Windows Service 
    installation using pywin32 or sc.exe.
    """
    
    SERVICE_NAME = "AlluciDaemon"
    DISPLAY_NAME = "Alluci Sovereign Agent"
    DESCRIPTION = "Sovereign AI node for unified messaging and automation."

    @classmethod
    def is_windows(cls) -> bool:
        return platform.system() == "Windows"

    def install_service(self) -> Dict[str, Any]:
        """Registers the python script as a Windows service."""
        if not self.is_windows():
            return {"status": "error", "message": "Not a Windows system."}

        working_dir = os.getcwd()
        python_executable = sys.executable
        app_entry = os.path.join(working_dir, "backend", "app.py")
        
        # We'll use sc.exe for simplicity across standard Python installs
        # NSSM or pywin32 are alternatives but sc is built-in.
        # Note: sc create requires admin privileges.
        
        try:
            # Check if service already exists
            check_res = subprocess.run(["sc", "query", self.SERVICE_NAME], capture_output=True)
            if check_res.returncode == 0:
                subprocess.run(["sc", "stop", self.SERVICE_NAME], capture_output=True)
                subprocess.run(["sc", "delete", self.SERVICE_NAME], capture_output=True)

            cmd = [
                "sc", "create", self.SERVICE_NAME,
                f"binPath= \"{python_executable}\" \"{app_entry}\"",
                "DisplayName=", self.DISPLAY_NAME,
                "start=", "auto",
                "obj=", "LocalSystem"
            ]
            
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                subprocess.run(["sc", "description", self.SERVICE_NAME, self.DESCRIPTION], capture_output=True)
                subprocess.run(["sc", "start", self.SERVICE_NAME], capture_output=True)
                logger.info(f"Windows Service {self.SERVICE_NAME} installed.")
                return {"status": "success", "message": "Windows Service installed successfully."}
            else:
                return {"status": "error", "message": f"sc create failed: {res.stderr}"}
                
        except Exception as e:
            logger.error(f"Failed to install Windows service: {e}")
            return {"status": "error", "message": str(e)}

    def uninstall_service(self) -> Dict[str, Any]:
        """Stops and deletes the Windows service."""
        if not self.is_windows():
            return {"status": "error", "message": "Not a Windows system."}

        try:
            subprocess.run(["sc", "stop", self.SERVICE_NAME], capture_output=True)
            res = subprocess.run(["sc", "delete", self.SERVICE_NAME], capture_output=True, text=True)
            if res.returncode == 0:
                return {"status": "success", "message": "Service uninstalled successfully."}
            else:
                return {"status": "error", "message": f"sc delete failed: {res.stderr}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_service_status(self) -> Dict[str, Any]:
        """Queries service status via sc."""
        if not self.is_windows():
            return {"status": "unsupported"}
            
        res = subprocess.run(["sc", "query", self.SERVICE_NAME], capture_output=True, text=True)
        if "RUNNING" in res.stdout:
            return {"status": "running"}
        elif "STOPPED" in res.stdout:
            return {"status": "stopped"}
        else:
            return {"status": "not_installed"}
