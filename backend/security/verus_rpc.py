
import httpx
import logging
from typing import Any, Dict, List
from backend.config import settings

logger = logging.getLogger("VerusRPC")

class VerusRPCClient:
    """
    Async client for communicating with the verusd daemon via JSON-RPC.
    """
    def __init__(self):
        self.url = f"http://{settings.VERUS_RPC_HOST}:{settings.VERUS_RPC_PORT}"
        self.auth = None
        if settings.VERUS_RPC_USER and settings.VERUS_RPC_PASSWORD:
            self.auth = (settings.VERUS_RPC_USER, settings.VERUS_RPC_PASSWORD)
        
        self.client = httpx.AsyncClient(
            auth=self.auth,
            timeout=30.0
        )

    async def _call(self, method: str, params: List[Any] = []) -> Any:
        payload = {
            "jsonrpc": "1.0",
            "id": "alluci-agent",
            "method": method,
            "params": params
        }
        try:
            response = await self.client.post(self.url, json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("error"):
                logger.error(f"Verus RPC Error [{method}]: {result['error']}")
                raise Exception(f"Verus RPC Error: {result['error']}")
            return result.get("result")
        except httpx.HTTPStatusError as e:
            logger.error(f"Verus RPC HTTP Error [{method}]: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"Verus RPC Connection Error [{method}]: {str(e)}")
            raise

    async def get_identity(self, name_or_iaddr: str) -> Dict[str, Any]:
        """Calls getidentity RPC."""
        return await self._call("getidentity", [name_or_iaddr])

    async def sign_message(self, identity: str, message: str) -> str:
        """Calls signmessage RPC."""
        return await self._call("signmessage", [identity, message])

    async def verify_message(self, identity: str, signature: str, message: str) -> bool:
        """Calls verifymessage RPC."""
        return await self._call("verifymessage", [identity, signature, message])

    async def update_identity(self, identity_json: Dict[str, Any]) -> str:
        """Calls updateidentity RPC. Requires funded wallet for fees."""
        return await self._call("updateidentity", [identity_json])

    async def get_content_multimap(self, identity: str, key: str = "") -> Dict[str, Any]:
        """Helper to specifically extract VDXF contentmultimap data."""
        identity_data = await self.get_identity(identity)
        content_map = identity_data.get("identity", {}).get("contentmultimap", {})
        if key:
            return content_map.get(key, [])
        return content_map

    async def close(self):
        await self.client.aclose()

# Singleton instance
verus_rpc = VerusRPCClient()
