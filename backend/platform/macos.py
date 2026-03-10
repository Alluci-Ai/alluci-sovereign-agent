import os
import subprocess
import logging
import platform
from typing import Dict, Any

logger = logging.getLogger("MacOSPlatform")

class MacOSPlatform:
    """
    Handles macOS-specific platform integrations, primarily launchd service 
    installation and management for background daemon operation.
    """
    
    SERVICE_NAME = "com.alluci.daemon"
    PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{SERVICE_NAME}.plist")

    @classmethod
    def is_macos(cls) -> bool:
        return platform.system() == "Darwin"

    def get_plist_content(self) -> str:
        """Generates the launchd plist content based on current execution environment."""
        working_dir = os.getcwd()
        python_executable = os.path.abspath(subprocess.check_output(["which", "python3"]).decode().strip())
        app_entry = os.path.join(working_dir, "backend/app.py")
        
        # Ensure log directory exists
        log_dir = os.path.expanduser("~/.alluci/logs")
        os.makedirs(log_dir, exist_ok=True)

        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{self.SERVICE_NAME}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_executable}</string>
        <string>{app_entry}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
    <key>StandardOutPath</key>
    <string>{log_dir}/daemon.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>{log_dir}/daemon.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>{os.environ.get('PATH', '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin')}</string>
        <key>PYTHONPATH</key>
        <string>{working_dir}</string>
        <key>APP_ENV</key>
        <string>production</string>
    </dict>
</dict>
</plist>
"""
        return plist

    def install_service(self) -> Dict[str, Any]:
        """Writes the plist and attempts to load it via launchctl."""
        if not self.is_macos():
            return {"status": "error", "message": "Not a macOS system."}

        try:
            content = self.get_plist_content()
            os.makedirs(os.path.dirname(self.PLIST_PATH), exist_ok=True)
            
            with open(self.PLIST_PATH, "w") as f:
                f.write(content)
            
            # Load the service
            subprocess.run(["launchctl", "unload", self.PLIST_PATH], capture_output=True) # Unload if exists
            res = subprocess.run(["launchctl", "load", "-w", self.PLIST_PATH], capture_output=True, text=True)
            
            if res.returncode == 0:
                logger.info(f"Service {self.SERVICE_NAME} installed and loaded.")
                return {"status": "success", "message": "Service installed successfully."}
            else:
                return {"status": "error", "message": f"launchctl failed: {res.stderr}"}
                
        except Exception as e:
            logger.error(f"Failed to install service: {e}")
            return {"status": "error", "message": str(e)}

    def uninstall_service(self) -> Dict[str, Any]:
        """Unloads the service and removes the plist file."""
        if not self.is_macos():
            return {"status": "error", "message": "Not a macOS system."}

        try:
            subprocess.run(["launchctl", "unload", self.PLIST_PATH], capture_output=True)
            if os.path.exists(self.PLIST_PATH):
                os.remove(self.PLIST_PATH)
            return {"status": "success", "message": "Service uninstalled successfully."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_service_status(self) -> Dict[str, Any]:
        """Checks if the service is currently managed by launchctl."""
        if not self.is_macos():
            return {"status": "unsupported"}
            
        res = subprocess.run(["launchctl", "list", self.SERVICE_NAME], capture_output=True, text=True)
        if res.returncode == 0:
            return {"status": "running", "details": res.stdout}
        else:
            return {"status": "not_loaded"}
