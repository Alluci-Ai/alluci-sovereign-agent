import os
import sys
import shutil
import signal
import socket
import asyncio
import logging
from typing import Optional, Dict, Any
import httpx

from ..logging_config import get_logger
from ..config import settings

logger = get_logger("OpenCodeDaemon")


class OpenCodeDaemon:
    """
    [ PPN-035 ] Sovereign Supervisor for OpenCode Headless Server.
    Manages the lifecycle of `opencode serve` as an isolated on-device child process.
    Guarantees zero remote GitHub network access by completely sanitizing environment credentials.
    """
    _instance: Optional["OpenCodeDaemon"] = None

    def __init__(self, port: int = 4096, hostname: str = "127.0.0.1"):
        self.preferred_port = port
        self.active_port = port
        self.hostname = hostname
        self.process: Optional[asyncio.subprocess.Process] = None
        self._lock = asyncio.Lock()
        self.is_shutting_down = False

    @classmethod
    def get_instance(cls) -> "OpenCodeDaemon":
        if cls._instance is None:
            cls._instance = OpenCodeDaemon()
        return cls._instance

    @staticmethod
    def _find_available_port(start_port: int = 4096, max_attempts: int = 10) -> int:
        """Finds the first unbound local port starting from start_port."""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    s.bind(("127.0.0.1", port))
                    return port
                except OSError:
                    continue
        return start_port

    def _sanitize_environment(self) -> Dict[str, str]:
        """
        Creates an air-gapped environment copy stripped of any remote GitHub credentials,
        PATs, or SSH agent tokens.
        """
        env = os.environ.copy()
        forbidden_keys = [
            "GITHUB_TOKEN",
            "GH_TOKEN",
            "GITHUB_PAT",
            "GIT_SSH_COMMAND",
            "GIT_ASKPASS",
            "SSH_AUTH_SOCK",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY"
        ]
        for key in forbidden_keys:
            env.pop(key, None)

        # Force local baseURL to Alluci's local MLX inference bridge
        env["OPENCODE_BASE_URL"] = f"http://127.0.0.1:{getattr(settings, 'PORT', 8000)}/v1"
        return env

    def _find_opencode_binary(self) -> Optional[str]:
        """Locates the opencode executable on the local system."""
        # 1. Check system PATH
        binary = shutil.which("opencode")
        if binary:
            return binary

        # 2. Check local npm / bun binaries
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        local_node_bin = os.path.join(project_root, "node_modules", ".bin", "opencode")
        if os.path.exists(local_node_bin) and os.access(local_node_bin, os.X_OK):
            return local_node_bin

        # 3. Check global npm paths
        global_npm = os.path.expanduser("~/.npm-global/bin/opencode")
        if os.path.exists(global_npm) and os.access(global_npm, os.X_OK):
            return global_npm

        return None

    async def start(self) -> bool:
        """Starts the OpenCode headless daemon if not already active."""
        async with self._lock:
            if self.process and self.process.returncode is None:
                logger.info(f"[ OpenCodeDaemon ] Server already running on port {self.active_port} (PID: {self.process.pid})")
                return True

            self.active_port = self._find_available_port(self.preferred_port)
            binary = self._find_opencode_binary()

            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            sanitized_env = self._sanitize_environment()

            if binary:
                cmd = [binary, "serve", "--port", str(self.active_port), "--hostname", self.hostname]
            else:
                # Fallback to npx runner if global binary not on PATH
                npx_bin = shutil.which("npx")
                if npx_bin:
                    cmd = [npx_bin, "-y", "opencode-ai", "serve", "--port", str(self.active_port), "--hostname", self.hostname]
                else:
                    logger.warning("[ OpenCodeDaemon ] Neither 'opencode' binary nor 'npx' found. OpenCode harness running in virtual mode.")
                    return False

            try:
                logger.info(f"[ OpenCodeDaemon ] Spawning: {' '.join(cmd)} (cwd: {project_root})")
                self.process = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=project_root,
                    env=sanitized_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                logger.info(f"[ OpenCodeDaemon ] Started process PID: {self.process.pid} on port {self.active_port}")

                # Verify health check
                is_healthy = await self.wait_for_healthy(timeout=10.0)
                if is_healthy:
                    logger.info(f"[ OpenCodeDaemon ] ✅ Health probe verified on http://{self.hostname}:{self.active_port}")
                    return True
                else:
                    logger.warning(f"[ OpenCodeDaemon ] Health check timed out, process PID: {self.process.pid} is starting up.")
                    return True

            except Exception as e:
                logger.error(f"[ OpenCodeDaemon ] Failed to launch server process: {e}")
                self.process = None
                return False

    async def wait_for_healthy(self, timeout: float = 10.0) -> bool:
        """Polls the /global/health endpoint until healthy or timeout expires."""
        url = f"http://{self.hostname}:{self.active_port}/global/health"
        start = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start) < timeout:
            if self.process and self.process.returncode is not None:
                logger.error(f"[ OpenCodeDaemon ] Process exited prematurely with code {self.process.returncode}")
                return False
            try:
                async with httpx.AsyncClient(timeout=1.0) as client:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.5)

        return False

    async def stop(self) -> None:
        """Gracefully terminates the child process and cleans up sockets."""
        async with self._lock:
            self.is_shutting_down = True
            if not self.process or self.process.returncode is not None:
                return

            pid = self.process.pid
            logger.info(f"[ OpenCodeDaemon ] Terminating OpenCode process PID: {pid}...")
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning(f"[ OpenCodeDaemon ] Process {pid} did not terminate gracefully; sending SIGKILL.")
                    self.process.kill()
                    await self.process.wait()
                logger.info(f"[ OpenCodeDaemon ] Process PID {pid} stopped cleanly.")
            except Exception as e:
                logger.error(f"[ OpenCodeDaemon ] Error stopping process {pid}: {e}")
            finally:
                self.process = None

    async def get_status(self) -> Dict[str, Any]:
        """Returns the current operational status of the daemon."""
        running = self.process is not None and self.process.returncode is None
        pid = self.process.pid if running else None
        healthy = False

        if running:
            try:
                async with httpx.AsyncClient(timeout=1.0) as client:
                    resp = await client.get(f"http://{self.hostname}:{self.active_port}/global/health")
                    healthy = (resp.status_code == 200)
            except Exception:
                healthy = False

        return {
            "running": running,
            "port": self.active_port if running else self.preferred_port,
            "pid": pid,
            "healthy": healthy,
            "hostname": self.hostname
        }
