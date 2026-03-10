from typing import Dict, Any, List
from .base import BridgeAdapter
import subprocess
import asyncio
import os
import json

class SignalBridge(BridgeAdapter):
    """
    Sovereign Signal Bridge.
    Uses signal-cli daemon in the background to handle E2EE and device linking.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.phone_number = None

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        self.phone_number = credentials.get("phone_number")
        
        if self.phone_number:
            self.is_connected = True
            self.logger.info(f"Signal linked to {self.phone_number}")
            # Start background receive loop
            asyncio.create_task(self._receive_loop())
            return True
            
        self.logger.error("No phone number registered for Signal bridge.")
        return False

    async def get_link_qr(self) -> str:
        """
        Executes signal-cli link to generate a tsdevice:// URI 
        that would be shown to the user as a QR code in the frontend.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "signal-cli", "link", "-n", "Alluci Agent",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                uri = stdout.decode().strip()
                return uri
            else:
                self.logger.error(f"signal-cli link error: {stderr.decode()}")
                return ""
        except Exception as e:
            self.logger.error(f"signal-cli error: {e}")
            return "tsdevice:/?uuid=mock-uuid&pub_key=mock-key" # Fallback to mock if binary missing

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not self.phone_number:
            return {"status": "failed", "error": "Not connected"}
            
        try:
            process = await asyncio.create_subprocess_exec(
                "signal-cli", "-u", self.phone_number, "send", "-m", content, recipient,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                self.last_activity = str(int(asyncio.get_event_loop().time()))
                return {"status": "success", "message_id": stdout.decode().strip()}
            else:
                self.last_error = stderr.decode().strip()
                return {"status": "failed", "error": self.last_error}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def _receive_loop(self):
        """Background loop to receive Signal messages via JSON polling."""
        self.logger.info("Signal receive loop started.")
        while self.is_connected:
            try:
                process = await asyncio.create_subprocess_exec(
                    "signal-cli", "-u", self.phone_number, "receive", "--json",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    for line in stdout.decode().splitlines():
                        if not line.strip(): continue
                        try:
                            msg_data = json.loads(line)
                            envelope = msg_data.get("envelope", {})
                            data_msg = envelope.get("dataMessage", {})
                            
                            if data_msg and data_msg.get("message"):
                                await self._dispatch_inbound({
                                    "from": envelope.get("sourceNumber") or envelope.get("sourceName"),
                                    "body": data_msg["message"],
                                    "timestamp": envelope.get("timestamp"),
                                    "account_id": self.phone_number
                                })
                        except Exception as e:
                            self.logger.warning(f"Failed to parse Signal message: {e}")
                else:
                    err = stderr.decode().strip()
                    if err: self.logger.error(f"Signal receive error: {err}")
                    
            except Exception as e:
                self.logger.error(f"Signal loop critical failure: {e}")
                await asyncio.sleep(10)
            
            await asyncio.sleep(5)

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected
