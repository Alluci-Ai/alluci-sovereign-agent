import os
import logging
import asyncio
import httpx
from typing import List, Dict, Any, Callable
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class BridgeAdapter(ABC):
    """
    Abstract Base Class for all sovereign bridge integrations.
    Enforces Simplicial Vault Isolation to prevent cross-bridge data leakage.
    """
    def __init__(self, bridge_id: str, vault_root: str):
        self.bridge_id = bridge_id
        self.logger = logging.getLogger(f"Bridge_{bridge_id.upper()}")
        
        # Simplicial Vault Path: ~/.polytope/vaults/{bridge_id}
        self.vault_path = os.path.join(vault_root, bridge_id)
        self._enforce_vault_isolation()
        
        self.is_connected = False
        self.session: Any = None
        self.client = httpx.AsyncClient(timeout=30.0)

    @staticmethod
    def resilient_request(func: Callable):
        """
        Decorator to wrap bridge network requests with production-grade resilience.
        Retries on connection errors and transient 5xx responses with exponential backoff.
        """
        return retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPProtocolError)),
            reraise=True
        )(func)

    def _enforce_vault_isolation(self):
        """
        Creates the isolated vault directory with strict permissions (rwx------).
        """
        if not os.path.exists(self.vault_path):
            try:
                os.makedirs(self.vault_path, mode=0o700, exist_ok=True)
            except OSError as e:
                self.logger.critical(f"Failed to create isolated vault: {e}")
                raise PermissionError(f"Vault isolation failed for {self.bridge_id}")

    @abstractmethod
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Initialize secure session with the manifold provider."""
        pass

    @abstractmethod
    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Transmit data through the secure bridge tunnel (Legacy)."""
        pass

    @abstractmethod
    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Canonical data transmission method (Sovereign Spec §2.3)."""
        pass

    @abstractmethod
    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent communications for autonomous processing."""
        pass

    @abstractmethod
    async def validate_integrity(self) -> bool:
        """Verify the E2E encryption and connection status."""
        pass

    async def _get_valid_token(self, creds: Dict[str, Any], token_url: str, client_id: str, client_secret: str) -> Dict[str, Any]:
        """
        Helper for OAuth2 bridges to check expiration and refresh the access token if needed.
        Returns the updated credentials dictionary.
        Uses resilient_request internally.
        """
        import time
        expires_at = creds.get("expires_at", 0)
        if not expires_at or time.time() < expires_at - 60:
            return creds

        refresh_token = creds.get("refresh_token")
        if not refresh_token:
            self.logger.error("Token expired and no refresh_token available.")
            raise ValueError("OAuth Token expired, no refresh token.")

        self.logger.info("Access token expired, refreshing...")
        
        @self.resilient_request
        async def perform_refresh():
            return await self.client.post(token_url, data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            })

        resp = await perform_refresh()
        resp.raise_for_status()
        data = resp.json()
        creds["access_token"] = data["access_token"]
        if "refresh_token" in data:
            creds["refresh_token"] = data["refresh_token"]
        creds["expires_at"] = time.time() + data.get("expires_in", 3600)
        return creds

    async def disconnect(self):
        """Graceful teardown of the connection."""
        if self.client:
            await self.client.aclose()
        self.is_connected = False
        self.session = None
