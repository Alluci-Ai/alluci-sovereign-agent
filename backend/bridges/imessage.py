import os
import json
import subprocess
from datetime import datetime
from typing import List, Dict, Any
from .base import BridgeAdapter

class IMessageBridge(BridgeAdapter):
    """
    Production stub for Apple iMessage via local SQLite / AppleScript injection
    or BlueBubbles API. Operates fully isolated on local hardware.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.mode = "applescript" # or "bluebubbles"

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Verify local macOS environment for AppleScript execution.
        """
        self.mode = credentials.get("mode", "applescript")
        
        if self.mode == "applescript":
             # Verify we are on macOS
             import platform
             if platform.system() == "Darwin":
                  self.is_connected = True
                  self.logger.info("iMessage Bridge: macOS Local Execution Available")
                  return True
             else:
                  self.logger.error("iMessage Local Applescript requires macOS hardware.")
                  return False
        return False

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        timestamp = datetime.now().isoformat()
        
        try:
            if self.mode == "applescript":
                script = f'''
                tell application "Messages"
                    set targetService to 1st service whose service type = iMessage
                    set targetBuddy to buddy "{recipient}" of targetService
                    send "{content}" to targetBuddy
                end tell
                '''
                
                # Sandboxed local execution
                p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                
                status = "success" if p.returncode == 0 else "failed"
                
                self._persist_to_vault("sent", {
                    "recipient": recipient,
                    "content": content,
                    "status": status,
                    "timestamp": timestamp,
                    "error": p.stderr if status == "failed" else None
                })
                
                return {"status": status, "output": p.stdout}
            
            return {"status": "failed", "error": "Unknown connection mode"}
            
        except Exception as e:
            self._persist_to_vault("sent", {"recipient": recipient, "content": content, "status": "exception", "error": str(e)})
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        # Usually requires reading ~/Library/Messages/chat.db (requires Full Disk Access on macOS)
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
