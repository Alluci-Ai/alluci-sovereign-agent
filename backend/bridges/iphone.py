import os
import json
import socket
import ssl
import asyncio
from typing import Dict, Any, List, Optional
from collections import deque
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, ServiceInfo
from .base import BridgeAdapter

class IPhoneBridge(BridgeAdapter, ServiceListener):
    """
    Sovereign iPhone bridge using zero-configuration mDNS for discovery
    and local TLS TCP sockets for bridging data to avoiding cloud relay endpoints.
    
    [ GAP-001 ] Implements a 100-message inbound buffer for intermittent iOS polling.
    [ GAP-003 ] Implements TLS certificate pinning using a self-managed CA vault.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.zc = None
        self.browser = None
        self.info: Optional[ServiceInfo] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._listen_task: Optional[asyncio.Task] = None
        # [ GAP-001 ] Inbound message buffer for companion polling
        self._inbound_buffer = deque(maxlen=100)
        # [ GAP-003 ] TLS Pinning: Path to the companion's CA cert in the vault
        self._ca_cert_path = os.path.join(self.vault_path, "companion_ca.crt")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        if self.info and self.info.name == name:
            self.logger.info(f"iPhone service {name} removed.")
            self.info = None
            self.is_connected = False

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            self.logger.info(f"iPhone service {name} discovered at {info.parsed_addresses()}")
            self.info = info

    async def store_pinned_ca(self, cert_pem: str) -> bool:
        """
        [ GAP-003 ] Securely stores the companion's CA certificate for TLS pinning.
        This is called during the initial 'pairing' flow.
        """
        try:
            with open(self._ca_cert_path, "w") as f:
                f.write(cert_pem)
            os.chmod(self._ca_cert_path, 0o600)
            self.logger.info("[IPHONE] Companion CA certificate pinned.")
            return True
        except Exception as e:
            self.logger.error(f"[IPHONE] Failed to store pinned CA: {e}")
            return False

    def _build_ssl_context(self) -> ssl.SSLContext:
        """
        [ GAP-003 ] Builds a hardened SSL context with certificate pinning.
        If a pinned CA exists, it enforces strict verification.
        """
        if os.path.exists(self._ca_cert_path):
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self._ca_cert_path)
            context.check_hostname = False # Local discovery uses .local/IPs
            context.verify_mode = ssl.CERT_REQUIRED
            self.logger.debug("[IPHONE] Using pinned TLS certificate verification.")
        else:
            # Fallback for un-paired devices (development only)
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            self.logger.warning("[IPHONE] Security Warning: TLS pinning not active. Pair device to enable.")
        return context

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        if not self.zc:
            self.zc = Zeroconf()
            self.browser = ServiceBrowser(self.zc, "_alluci-iphone._tcp.local.", self)
        
        # Wait a bit for discovery
        for _ in range(10):
            if self.info:
                break
            await asyncio.sleep(0.5)
            
        if not self.info:
            self.logger.warning("No iPhone service discovered over mDNS yet.")
            return False

        try:
            addr = self.info.parsed_addresses()[0]
            port = self.info.port
            
            ssl_context = self._build_ssl_context()
            
            self.reader, self.writer = await asyncio.open_connection(
                addr, port, ssl=ssl_context
            )
            self.is_connected = True
            
            if self._listen_task:
                self._listen_task.cancel()
            self._listen_task = asyncio.create_task(self._listen_loop())
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to iPhone socket: {e}")
            return False

    async def _listen_loop(self):
        try:
            while self.is_connected and self.reader:
                line = await self.reader.readline()
                if not line:
                    break
                try:
                    data = json.loads(line.decode().strip())
                    msg = {
                        "id": data.get("id", "ios_msg"),
                        "from_id": "iphone",
                        "body": data.get("body", ""),
                        "protocol": "IPHONE",
                        "type": data.get("type", "message"),
                        "timestamp": data.get("timestamp") or int(asyncio.get_event_loop().time())
                    }
                    # [ GAP-001 ] Buffer for polling-based retrieval
                    self._inbound_buffer.append(msg)
                    
                    # Also dispatch to real-time pipelines if connected
                    await self._dispatch_inbound(msg)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            self.logger.error(f"iPhone socket listen error: {e}")
        finally:
            self.is_connected = False

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        if not self.is_connected or not self.writer:
            return {"status": "failed", "error": "Not connected to iOS device socket."}
        
        payload = {"recipient": recipient, "body": content}
        payload.update(kwargs)
        
        try:
            self.writer.write((json.dumps(payload) + "\n").encode())
            await self.writer.drain()
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"iPhone socket send error: {e}")
            return {"status": "failed", "error": str(e)}

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        return await self.send(recipient, content)

    async def disconnect(self):
        self.is_connected = False
        if self._listen_task:
            self._listen_task.cancel()
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        if self.zc:
            self.zc.close()
        await super().disconnect()

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        [ GAP-001 ] Retrieves and clears pending messages from the inbound buffer.
        """
        messages = []
        while self._inbound_buffer and len(messages) < limit:
            messages.append(self._inbound_buffer.popleft())
        return messages

    async def validate_integrity(self) -> bool:
        return self.is_connected
