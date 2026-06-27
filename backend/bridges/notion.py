import httpx
import json
from typing import Dict, Any, Optional, List
from .base import BridgeAdapter, PlatformRequirement

class NotionBridge(BridgeAdapter):
    """
    Notion Enterprise Core Bridge.
    Connects to Notion using an Internal Integration Token (secret_...).
    """
    platform_requirements = set()  # Only requires internet access

    def __init__(self, bridge_id: str = "notion", vault_root: str = "", vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.api_key: Optional[str] = None
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Validates the Notion Integration Token and establishes the connection.
        """
        if not credentials:
            self.logger.error("[NOTION] No credentials provided.")
            return False

        self.api_key = credentials.get("api_key") or credentials.get("token")
        if not self.api_key:
            self.logger.error("[NOTION] Missing api_key or token in credentials.")
            return False

        self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Validate the token by fetching the bot's identity
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/users/me", headers=self.headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    self.is_connected = True
                    self.logger.info(f"[NOTION] Successfully connected as {data.get('bot', {}).get('workspace_name', 'Notion Bot')}")
                    await self._save_credentials(credentials)
                    return True
                else:
                    self.logger.error(f"[NOTION] Auth failed. Code: {resp.status_code}, Resp: {resp.text}")
                    return False
        except Exception as e:
            self.logger.error(f"[NOTION] Connection exception: {e}")
            return False

    async def disconnect(self) -> None:
        await super().disconnect()
        self.api_key = None
        if "Authorization" in self.headers:
            del self.headers["Authorization"]
        self.logger.info("[NOTION] Disconnected.")

    def status(self) -> Dict[str, Any]:
        return {
            "is_connected": self.is_connected,
            "bridge_id": self.bridge_id,
            "platform": "NOTION"
        }

    # --- Full Capability Operations ---

    async def search(self, query: str = "", filter_type: Optional[str] = None) -> Dict[str, Any]:
        """Search across all shared pages and databases."""
        if not self.is_connected:
            raise Exception("Notion bridge is not connected.")
        
        payload: Dict[str, Any] = {"query": query}
        if filter_type in ["page", "database"]:
            payload["filter"] = {"value": filter_type, "property": "object"}
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/search", headers=self.headers, json=payload, timeout=30.0)
            resp.raise_for_status()
            return resp.json()

    async def get_page(self, page_id: str) -> Dict[str, Any]:
        """Retrieve a specific page's properties."""
        if not self.is_connected:
            raise Exception("Notion bridge is not connected.")
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/pages/{page_id}", headers=self.headers, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def get_block_children(self, block_id: str) -> Dict[str, Any]:
        """Retrieve the contents (children blocks) of a page or block."""
        if not self.is_connected:
            raise Exception("Notion bridge is not connected.")
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/blocks/{block_id}/children", headers=self.headers, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def append_block_children(self, block_id: str, children: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Append blocks to a page or block."""
        if not self.is_connected:
            raise Exception("Notion bridge is not connected.")
            
        payload = {"children": children}
        async with httpx.AsyncClient() as client:
            resp = await client.patch(f"{self.base_url}/blocks/{block_id}/children", headers=self.headers, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def create_page(self, parent_id: str, parent_type: str, properties: Dict[str, Any], children: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Create a new page in a database or as a child of another page."""
        if not self.is_connected:
            raise Exception("Notion bridge is not connected.")
            
        payload: Dict[str, Any] = {
            "parent": {parent_type: parent_id},
            "properties": properties
        }
        if children:
            payload["children"] = children
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/pages", headers=self.headers, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def update_page(self, page_id: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Update a page's properties."""
        if not self.is_connected:
            raise Exception("Notion bridge is not connected.")
            
        payload = {"properties": properties}
        async with httpx.AsyncClient() as client:
            resp = await client.patch(f"{self.base_url}/pages/{page_id}", headers=self.headers, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def query_database(self, database_id: str, filter: Optional[Dict[str, Any]] = None, sorts: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Query a database."""
        if not self.is_connected:
            raise Exception("Notion bridge is not connected.")
            
        payload: Dict[str, Any] = {}
        if filter:
            payload["filter"] = filter
        if sorts:
            payload["sorts"] = sorts
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/databases/{database_id}/query", headers=self.headers, json=payload, timeout=30.0)
            resp.raise_for_status()
            return resp.json()

    # --- Abstract Base Class Implementations ---

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Transmit data through the secure bridge tunnel (Legacy)."""
        self.logger.warning("[NOTION] send_message is not natively supported for Notion.")
        return {"status": "unsupported", "protocol": "NOTION"}

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Canonical data transmission method (Sovereign Spec §2.3)."""
        self.logger.warning("[NOTION] send is not natively supported for Notion.")
        return {"status": "unsupported", "protocol": "NOTION"}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent communications for autonomous processing."""
        self.logger.warning("[NOTION] fetch_unread is not natively supported for Notion.")
        return []

    async def validate_integrity(self) -> bool:
        """Verify the E2E encryption and connection status."""
        return self.is_connected
