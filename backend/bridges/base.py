import os
import json
import logging
from ..logging_config import get_logger
import asyncio
import httpx
from typing import List, Dict, Any, Callable, Optional
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import platform
import sys
from enum import Enum
from typing import Set

class PlatformRequirement(str, Enum):
   """Declares what a bridge needs at the host system level."""
   MACOS         = "macos"           # Requires macOS (iMessage, iCloud)
   LINUX         = "linux"           # Requires Linux (signal-cli daemon)
   ENTERPRISE_API = "enterprise_api" # Requires paid/enterprise API access
   SIGNAL_CLI    = "signal_cli"      # Requires signal-cli binary in PATH
   DOCKER        = "docker"          # Requires Docker daemon

def get_platform_requirements_met(requirements: Set[PlatformRequirement]) -> dict:
   """
   Returns a dict of {requirement: bool} indicating which are satisfied.
   Called at bridge init to populate the status API.
   """
   import shutil
   results: Dict[PlatformRequirement, bool] = {}
   for req in requirements:
       if req == PlatformRequirement.MACOS:
           results[req] = platform.system() == "Darwin"
       elif req == PlatformRequirement.LINUX:
           results[req] = platform.system() == "Linux"  # type: ignore
       elif req == PlatformRequirement.SIGNAL_CLI:
           results[req] = shutil.which("signal-cli") is not None  # type: ignore
       elif req == PlatformRequirement.DOCKER:
           results[req] = shutil.which("docker") is not None  # type: ignore
       elif req == PlatformRequirement.ENTERPRISE_API:
           results[req] = True  # Can't check at init; verified at connect()  # type: ignore
       else:
           results[req] = False
   return results

class BridgeAdapter(ABC):
    platform_requirements: Set[PlatformRequirement] = set()
    is_officially_supported: bool = True  # False for unofficial/scraped bridges
    """
    Abstract Base Class for all sovereign bridge integrations.
    Enforces Simplicial Vault Isolation to prevent cross-bridge data leakage.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        self.bridge_id = bridge_id
        self.vault_manager = vault_manager
        self.logger = get_logger(f"Bridge_{bridge_id.upper()}")
        
        # Platform availability check
        self._platform_status = get_platform_requirements_met(self.platform_requirements)
        self.is_platform_available = all(self._platform_status.values())

        if not self.is_platform_available:
            unmet = [k.value for k, v in self._platform_status.items() if not v]
            self.logger.warning(
                f"[{bridge_id.upper()}] Bridge UNAVAILABLE on this platform. "
                f"Unmet requirements: {unmet}"
            )
        
        # Simplicial Vault Path: ~/.polytope/vaults/{bridge_id}
        self.vault_path = os.path.join(vault_root, bridge_id)
        self._enforce_vault_isolation()
        
        self.is_connected = False
        self.session: Any = None
        self.client = httpx.AsyncClient(timeout=30.0)
        self.on_inbound: Optional[Callable] = None
        self.on_event: Optional[Callable] = None
        self.last_activity: Optional[str] = None
        self.last_error: Optional[str] = None
        self._refresh_task: Optional[asyncio.Task] = None

    async def _save_credentials(self, credentials: Dict[str, Any], account_id: str = "default"):
        """Securely persists credentials to the encrypted vault."""
        if self.vault_manager:
            await self.vault_manager.store_connection_secret(self.bridge_id, account_id, credentials)
        else:
            # Fallback for unmanaged environments (testing)
            vault_file = os.path.join(self.vault_path, f"{account_id}_credentials.json")
            with open(vault_file, "w") as f:
                json.dump(credentials, f)
            os.chmod(vault_file, 0o600)

    async def _load_credentials(self, account_id: str = "default") -> Dict[str, Any]:
        """Retrieves credentials from the encrypted vault."""
        if self.vault_manager:
            return await self.vault_manager.retrieve_connection_secret(self.bridge_id, account_id)
        else:
            vault_file = os.path.join(self.vault_path, f"{account_id}_credentials.json")
            if os.path.exists(vault_file):
                with open(vault_file, "r") as f:
                    return json.load(f)
            return {}

    @staticmethod
    def resilient_request(func: Callable):
        """
        Decorator to wrap bridge network requests with production-grade resilience.
        Retries on connection errors and transient 5xx responses with exponential backoff.
        """
        return retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            retry=retry_if_exception_type((httpx.RequestError, httpx.ProtocolError, httpx.HTTPStatusError)),
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

    async def disconnect(self) -> None:
        """Close connections and cleanup background tasks."""
        self.is_connected = False
        if getattr(self, "_refresh_task", None) and not self._refresh_task.done():
            self._refresh_task.cancel()
        if hasattr(self, "client") and isinstance(self.client, httpx.AsyncClient):
            await self.client.aclose()

    async def _dispatch_inbound(self, message: Dict[str, Any]):
        """
        Dispatches an inbound message to the orchestrator pipeline.
        Standardizes the message format before routing.
        """
        if not self.on_inbound:
            self.logger.warning(f"Inbound message dropped — No orchestrator pipeline registered for {self.bridge_id}.")
            return

        # Ensure essential fields exist
        if "protocol" not in message: message["protocol"] = self.bridge_id.split('_')[0].upper()
        if "timestamp" not in message: import time; message["timestamp"] = int(time.time())
        
        self.last_activity = str(message.get("timestamp"))
        
        try:
            if asyncio.iscoroutinefunction(self.on_inbound):
                await self.on_inbound(message)
            else:
                self.on_inbound(message)
        except Exception as e:
            self.logger.error(f"Failed to dispatch inbound message: {e}")
            self.last_error = str(e)

    def get_health(self) -> Dict[str, Any]:
        """
        Returns a standardised health report for this bridge.
        """
        return {
            "bridge_id": self.bridge_id,
            "is_connected": self.is_connected,
            "last_activity": self.last_activity,
            "last_error": self.last_error,
            "protocol": self.bridge_id.split('_')[0].upper()
        }

    def get_availability_status(self) -> dict:
        """Returns structured availability info for the UI Bridge Center."""
        return {
            "bridge_id": self.bridge_id,
            "platform_available": self.is_platform_available,
            "officially_supported": self.is_officially_supported,
            "requirements": {k.value: v for k, v in self._platform_status.items()},
            "connected": self.is_connected,
        }

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

    async def _token_refresh_loop(self, get_creds_fn, set_creds_fn, token_url, client_id, client_secret):
        """
        Background task to periodically refresh tokens before they expire.
        """
        self.logger.info(f"Starting background token refresh loop for {self.bridge_id}")
        while self.is_connected:
            try:
                creds = await get_creds_fn()
                if creds and creds.get("refresh_token") and creds.get("expires_at"):
                    # Use the helper to check and refresh
                    updated = await self._get_valid_token(creds, token_url, client_id, client_secret)
                    if updated["access_token"] != creds["access_token"]:
                        await set_creds_fn(updated)
            except Exception as e:
                self.logger.error(f"Error in {self.bridge_id} refresh loop: {e}")
            
            # Check every 10 minutes
            await asyncio.sleep(600)


class UnofficialBridgeMixin:
    """
    Validation mixin for bridges that use unofficial/private APIs.
    Enforces the UNOFFICIAL_BRIDGES_ENABLED gate and issues a ToS risk disclosure.
    
    If settings.UNOFFICIAL_BRIDGES_ENABLED is False, any attempt to connect
    will raise a RuntimeError with a clear explanation of why it was blocked.
    """
    
    def validate_official_gate(self, protocol_name: str):
        """
        Check if unofficial bridges are enabled in the global settings.
        Raises RuntimeError if disabled.
        """
        from ..config import settings
        if not getattr(settings, "UNOFFICIAL_BRIDGES_ENABLED", False):
            msg = (
                f"[{protocol_name}] Connection blocked. This bridge uses an unofficial "
                "API that carries Terms of Service (ToS) risks. "
                "To enable it, set UNOFFICIAL_BRIDGES_ENABLED=true in your .env file."
            )
            # Use self.logger if available (via BridgeAdapter)
            if hasattr(self, "logger"):
                self.logger.error(msg)
            raise RuntimeError(msg)
        
        if hasattr(self, "logger"):
            self.logger.warning(
                f"[{protocol_name}] Unofficial bridge active. Reminder: Using private "
                "APIs may violate platform Terms of Service and lead to account suspension."
            )
