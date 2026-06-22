import os
import subprocess
from ..logging_config import get_logger
import platform
from typing import Dict, Any

logger = get_logger("LinuxPlatform")

class LinuxPlatform:
    """
    Handles Linux-specific platform integrations, primarily systemd user 
    service installation and management for background daemon operation.
    """
    
    SERVICE_NAME = "alluci"
    UNIT_FILE_NAME = f"{SERVICE_NAME}.service"
    SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")
    UNIT_PATH = os.path.join(SYSTEMD_USER_DIR, UNIT_FILE_NAME)

    @classmethod
    def is_linux(cls) -> bool:
        return platform.system() == "Linux"

    def get_unit_content(self) -> str:
        """Generates the systemd user unit content."""
        working_dir = os.getcwd()
        python_executable = os.path.abspath(subprocess.check_output(["which", "python3"]).decode().strip())
        app_entry = os.path.join(working_dir, "backend/app.py")
        
        # Ensure log directory exists
        log_dir = os.path.expanduser("~/.alluci/logs")
        os.makedirs(log_dir, exist_ok=True)

        unit = f"""[Unit]
Description=Alluci Sovereign Agent Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory={working_dir}
ExecStart={python_executable} {app_entry}
Restart=always
RestartSec=5
StandardOutput=file:{log_dir}/daemon.stdout.log
StandardError=file:{log_dir}/daemon.stderr.log

[Install]
WantedBy=default.target
"""
        return unit

    def install_service(self) -> Dict[str, Any]:
        """Writes the unit file and enables/starts it via systemctl."""
        if not self.is_linux():
            return {"status": "error", "message": "Not a Linux system."}

        try:
            content = self.get_unit_content()
            os.makedirs(self.SYSTEMD_USER_DIR, exist_ok=True)
            
            with open(self.UNIT_PATH, "w") as f:
                f.write(content)
            
            # Reload, enable, and start the service
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", self.UNIT_FILE_NAME], capture_output=True)
            res = subprocess.run(["systemctl", "--user", "restart", self.UNIT_FILE_NAME], capture_output=True, text=True)
            
            if res.returncode == 0:
                logger.info(f"Service {self.SERVICE_NAME} installed and started.")
                return {"status": "success", "message": "Service installed successfully via systemd."}
            else:
                return {"status": "error", "message": f"systemctl failed: {res.stderr}"}
                
        except Exception as e:
            logger.error(f"Failed to install systemd service: {e}")
            return {"status": "error", "message": str(e)}

    def uninstall_service(self) -> Dict[str, Any]:
        """Stops, disables, and removes the systemd unit file."""
        if not self.is_linux():
            return {"status": "error", "message": "Not a Linux system."}

        try:
            subprocess.run(["systemctl", "--user", "stop", self.UNIT_FILE_NAME], capture_output=True)
            subprocess.run(["systemctl", "--user", "disable", self.UNIT_FILE_NAME], capture_output=True)
            if os.path.exists(self.UNIT_PATH):
                os.remove(self.UNIT_PATH)
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            return {"status": "success", "message": "Service uninstalled successfully from systemd."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_service_status(self) -> Dict[str, Any]:
        """Checks the status of the systemd service."""
        if not self.is_linux():
            return {"status": "unsupported"}
            
        res = subprocess.run(["systemctl", "--user", "is-active", self.UNIT_FILE_NAME], capture_output=True, text=True)
        is_active = res.stdout.strip() == "active"
        
        status_res = subprocess.run(["systemctl", "--user", "status", self.UNIT_FILE_NAME], capture_output=True, text=True)
        
        return {
            "status": "running" if is_active else "stopped",
            "details": status_res.stdout
        }
