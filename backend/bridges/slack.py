
import httpx
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from .base import BridgeAdapter

class SlackBridge(BridgeAdapter):
    """
    Production Slack Bridge using the Slack Web API.
    Adheres to Simplicial Vault Isolation by persisting all messages.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        super().__init__(bridge_id, vault_root)
        self.api_url = "https://slack.com/api"
        self.bot_token: str = ""
        self.default_channel: str = ""

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connects to Slack.
        Expected credentials: {"bot_token": "xoxb-...", "default_channel": "C12345"}
        """
        self.bot_token = credentials.get("bot_token", "")
        self.default_channel = credentials.get("default_channel", "")
        
        if not self.bot_token.startswith("xoxb-"):
            self.logger.error("Invalid Slack Bot Token format.")
            return False

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}/auth.test",
                    headers={"Authorization": f"Bearer {self.bot_token}"}
                )
                data = res.json()
                if data.get("ok"):
                    self.is_connected = True
                    self.logger.info(f"Slack Connected. Bot ID: {data.get('bot_id')} User: {data.get('user')}")
                    return True
                else:
                    self.logger.error(f"Slack auth failed: {data.get('error')}")
                    return False
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """
        Sends a message to a Slack channel/user and logs it to the vault.
        If recipient is None, defaults to self.default_channel.
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Bridge Disconnected"}

        target = recipient if recipient else self.default_channel
        if not target:
             return {"status": "failed", "error": "No recipient specified"}

        timestamp = datetime.now().isoformat()
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}/chat.postMessage",
                    headers={"Authorization": f"Bearer {self.bot_token}"},
                    json={"channel": target, "text": content}
                )
                data = res.json()
                
                status = "success" if data.get("ok") else "failed"
                
                # Vault Persistence
                self._persist_to_vault("sent", {
                    "channel": target,
                    "content": content,
                    "status": status,
                    "slack_ts": data.get("ts"),
                    "timestamp": timestamp,
                    "error": data.get("error")
                })

                if data.get("ok"):
                    return {"status": "success", "ts": data.get("ts")}
                else:
                    return {"status": "failed", "error": data.get("error")}
        except Exception as e:
            # Log failure to vault
            self._persist_to_vault("sent", {
                "channel": target,
                "content": content,
                "status": "exception",
                "timestamp": timestamp,
                "error": str(e)
            })
            return {"status": "failed", "error": str(e)}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetches history from the default channel if configured.
        """
        if not self.is_connected or not self.default_channel:
            return []
            
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}/conversations.history",
                    headers={"Authorization": f"Bearer {self.bot_token}"},
                    data={"channel": self.default_channel, "limit": limit}
                )
                data = res.json()
                if not data.get("ok"):
                    self.logger.error(f"Fetch failed: {data.get('error')}")
                    return []
                
                messages = []
                for msg in data.get("messages", []):
                    # Basic mapping
                    m = {
                        "id": msg.get("ts"),
                        "from": msg.get("user", "unknown"),
                        "body": msg.get("text", ""),
                        "timestamp": datetime.fromtimestamp(float(msg.get("ts"))).isoformat(),
                        "protocol": "SLACK"
                    }
                    messages.append(m)
                    self._persist_to_vault("inbox", m)
                    
                return messages
        except Exception as e:
            self.logger.error(f"Fetch exception: {e}")
            return []

    async def validate_integrity(self) -> bool:
        if not self.is_connected:
            return False
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(
                    f"{self.api_url}/auth.test",
                    headers={"Authorization": f"Bearer {self.bot_token}"}
                )
                return res.json().get("ok", False)
        except:
            return False

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        """
        Writes structured data to the isolated bridge vault.
        """
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"Vault Write Error: {e}")
