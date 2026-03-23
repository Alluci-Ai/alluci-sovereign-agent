"""
Self-Update Manager for the Alluci Sovereign Agent.
Provides background version checks against GitHub and performs pull-and-migrate updates.

Sovereign Rule: All updates must be triggered by an authenticated administrative session
over the secure WebSocket manifold or REST API. Automatic "silent" updates are disabled
to maintain environmental stability.
"""

import os
import sys
import asyncio
import logging
from .logging_config import get_logger
import httpx
import subprocess
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = get_logger("Updater")

# Default repo for the Sovereign Manifold
GITHUB_REPO = "Alluci-Ai/alluci-sovereign-agent"

class UpdateManager:
    """
    Handles the lifecycle of the daemon's binary and database updates.
    """

    def __init__(self, current_version: str = "1.0.0"):
        self.current_version = current_version
        self.update_available = False
        self.latest_version: Optional[str] = None
        self.checking_task: Optional[asyncio.Task] = None
        self._last_check: Optional[datetime] = None

    async def start(self):
        """Main loop that checks for updates every 4 hours."""
        logger.info("[ UPDATER ] Initializing background version monitor...")
        self.checking_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while True:
            await self.check_for_updates()
            await asyncio.sleep(4 * 3600)  # 4-hour interval

    async def check_for_updates(self) -> bool:
        """
        Queries the GitHub Releases API for the latest version tag.
        """
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        try:
            async with httpx.AsyncClient() as client:
                # Use a timeout of 10s to avoid hanging during network issues
                resp = await client.get(url, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    tag = data.get("tag_name", "").lstrip("v")
                    
                    if tag and self._is_newer(tag, self.current_version):
                        self.update_available = True
                        self.latest_version = tag
                        logger.info(f"[ UPDATER ] New version discovered: v{tag} (Local: v{self.current_version})")
                    else:
                        self.update_available = False
                        logger.debug(f"[ UPDATER ] System up to date (Latest: v{tag})")

                self._last_check = datetime.now(timezone.utc)
                return self.update_available

        except Exception as e:
            logger.warning(f"[ UPDATER ] Network error during version check: {e}")
            return False

    def _is_newer(self, remote: str, local: str) -> bool:
        """Simple semver comparison for version tags."""
        try:
            r_parts = [int(p) for p in remote.split(".")]
            l_parts = [int(p) for p in local.split(".")]
            return r_parts > l_parts
        except Exception:
            # Fallback to string comparison if not strict semver
            return remote != local

    async def perform_update(self) -> Dict[str, Any]:
        """
        [ DEPRECATED ] In-place updates are disabled for production safety. 
        Updates should be performed via the artifact-based deployment pipeline (Docker / CI).
        """
        logger.warning("[ UPDATER ] Blocked: In-place update attempted. Use deployment pipeline.")
        return {
            "ok": False, 
            "error": "In-place updates are disabled. Please deploy a new container image/artifact."
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "last_check": self._last_check.isoformat() if self._last_check else None
        }

# Global singleton
updater = UpdateManager()
