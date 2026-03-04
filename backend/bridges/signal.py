import subprocess
import asyncio
import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter

# Default path for signal-cli binary (assumed to be in PATH)
# Reference: OpenClaw Section 2.3 - Native Subprocess Adapters
SIGNAL_CLI_BIN = "signal-cli"

class SignalBridge(BridgeAdapter):
    """
    Sovereign Signal Bridge via signal-cli subprocess adapter.
    Implements E2EE messaging within an isolated Simplicial Vault.
    Overrides REST-based stubs for direct binary execution.
    """

    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.phone_number: str = ""
        # The configuration for signal-cli is ENTIRELY contained within the vault_path.
        # This ensures that one bridge's state cannot leak to another.
        self.config_dir = os.path.join(self.vault_path, "signal_state")
        os.makedirs(self.config_dir, mode=0o700, exist_ok=True)
        self.logger = logging.getLogger(f"Bridge_SIGNAL")

    async def _run_command(self, args: List[str], timeout: int = 30) -> Dict[str, Any]:
        """Executes signal-cli with isolated config via subprocess."""
        cmd = [SIGNAL_CLI_BIN, "--config", self.config_dir] + args
        try:
            self.logger.debug(f"[ SIGNAL ] Executing: {' '.join(cmd)}")
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            
            return {
                "returncode": proc.returncode,
                "stdout": stdout.decode().strip(),
                "stderr": stderr.decode().strip()
            }
        except Exception as e:
            self.logger.error(f"[ SIGNAL ] Execution Error: {e}")
            return {"returncode": -1, "stdout": "", "stderr": str(e)}

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to the Signal account managed in the vault.
        Expected credentials: {"phone_number": "+1..."}
        """
        self.phone_number = credentials.get("phone_number", "")
        if not self.phone_number:
            self.logger.error("[ SIGNAL ] Phone number missing from credentials.")
            return False

        # Verify registration status in the isolated vault
        res = await self._run_command(["listAccounts"])
        if res["returncode"] == 0 and self.phone_number in res.get("stdout", ""):
            self.is_connected = True
            self.logger.info(f"[ SIGNAL ] Secured connection for {self.phone_number}")
            return True
        
        self.logger.warning(f"[ SIGNAL ] Account {self.phone_number} not found in isolated vault.")
        return False

    async def register(self, phone_number: str, use_voice: bool = False) -> Dict[str, Any]:
        """Starts the Signal registration process via SMS or Voice."""
        args = ["-a", phone_number, "register"]
        if use_voice:
            args.append("--voice")
        
        res = await self._run_command(args, timeout=60)
        if res["returncode"] == 0:
            return {"status": "pending", "message": "Verification code requested via SMS/Voice."}
        return {"status": "error", "message": res["stderr"] or res["stdout"]}

    async def verify(self, phone_number: str, code: str) -> Dict[str, Any]:
        """Completes registration with the received SMS/Voice code."""
        res = await self._run_command(["-a", phone_number, "verify", code])
        if res["returncode"] == 0:
            self.phone_number = phone_number
            self.is_connected = True
            return {"status": "success", "message": f"Account {phone_number} successfully anchored."}
        return {"status": "error", "message": res["stderr"] or res["stdout"]}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Legacy shim for BridgeAdapter compatibility."""
        return await self.send(recipient, content)

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Canonical data transmission method.
        Supports individual recipients, group IDs, and file attachments.
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        attachments = kwargs.get("attachments", [])
        group_id = kwargs.get("group_id")
        
        args = ["-a", self.phone_number, "send"]
        
        if attachments:
            for attachment in attachments:
                if os.path.exists(attachment):
                    args.extend(["-a", attachment])
                else:
                    self.logger.warning(f"[ SIGNAL ] Attachment not found: {attachment}")
        
        if group_id:
            args.extend(["-g", group_id])
        else:
            args.append(recipient)
        
        args.extend(["-m", content])

        res = await self._run_command(args)
        status = "success" if res["returncode"] == 0 else "failed"
        
        # Persist to local vault trail for auditability
        self._persist_to_vault("sent_buffer", {
            "to": group_id or recipient,
            "content": content,
            "attachments": attachments,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "error": res["stderr"] if status == "failed" else None
        })

        return {"status": status, "output": res["stdout"], "error": res["stderr"]}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Pulls unread envelopes from Signal server."""
        if not self.is_connected:
            return []
            
        res = await self._run_command(["-a", self.phone_number, "receive", "--json"])
        try:
            messages = []
            for line in res["stdout"].splitlines():
                if line.strip():
                    try:
                        msg = json.loads(line)
                        messages.append(msg)
                    except json.JSONDecodeError:
                        continue
            return messages[:limit]
        except Exception as e:
            self.logger.error(f"[ SIGNAL ] Failed to parse unread messages: {e}")
            return []

    async def validate_integrity(self) -> bool:
        if not self.phone_number:
             return False
        res = await self._run_command(["-a", self.phone_number, "listAccounts"])
        return self.phone_number in res["stdout"]

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"[ SIGNAL ] Vault Write Error: {e}")

    async def sync_groups(self) -> Dict[str, Any]:
        """Syncs group metadata with the Signal server."""
        res = await self._run_command(["-a", self.phone_number, "syncGroups"])
        return {"status": "success" if res["returncode"] == 0 else "failed", "output": res["stdout"]}
