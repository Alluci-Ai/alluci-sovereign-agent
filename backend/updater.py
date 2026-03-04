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
import httpx
import subprocess
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger("Updater")

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
        Pulls code, installs requirements, migrates database, and triggers a restart.
        Requires authenticated administrative approval.
        """
        if not self.update_available:
            return {"ok": False, "error": "No update available."}

        logger.critical(f"[ UPDATER ] INITIATING SELF-UPDATE TO v{self.latest_version}...")
        
        try:
            # 1. Pull Git Origin
            logger.info("[ UPDATER ] Syncing manifold codebase via git...")
            pull_res = subprocess.run(["git", "pull", "origin", "main"], capture_output=True, text=True)
            if pull_res.returncode != 0:
                return {"ok": False, "error": f"Git Pull Failed: {pull_res.stderr}"}

            # 2. Update Python dependencies
            logger.info("[ UPDATER ] Refreshing dependencies from requirements.txt...")
            pip_res = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], capture_output=True, text=True)
            if pip_res.returncode != 0:
                logger.warning(f"[ UPDATER ] Pip update issues (likely ignored): {pip_res.stderr}")

            # 3. Apply Schema Migrations
            logger.info("[ UPDATER ] Re-anchoring data schema via Alembic...")
            migrate_res = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
            if migrate_res.returncode != 0:
                return {"ok": False, "error": f"Migration Failed: {migrate_res.stderr}"}

            # 4. Trigger Restart
            # We schedule a hard exit. The supervisor (docker, systemd) will bring us back.
            logger.critical("[ UPDATER ] SUCCESS. SYSTEM REBOOT IN 3 SECONDS.")
            asyncio.get_event_loop().call_later(3, lambda: sys.exit(0))
            
            return {"ok": True, "message": "Update sequence successfully initiated. Rebooting..."}

        except Exception as e:
            logger.error(f"[ UPDATER ] Update Failure: {e}")
            return {"ok": False, "error": str(e)}

    def get_status(self) -> Dict[str, Any]:
        return {
            "current_version": self.current_version,
            "latest_version": self.latest_version,
            "update_available": self.update_available,
            "last_check": self._last_check.isoformat() if self._last_check else None
        }

# Global singleton
updater = UpdateManager()
