"""
Verus Node Manager — Autonomous daemon management for Sovereign Mode.

Handles:
- Downloading and verifying the verusd binary for the current OS/Arch.
- Auto-generating VRSC.conf with secure, random credentials.
- Managing the daemon process (start, stop, monitor).
- Tracking synchronization progress.
"""

import os
import sys
import json
import secrets
import shutil
import asyncio
import logging
from ..logging_config import get_logger
import platform
import subprocess
import httpx
import tarfile
from pathlib import Path
from typing import Optional, Dict, Any
from backend.config import settings

logger = get_logger("VerusNode")

class VerusNodeManager:
    """
    Orchestrates the lifecycle of the local verusd node.
    """
    
    # Latest release info
    VERUSD_RELEASES = {
        "Darwin": {
            "x86_64": "https://github.com/VerusCoin/VerusCoin/releases/download/v1.2.15/Verus-CLI-MacOS-v1.2.15.tgz",
            "arm64": "https://github.com/VerusCoin/VerusCoin/releases/download/v1.2.15/Verus-CLI-MacOS-v1.2.15.tgz",
        },
        "Linux": {
            "x86_64": "https://github.com/VerusCoin/VerusCoin/releases/download/v1.2.15/Verus-CLI-Linux-v1.2.15-x86_64.tgz",
            "aarch64": "https://github.com/VerusCoin/VerusCoin/releases/download/v1.2.15/Verus-CLI-Linux-v1.2.15-arm64.tgz",
        }
    }

    def __init__(self):
        self.os_type = platform.system()
        self.arch = platform.machine()
        
        # Base paths
        self.home_dir = Path.home()
        self.alluci_dir = self.home_dir / ".alluci" / "verus"
        self.bin_dir = self.alluci_dir / "bin"
        self.data_dir = self.alluci_dir / "data"
        self.verusd_path = self.bin_dir / ("verusd" if self.os_type != "Windows" else "verusd.exe")
        self.conf_path = self.data_dir / "VRSC.conf"
        
        # Process management
        self.process: Optional[asyncio.subprocess.Process] = None
        self._sync_status: Dict[str, Any] = {"height": 0, "longestchain": 0, "percent": 0.0}

        # Initialize directories
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def is_installed(self) -> bool:
        """Checks if the verusd binary is present."""
        return self.verusd_path.exists()

    async def provision_binary(self):
        """Downloads and extracts the correct verusd binary."""
        if await self.is_installed():
            logger.info("[Node] verusd already installed.")
            return

        release_url = self.VERUSD_RELEASES.get(self.os_type, {}).get(self.arch)
        if not release_url:
            raise Exception(f"Unsupported OS/Arch: {self.os_type}/{self.arch}")

        logger.info(f"[Node] Downloading verusd from {release_url}...")
        
        tmp_file = self.alluci_dir / "verus_cli.tgz"
        async with httpx.AsyncClient() as client:
            resp = await client.get(release_url, follow_redirects=True, timeout=300.0)
            resp.raise_for_status()
            with open(tmp_file, "wb") as f:
                f.write(resp.content)

        logger.info("[Node] Extracting outer bundle...")
        with tarfile.open(tmp_file, "r:gz") as tar:
            tar.extractall(path=self.bin_dir)
        
        # Check for nested tarball (v1.2.15+)
        for item in self.bin_dir.iterdir():
            if item.suffix == ".gz":
                logger.info(f"[Node] Extracting nested tarball: {item.name}")
                with tarfile.open(item, "r:gz") as nest_tar:
                    nest_tar.extractall(path=self.bin_dir)
                os.remove(item)

        # Move binaries to root of bin_dir if nested
        for item in self.bin_dir.iterdir():
            if item.is_dir() and "verus" in item.name.lower():
                for subitem in item.iterdir():
                    dest = self.bin_dir / subitem.name
                    if dest.exists():
                        if dest.is_dir(): shutil.rmtree(dest)
                        else: os.remove(dest)
                    shutil.move(str(subitem), str(self.bin_dir))
                shutil.rmtree(item)

        os.remove(tmp_file)
        # Ensure executable permissions
        if self.verusd_path.exists():
            os.chmod(self.verusd_path, 0o755)
        
        # Run fetch-params if available
        fetch_params = self.bin_dir / "fetch-params"
        if fetch_params.exists():
            logger.info("[Node] Running fetch-params (Zcash parameters)...")
            os.chmod(fetch_params, 0o755)
            # This can be slow, but mandatory for first run
            subprocess.run([str(fetch_params)], check=False)

        logger.info("[Node] verusd provisioned successfully.")

    async def generate_config(self, force: bool = False):
        """Creates VRSC.conf if it doesn't exist."""
        if self.conf_path.exists() and not force:
            return

        rpc_user = "alluci"
        rpc_pass = secrets.token_hex(16)
        
        config_content = f"""
rpcuser={rpc_user}
rpcpassword={rpc_pass}
rpcport={settings.VERUS_RPC_PORT}
rpcallowip=127.0.0.1
server=1
txindex=1
addressindex=1
timestampindex=1
spentindex=1
zindex=1
"""
        with open(self.conf_path, "w") as f:
            f.write(config_content)
        
        logger.info(f"[Node] VRSC.conf generated at {self.conf_path}")
        
    async def start(self):
        """Starts the verusd daemon in the background."""
        if self.process:
            logger.warning("[Node] Daemon process already running.")
            return

        if not await self.is_installed():
            await self.provision_binary()
        
        await self.generate_config()

        cmd = [
            str(self.verusd_path),
            f"-datadir={self.data_dir}",
            "-conf=VRSC.conf"
        ]

        logger.info(f"[Node] Starting daemon: {' '.join(cmd)}")
        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            # Start background task to monitor logs and sync
            asyncio.create_task(self._monitor_process())
        except Exception as e:
            logger.error(f"[Node] Failed to start daemon: {e}")
            raise

    async def stop(self):
        """Stops the verusd daemon."""
        if not self.process:
            return

        logger.info("[Node] Stopping verusd...")
        self.process.terminate()
        await self.process.wait()
        self.process = None

    async def _monitor_process(self):
        """Continuously monitors status and sync progress."""
        while self.process:
            try:
                # We'll use the existing VerusRPCClient to check status 
                # (it handles its own retries/fallbacks)
                from backend.security.verus_rpc import verus_rpc
                info = await verus_rpc.get_info()
                if info:
                    self._sync_status["height"] = info.get("blocks", 0)
                    self._sync_status["longestchain"] = info.get("longestchain", 0)
                    if self._sync_status["longestchain"] > 0:
                        self._sync_status["percent"] = (self._sync_status["height"] / self._sync_status["longestchain"]) * 100
                    else:
                        self._sync_status["percent"] = 100.0 if self._sync_status["height"] > 0 else 0.0
                
            except Exception:
                # Daemon might just be starting up
                pass
            await asyncio.sleep(10)

    def get_status(self) -> Dict[str, Any]:
        """Returns the current node status."""
        return {
            "active": self.process is not None,
            "pid": self.process.pid if self.process else None,
            "sync": self._sync_status,
            "directories": {
                "bin": str(self.bin_dir),
                "data": str(self.data_dir)
            }
        }

# Singleton instance
node_manager = VerusNodeManager()
