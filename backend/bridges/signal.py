"""
Sovereign Signal Bridge.

Architecture:
  PRIMARY:  signal-cli daemon --socket (persistent process, Unix JSON-RPC socket)
  FALLBACK: signal-cli receive --json  (subprocess polling — legacy, high overhead)

Prerequisites:
  - signal-cli >= 0.13.0 installed and in PATH (or configured via SIGNAL_CLI_PATH)
  - Phone number registered and linked via `signal-cli link` or `signal-cli register`
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BridgeAdapter, PlatformRequirement

class SignalBridge(BridgeAdapter):
    platform_requirements = {PlatformRequirement.SIGNAL_CLI}
    is_officially_supported = True
    """
    Production Signal Bridge using signal-cli daemon mode with Unix socket JSON-RPC.
    Falls back to subprocess polling when the daemon is unavailable.
    """

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        from ..config import settings
        super().__init__(bridge_id, vault_root, vault_manager)
        self.phone_number: Optional[str] = None
        self._cli_path: str = settings.SIGNAL_CLI_PATH
        self._socket_path: str = settings.SIGNAL_SOCKET_PATH

        # Daemon state
        self._daemon_process: Optional[asyncio.subprocess.Process] = None
        self._daemon_task: Optional[asyncio.Task] = None
        self._listener_task: Optional[asyncio.Task] = None
        self._rpc_id: int = 0

        # Fallback polling state
        self._use_daemon: bool = True
        self._message_buffer: List[Dict[str, Any]] = []

    # ── Connection ───────────────────────────────────────────────────────────

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Link the bridge to a registered Signal phone number and start the daemon.
        credentials:
            phone_number (str): E.164 format, e.g. "+14155552671"
            cli_path (str):     Path to signal-cli binary (optional)
            socket_path (str):  Unix socket path (optional)
        """
        from ..config import settings

        self.phone_number = credentials.get("phone_number")
        self._cli_path    = credentials.get("cli_path") or settings.SIGNAL_CLI_PATH  # type: ignore
        self._socket_path = credentials.get("socket_path") or settings.SIGNAL_SOCKET_PATH  # type: ignore

        if self._cli_path == "signal-cli":
            import os
            wrapper_path = os.path.join(os.getcwd(), "bin", "signal-wrapper")
            if os.path.exists(wrapper_path):
                self._cli_path = wrapper_path

        if not self.phone_number:
            import os, json
            from pathlib import Path
            accounts_path = Path("~/.local/share/signal-cli/data/accounts.json").expanduser()
            if accounts_path.exists():
                try:
                    with open(accounts_path, "r") as f:
                        data = json.load(f)
                        if "accounts" in data and len(data["accounts"]) > 0:
                            self.phone_number = data["accounts"][0].get("number")
                except Exception as e:
                    self.logger.error(f"[SIGNAL] Failed to read accounts.json: {e}")

        if not self.phone_number:
            self.last_error = "phone_number required for Signal bridge."
            self.logger.error(f"[SIGNAL] {self.last_error}")
            return False

        # Try to start the daemon
        started = await self._start_daemon()
        if started:
            self._use_daemon = True
            self._listener_task = asyncio.create_task(self._daemon_listener())
            self.logger.info(
                f"[SIGNAL] Daemon mode active — {self.phone_number} on {self._socket_path}"
            )
        else:
            self._use_daemon = False
            self._listener_task = asyncio.create_task(self._polling_fallback())
            self.logger.info(
                f"[SIGNAL] Daemon socket not found. Initialized polling fallback for {self.phone_number}."
            )

        self.is_connected = True
        return True

    # ── Daemon Lifecycle ─────────────────────────────────────────────────────

    async def _start_daemon(self) -> bool:
        """
        Start `signal-cli daemon --socket <path>` as a persistent background process.
        Returns True if the daemon started and the socket became available within 10s.
        """
        # 1. Kill any orphaned signal-cli processes for this number (prevents stale DB locks)
        try:
            import subprocess
            subprocess.run(
                ["pkill", "-9", "-f", f"signal-cli.*{self.phone_number}"],
                capture_output=True
            )
            await asyncio.sleep(0.5)  # Wait for process to fully terminate and release locks
        except Exception as e:
            self.logger.debug(f"[SIGNAL] Orphan cleanup error: {e}")

        # 2. Remove stale socket
        if os.path.exists(self._socket_path):
            try:
                os.remove(self._socket_path)
            except OSError as e:
                self.logger.warning(f"[SIGNAL] Stale socket remove failed: {e}")

        try:
            self._daemon_process = await asyncio.create_subprocess_exec(
                self._cli_path,
                "-u", self.phone_number,  # type: ignore
                "daemon",
                "--socket", self._socket_path,
                "--ignore-stories",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError:
            self.logger.error(f"[SIGNAL] {self._cli_path} not found.")
            return False

        # Wait up to 10 seconds for the socket to appear
        for _ in range(20):
            await asyncio.sleep(0.5)
            if os.path.exists(self._socket_path):
                self.logger.info("[SIGNAL] Daemon socket ready.")
                # Start a stderr reader so the process doesn't deadlock
                asyncio.create_task(self._drain_stderr(self._daemon_process))
                return True

        self.logger.warning("[SIGNAL] Daemon socket did not appear within 10s.")
        if self._daemon_process:
            try:
                self._daemon_process.terminate()
            except ProcessLookupError:
                pass
            self._daemon_process = None
        return False

    async def _drain_stderr(self, proc: asyncio.subprocess.Process) -> None:
        """Consume stderr from the daemon process to prevent pipe deadlock."""
        if proc.stderr:
            async for line in proc.stderr:
                decoded = line.decode(errors="replace").strip()
                if decoded:
                    self.logger.debug(f"[SIGNAL-DAEMON] {decoded}")

    # ── Unix Socket JSON-RPC Client ──────────────────────────────────────────

    async def _rpc_call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a JSON-RPC 2.0 request to the signal-cli daemon socket.
        signal-cli daemon protocol: newline-delimited JSON over a Unix socket.
        """
        self._rpc_id += 1
        request = json.dumps({
            "jsonrpc": "2.0",
            "id":      self._rpc_id,
            "method":  method,
            "params":  params,
        }) + "\n"

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self._socket_path),
                timeout=5.0,
            )
            writer.write(request.encode())
            await writer.drain()

            response_line = await asyncio.wait_for(reader.readline(), timeout=15.0)
            writer.close()
            await writer.wait_closed()

            response = json.loads(response_line.decode())
            if "error" in response:
                raise RuntimeError(
                    f"signal-cli RPC error: {response['error'].get('message', response['error'])}"
                )
            return response.get("result", {})

        except asyncio.TimeoutError:
            raise TimeoutError("signal-cli daemon did not respond within timeout.")
        except (ConnectionRefusedError, FileNotFoundError) as e:
            raise ConnectionError(f"Signal daemon socket unavailable: {e}")

    # ── Daemon Listener (receive loop) ───────────────────────────────────────

    async def _daemon_listener(self) -> None:
        """
        Subscribe to incoming messages via the daemon socket using
        the `subscribeReceive` JSON-RPC method and process them as a stream.
        """
        self.logger.info("[SIGNAL] Starting daemon listener (subscribeReceive).")
        reconnect_delay = 2.0

        while self.is_connected:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_unix_connection(self._socket_path),
                    timeout=5.0,
                )
                # Subscribe to receive events
                subscribe_request = json.dumps({
                    "jsonrpc": "2.0",
                    "id":      0,
                    "method":  "subscribeReceive",
                    "params":  {"account": self.phone_number},
                }) + "\n"
                writer.write(subscribe_request.encode())
                await writer.drain()

                reconnect_delay = 2.0  # Reset on successful connect

                async for raw_line in reader:
                    if not raw_line:
                        break
                    try:
                        event = json.loads(raw_line.decode())
                        await self._handle_daemon_event(event)
                    except json.JSONDecodeError:
                        continue

                writer.close()
                await writer.wait_closed()

            except asyncio.CancelledError:
                self.logger.info("[SIGNAL] Daemon listener cancelled.")
                return
            except Exception as e:
                self.logger.error(f"[SIGNAL] Daemon listener error: {e}. Reconnecting in {reconnect_delay}s.")
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 60)  # Exponential backoff

    async def _handle_daemon_event(self, event: Dict[str, Any]) -> None:
        """Parse a signal-cli daemon event and dispatch normalised inbound message."""
        method = event.get("method", "")
        params = event.get("params", {})

        if method != "receive":
            return

        envelope = params.get("envelope", {})
        data_msg = envelope.get("dataMessage", {})
        sync_msg = envelope.get("syncMessage", {})

        # Handle direct messages and sync messages
        target = data_msg if data_msg else sync_msg.get("sentMessage", {})
        if not target or not target.get("message"):
            return

        sender = envelope.get("sourceNumber") or envelope.get("sourceName", "unknown")
        group_id = target.get("groupInfo", {}).get("groupId")

        # Extract attachments
        attachments = [
            {
                "id":        att.get("id"),
                "mime":      att.get("contentType"),
                "filename":  att.get("filename"),
                "size":      att.get("size"),
                "local_path": att.get("filename"),  # signal-cli downloads to temp dir
            }
            for att in target.get("attachments", [])
        ]

        normalized = {
            "id":          f"{envelope.get('timestamp')}-{sender}",
            "from":        sender,
            "body":        target["message"],
            "group_id":    group_id,
            "attachments": attachments,
            "timestamp":   envelope.get("timestamp"),
            "account_id":  self.phone_number,
            "protocol":    "SIGNAL",
        }

        # Buffer for fetch_unread()
        self._message_buffer.append(normalized)
        if len(self._message_buffer) > 100:
            self._message_buffer.pop(0)

        self.last_activity = datetime.now(timezone.utc).isoformat()
        await self._dispatch_inbound(normalized)

    # ── Subprocess Polling Fallback ──────────────────────────────────────────

    async def _polling_fallback(self) -> None:
        """
        Legacy fallback: calls `signal-cli receive --json` once per 30 seconds.
        Uses a single subprocess call per cycle (not one per message).
        """
        self.logger.info("[SIGNAL] Polling fallback active (30s interval).")

        while self.is_connected:
            try:
                proc = await asyncio.create_subprocess_exec(
                    self._cli_path, "-u", self.phone_number, "receive", "--json",  # type: ignore
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            except FileNotFoundError:
                self.logger.error(f"[SIGNAL] {self._cli_path} not found during polling.")
                await asyncio.sleep(30)
                continue
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20.0)

                if proc.returncode == 0:
                    for line in stdout.decode().splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            await self._handle_daemon_event(json.loads(line))
                        except Exception:
                            continue
                elif stderr:
                    err = stderr.decode().strip()
                    if err:
                        self.logger.error(f"[SIGNAL] Polling error: {err}")

            except asyncio.TimeoutError:
                self.logger.warning("[SIGNAL] Polling subprocess timed out.")
            except asyncio.CancelledError:
                return
            except Exception as e:
                self.logger.error(f"[SIGNAL] Polling fallback failed: {e}")

            await asyncio.sleep(30)

    # ── Send ────────────────────────────────────────────────────────────────

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Send a Signal message.
        Uses JSON-RPC when in daemon mode, subprocess when in fallback mode.
        kwargs:
            attachments (list[str]): Local file paths to attach
            group_id (str):          Group ID for group messages
        """
        if not self.is_connected:
            return {"status": "failed", "error": "Not connected"}

        if self._use_daemon:
            return await self._send_daemon(recipient, content, **kwargs)
        return await self._send_subprocess(recipient, content, **kwargs)

    async def _send_daemon(
        self, recipient: str, content: str, **kwargs
    ) -> Dict[str, Any]:
        """Send via JSON-RPC to the daemon socket."""
        params: Dict[str, Any] = {
            "account":    self.phone_number,
            "message":    content,
        }
        if kwargs.get("group_id"):
            params["groupId"] = kwargs["group_id"]
        else:
            params["recipients"] = [recipient]

        if kwargs.get("attachments"):
            params["attachments"] = kwargs["attachments"]

        try:
            result = await self._rpc_call("send", params)
            self.last_activity = datetime.now(timezone.utc).isoformat()
            return {"status": "success", "timestamp": result.get("timestamp")}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def _send_subprocess(
        self, recipient: str, content: str, **kwargs
    ) -> Dict[str, Any]:
        """Fallback send via subprocess (when daemon is not running)."""
        cmd = [self._cli_path, "-u", self.phone_number, "send", "-m", content]

        if kwargs.get("group_id"):
            cmd += ["-g", kwargs["group_id"]]
        else:
            cmd.append(recipient)

        for att in kwargs.get("attachments", []):
            cmd += ["-a", att]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,  # type: ignore
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
            if proc.returncode == 0:
                self.last_activity = datetime.now(timezone.utc).isoformat()
                return {"status": "success", "raw": stdout.decode().strip()}
            self.last_error = stderr.decode().strip()
            return {"status": "failed", "error": self.last_error}
        except Exception as e:
            self.last_error = str(e)
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    # ── Linking QR ───────────────────────────────────────────────────────────

    async def get_link_qr(self) -> str:
        """Generate a tsdevice:// URI for device linking."""
        import pty
        import os
        try:
            master, slave = pty.openpty()
            proc = await asyncio.create_subprocess_exec(
                self._cli_path, "link", "-n", "Alluci Agent",
                stdout=slave,
                stderr=slave,
            )
            os.close(slave)
            
            reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(reader)
            loop = asyncio.get_running_loop()
            await loop.connect_read_pipe(lambda: protocol, os.fdopen(master, 'rb', buffering=0))
            
            while True:
                line = await reader.readline()
                if not line:
                    break
                text = line.decode(errors='replace').strip()
                if text.startswith("sgnl://"):
                    return text
            return ""
        except Exception as e:
            import traceback
            err_trace = traceback.format_exc()
            self.logger.error(f"[SIGNAL] link command failed: {e}\nTraceback:\n{err_trace}")
            return ""

    async def init_qr(self) -> Dict[str, Any]:
        """Generate a tsdevice:// URI for device linking and broadcast QR_READY."""
        qr_url = await self.get_link_qr()
        if not qr_url:
            return {"status": "error", "message": "Failed to generate QR code. Is signal-cli installed?"}
        if self.on_event:
            asyncio.create_task(self.on_event("bridge.status", {
                "bridge_id": self.bridge_id,
                "status":    "QR_READY",
                "qr_url":    qr_url,
            }))
        return {"status": "ok", "qr_url": qr_url}

    # ── Teardown ─────────────────────────────────────────────────────────────

    async def disconnect(self) -> None:
        self.is_connected = False

        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._daemon_process:
            try:
                self._daemon_process.terminate()
                await asyncio.wait_for(self._daemon_process.wait(), timeout=5.0)
            except Exception:
                self._daemon_process.kill()
            self._daemon_process = None

        await super().disconnect()  # type: ignore
        self.logger.info("[SIGNAL] Bridge disconnected.")

    # ── Supporting Methods ───────────────────────────────────────────────────

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self._message_buffer[-limit:]

    async def validate_integrity(self) -> bool:
        if not self.is_connected:
            return False
        if self._use_daemon:
            return (
                self._daemon_process is not None
                and self._daemon_process.returncode is None
                and os.path.exists(self._socket_path)
            )
        return True

    def get_health(self) -> Dict[str, Any]:
        h = super().get_health()
        h.update({
            "mode":       "daemon" if self._use_daemon else "polling",
            "socket":     self._socket_path if self._use_daemon else None,
            "daemon_pid": self._daemon_process.pid if self._daemon_process else None,
            "buffered":   len(self._message_buffer),
        })
        return h
