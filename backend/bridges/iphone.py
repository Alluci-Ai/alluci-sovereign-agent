import os
import json
import ssl
import asyncio
from typing import Dict, Any, List, Optional
from collections import deque
try:
    from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, ServiceInfo
except ImportError:
    class Zeroconf:
        def close(self):
            pass
    class ServiceBrowser:
        def __init__(self, *args, **kwargs):
            pass
    class ServiceListener:
        pass
    class ServiceInfo:
        def __init__(self, *args, **kwargs):
            pass
        def parsed_addresses(self):
            return []
        @property
        def name(self):
            return ""
        @property
        def port(self):
            return 0
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
        self._inbound_buffer = deque(maxlen=100)  # type: ignore
        # Outbound message buffer for handling disconnects/roaming
        self._outbound_buffer = deque(maxlen=200)  # type: ignore
        # [ GAP-003 ] TLS Pinning: Path to the companion's CA cert in the vault
        self._ca_cert_path = os.path.join(self.vault_path, "companion_ca.crt")

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """
        [ RES-003 ] Triggered when iPhone service details (like IP) change.
        Ensures the bridge reconnects to the new address.
        """
        if self.info and self.info.name == name:
            new_info = zc.get_service_info(type_, name)
            if new_info and new_info.parsed_addresses() != self.info.parsed_addresses():
                self.logger.info(f"[IPHONE] Address change detected for {name}. Reconnecting...")
                self.info = new_info
                # Trigger an async reconnect in the background
                asyncio.create_task(self.connect({}))

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
        [ GAP-003 / RES-002 ] Securely and atomically stores the companion's CA certificate.
        """
        import tempfile
        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self._ca_cert_path))
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(cert_pem)
            os.chmod(temp_path, 0o600)
            os.replace(temp_path, self._ca_cert_path)
            self.logger.info("[IPHONE] Companion CA certificate pinned atomically.")
            return True
        except Exception as e:
            self.logger.error(f"[IPHONE] Failed to store pinned CA: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False

    def _build_ssl_context(self) -> ssl.SSLContext:
        """
        [ GAP-003 / DEBT-003 ] Builds a hardened SSL context with internal certificate pinning.
        Enforces strict verification; connection is rejected if the device is not paired.
        """
        if os.path.exists(self._ca_cert_path):
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self._ca_cert_path)
            context.check_hostname = False # Local discovery uses .local/IPs
            context.verify_mode = ssl.CERT_REQUIRED
            self.logger.debug("[IPHONE] Using pinned TLS certificate verification.")
            return context
        
        # [ DEBT-003 ] Refuse to connect entirely when unpaired
        raise ssl.SSLError("Security Violation: iPhone TLS pinning not active. Pair device to enable.")

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        if not self.zc:
            self.zc = Zeroconf()  # type: ignore
            self.browser = ServiceBrowser(self.zc, "_alluci-iphone._tcp.local.", self)  # type: ignore
        
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
                
                # Drain outbound buffer while connected
                while self._outbound_buffer and self.is_connected and self.writer:
                    queued_payload = self._outbound_buffer[0]
                    try:
                        self.writer.write((queued_payload + "\n").encode())
                        await self.writer.drain()
                        self._outbound_buffer.popleft()
                    except Exception as e:
                        self.logger.error(f"Failed to send queued outbound payload: {e}")
                        break
        except Exception as e:
            self.logger.error(f"iPhone socket listen error: {e}")
        finally:
            self.is_connected = False

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        payload = {"recipient": recipient, "body": content}
        payload.update(kwargs)
        payload_str = json.dumps(payload)
        
        if not self.is_connected or not self.writer:
            self._outbound_buffer.append(payload_str)
            self.logger.warning("iPhone socket disconnected. Payload queued for next connection.")
            return {"status": "queued", "message": "Queued for delivery."}
        
        try:
            self.writer.write((payload_str + "\n").encode())
            await self.writer.drain()
            return {"status": "success"}
        except Exception as e:
            self.logger.error(f"iPhone socket send error: {e}")
            self._outbound_buffer.append(payload_str)
            return {"status": "queued", "error": str(e)}

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
        await super().disconnect()  # type: ignore

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        [ GAP-001 ] Retrieves and clears pending messages from the inbound buffer.
        """
        messages = []  # type: ignore
        while self._inbound_buffer and len(messages) < limit:
            messages.append(self._inbound_buffer.popleft())
        return messages

    async def validate_integrity(self) -> bool:
        return self.is_connected
