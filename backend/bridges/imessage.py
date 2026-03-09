import os
import json
import subprocess
import platform
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter

class IMessageBridge(BridgeAdapter):
    """
    Sovereign iMessage Bridge for macOS.
    Utilizes osascript (AppleScript) for automated messaging and 
    local SQLite (chat.db) for message retrieval.
    
    Reference: Sovereign Spec Section 2.3 - Native OS Adapters
    """

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.system = platform.system()
        self.is_macos = self.system == "Darwin"
        self.last_error = None
        
        if not self.is_macos:
            self.logger.warning(f"[ IMESSAGE ] Gracefully disabled. Detected platform: {self.system}")

    async def check_permission(self) -> Dict[str, Any]:
        """Probes macOS for the three required permissions."""
        if not self.is_macos:
            return {"error": "macOS required"}
            
        chat_db = os.path.expanduser('~/Library/Messages/chat.db')
        fda = os.access(chat_db, os.R_OK)
        
        try:
            res = subprocess.run(['osascript', '-e', 'tell application "Messages" to return name'], capture_output=True, text=True, timeout=3)
            auto_msg = (res.returncode == 0)
        except Exception:
            auto_msg = False
            
        try:
            res = subprocess.run(['osascript', '-e', 'tell application "Contacts" to return name'], capture_output=True, text=True, timeout=3)
            contacts = (res.returncode == 0)
        except Exception:
            contacts = False

        return {
            "full_disk_access": fda,
            "automation_messages": auto_msg,
            "contacts": contacts,
            "all_granted": fda and auto_msg and contacts
        }

    async def connect(self, credentials: Dict[str, Any] = None) -> bool:
        """
        Verifies environment readiness for iMessage integration.
        Requires terminal/app to have 'Full Disk Access', 'Automation', and 'Contacts' permissions on macOS.
        """
        if not self.is_macos:
            self.last_error = "iMessage Bridge requires Apple macOS hardware."
            return False

        perms = await self.check_permission()
        if dict(perms).get("all_granted"):
            self.is_connected = True
            self.logger.info("[ IMESSAGE ] Bridge anchored to local Messages.app")
            return True
            
        self.last_error = "Missing required permissions. Check Privacy & Security settings."
        self.logger.error(f"[ IMESSAGE ] {self.last_error}")
        return False

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Legacy shim for BridgeAdapter compatibility."""
        return await self.send(recipient, content)

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Injects an iMessage send command via AppleScript.
        'recipient' can be a phone number or email address.
        """
        if not self.is_connected:
            return {"status": "failed", "error": self.last_error or "Bridge Disconnected"}

        # Sanitize content for AppleScript (escape double quotes)
        safe_content = content.replace('"', '\\"')
        
        # AppleScript for sending iMessage
        script = f'''
        tell application "Messages"
            set targetService to 1st service whose service type = iMessage
            set targetBuddy to buddy "{recipient}" of targetService
            send "{safe_content}" to targetBuddy
        end tell
        '''
        
        try:
            self.logger.debug(f"[ IMESSAGE ] Sending to {recipient}")
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=10)
            
            status = "success" if res.returncode == 0 else "failed"
            timestamp = datetime.now(timezone.utc).isoformat()
            
            self._persist_to_vault("sent_buffer", {
                "to": recipient,
                "content": content,
                "status": status,
                "timestamp": timestamp,
                "error": res.stderr.strip() if status == "failed" else None
            })
            
            return {
                "status": status, 
                "stdout": res.stdout.strip(), 
                "stderr": res.stderr.strip()
            }
        except Exception as e:
            self.logger.error(f"[ IMESSAGE ] Execution Exception: {e}")
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Attempts to read recent messages from the local chat.db.
        Requires 'Full Disk Access' for the parent process.
        """
        if not self.is_macos: return []
        
        db_path = os.path.expanduser("~/Library/Messages/chat.db")
        if not os.path.exists(db_path):
            self.logger.debug("[ IMESSAGE ] chat.db not found (likely no FDA permissions)")
            return []

        # We use sqlite3 via subprocess to pull recent messages
        # Reference: Sovereign Spec Section 2.3.2 - Local DB Extraction
        query = f"""
        SELECT 
            message.guid, 
            handle.id as sender, 
            message.text, 
            message.date / 1000000000 + 978307200 as ts
        FROM message 
        JOIN handle ON message.handle_id = handle.ROWID 
        WHERE message.is_from_me = 0 
        ORDER BY message.date DESC 
        LIMIT {limit};
        """
        
        try:
            # Using sqlite3 binary directly for performance and simplicity
            res = subprocess.run(["sqlite3", db_path, "-json", query], capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                raw_messages = json.loads(res.stdout)
                processed = []
                for msg in raw_messages:
                    processed.append({
                        "id": msg.get("guid"),
                        "from": msg.get("sender"),
                        "body": msg.get("text"),
                        "protocol": "IMESSAGE",
                        "timestamp": datetime.fromtimestamp(msg.get("ts"), tz=timezone.utc).isoformat()
                    })
                return processed
            return []
        except Exception as e:
            self.logger.debug(f"[ IMESSAGE ] SQLite read failed (Permissions?): {e}")
            return []

    async def validate_integrity(self) -> bool:
        if not self.is_macos: return False
        return self.is_connected

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"[ IMESSAGE ] Vault Write Error: {e}")

    def get_health(self) -> Dict[str, Any]:
        status_msg = "Operational (macOS Native)" if self.is_connected else "Platform Mismatch / Missing Permissions"
        if not self.is_macos:
            status_msg = f"Disabled (Detected: {self.system})"
            
        return {
            "channel": "imessage",
            "connected": self.is_connected,
            "platform": self.system,
            "status_message": status_msg,
            "last_error": self.last_error
        }
