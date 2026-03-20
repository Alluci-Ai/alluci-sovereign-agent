import os
import json
import socket
import ssl
import asyncio
from typing import Dict, Any, List, Optional
from zeroconf import Zeroconf, ServiceBrowser, ServiceListener, ServiceInfo
from .base import BridgeAdapter

class IPhoneBridge(BridgeAdapter, ServiceListener):
    """
    Sovereign iPhone bridge using zero-configuration mDNS for discovery
    and local TLS TCP sockets for bridging data to avoiding cloud relay endpoints.
    """
    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.zc = None
        self.browser = None
        self.info: Optional[ServiceInfo] = None
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._listen_task: Optional[asyncio.Task] = None

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
            
            # Setup TLS
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE  # Pinned cert would be better
            
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
                    await self._dispatch_inbound({
                        "id": data.get("id", "ios_msg"),
                        "from_id": "iphone",
                        "body": data.get("body", ""),
                        "protocol": "IPHONE",
                        "type": data.get("type", "message")
                    })
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
            self.writer.close()
            await self.writer.wait_closed()
        if self.zc:
            self.zc.close()
        await super().disconnect()

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        return []

    async def validate_integrity(self) -> bool:
        return self.is_connected
