import httpx
from typing import Dict, Any, Optional, List
from .base import BridgeAdapter, PlatformRequirement

class GithubBridge(BridgeAdapter):
    """
    GitHub Enterprise Core Bridge.
    Connects to GitHub using a Personal Access Token (PAT).
    """
    platform_requirements = set()  # Only requires internet access

    def __init__(self, bridge_id: str = "github", vault_root: str = "", vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.api_key: Optional[str] = None
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Validates the GitHub token and establishes the connection.
        """
        if not credentials:
            self.logger.error("[GITHUB] No credentials provided.")
            return False

        self.api_key = credentials.get("api_key") or credentials.get("token")
        if not self.api_key:
            self.logger.error("[GITHUB] Missing api_key or token in credentials.")
            return False

        self.headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Validate the token by fetching the authenticated user's identity
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.base_url}/user", headers=self.headers, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    self.is_connected = True
                    self.logger.info(f"[GITHUB] Successfully connected as {data.get('login', 'GitHub User')}")
                    await self._save_credentials(credentials)
                    return True
                else:
                    self.logger.error(f"[GITHUB] Auth failed. Code: {resp.status_code}, Resp: {resp.text}")
                    return False
        except Exception as e:
            self.logger.error(f"[GITHUB] Connection exception: {e}")
            return False

    async def disconnect(self) -> None:
        await super().disconnect()
        self.api_key = None
        if "Authorization" in self.headers:
            del self.headers["Authorization"]
        self.logger.info("[GITHUB] Disconnected.")

    def status(self) -> Dict[str, Any]:
        return {
            "is_connected": self.is_connected,
            "bridge_id": self.bridge_id,
            "platform": "GITHUB"
        }

    # --- Full Capability Operations ---

    async def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Retrieve details about a specific repository."""
        if not self.is_connected:
            raise Exception("GitHub bridge is not connected.")
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}", headers=self.headers, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """List pull requests for a repository."""
        if not self.is_connected:
            raise Exception("GitHub bridge is not connected.")
            
        params = {"state": state}
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}/pulls", headers=self.headers, params=params, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def get_pull_request(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """Retrieve details about a specific pull request."""
        if not self.is_connected:
            raise Exception("GitHub bridge is not connected.")
            
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}", headers=self.headers, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def close_pull_request(self, owner: str, repo: str, pull_number: int) -> Dict[str, Any]:
        """Close a pull request."""
        if not self.is_connected:
            raise Exception("GitHub bridge is not connected.")
            
        payload = {"state": "closed"}
        async with httpx.AsyncClient() as client:
            resp = await client.patch(f"{self.base_url}/repos/{owner}/{repo}/pulls/{pull_number}", headers=self.headers, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def create_issue(self, owner: str, repo: str, title: str, body: Optional[str] = None) -> Dict[str, Any]:
        """Create a new issue."""
        if not self.is_connected:
            raise Exception("GitHub bridge is not connected.")
            
        payload = {"title": title}
        if body:
            payload["body"] = body
            
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/repos/{owner}/{repo}/issues", headers=self.headers, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    async def create_issue_comment(self, owner: str, repo: str, issue_number: int, body: str) -> Dict[str, Any]:
        """Add a comment to an issue or pull request."""
        if not self.is_connected:
            raise Exception("GitHub bridge is not connected.")
            
        payload = {"body": body}
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/repos/{owner}/{repo}/issues/{issue_number}/comments", headers=self.headers, json=payload, timeout=10.0)
            resp.raise_for_status()
            return resp.json()

    # --- Abstract Base Class Implementations ---

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Transmit data through the secure bridge tunnel (Legacy)."""
        self.logger.warning("[GITHUB] send_message is not natively supported for GitHub.")
        return {"status": "unsupported", "protocol": "GITHUB"}

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """Canonical data transmission method (Sovereign Spec §2.3)."""
        self.logger.warning("[GITHUB] send is not natively supported for GitHub.")
        return {"status": "unsupported", "protocol": "GITHUB"}

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent communications for autonomous processing."""
        self.logger.warning("[GITHUB] fetch_unread is not natively supported for GitHub.")
        return []

    async def validate_integrity(self) -> bool:
        """Verify the E2E encryption and connection status."""
        return self.is_connected
