import asyncio
import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from .base import BridgeAdapter

try:
    from nostr_sdk import (
        Keys, 
        Client, 
        Options, 
        LogLevel, 
        EventBuilder, 
        Filter, 
        Event, 
        Metadata, 
        Kind,
        UnsignedEvent,
        ClientMessage,
        RelayMessage,
        Nip4EncryptedMessage
    )
    NOSTR_AVAILABLE = True
except ImportError:
    NOSTR_AVAILABLE = False

class NostrBridge(BridgeAdapter):
    """
    Sovereign Nostr Bridge via nostr-sdk.
    Implements decentralized identity (Keys), NIP-01 (Metadata, Notes), 
    and NIP-04 (Encrypted DMs) within a Simplicial Vault.
    """

    def __init__(self, bridge_id: str, vault_root: str, vault_manager: Optional[Any] = None):
        super().__init__(bridge_id, vault_root, vault_manager)
        self.keys: Optional[Keys] = None
        self.client: Optional[Client] = None
        self.relays: List[str] = [
            "wss://relay.damus.io",
            "wss://relay.snort.social",
            "wss://nos.lol"
        ]
        self.npub: Optional[str] = None
        self.nsec: Optional[str] = None
        self._load_config_from_vault()

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Initializes the Nostr client with a keypair and connects to relays.
        Credentials can contain 'nsec' or 'hex_private_key'.
        If none provided, it generates a new sovereign keypair.
        """
        if not NOSTR_AVAILABLE:
            self.logger.error("[ NOSTR ] nostr-sdk not installed.")
            return False

        nsec = credentials.get("nsec")
        hex_key = credentials.get("hex_private_key")
        
        try:
            if nsec:
                self.keys = Keys.from_nsec(nsec)
            elif hex_key:
                from nostr_sdk import SecretKey
                sk = SecretKey.from_hex(hex_key)
                self.keys = Keys(sk)
            else:
                # Generate new sovereign keys if not provided
                self.keys = Keys.generate()
                self.logger.info("[ NOSTR ] Generated new sovereign keypair.")

            self.npub = self.keys.public_key().to_bech32()
            self.nsec = self.keys.secret_key().to_bech32()
            
            # Setup Client
            opts = Options().wait_for_send(True)
            self.client = Client(self.keys, opts)
            
            custom_relays = credentials.get("relays", [])
            if custom_relays:
                self.relays = custom_relays

            for relay in self.relays:
                await self.client.add_relay(relay)
            
            await self.client.connect()
            self.is_connected = True
            
            # Persist state to vault
            self._persist_state()
            self.logger.info(f"[ NOSTR ] Anchored identity: {self.npub}")
            
            # Start subscription task for DMs and Mentions
            asyncio.create_task(self._subscribe_events())
            
            return True
        except Exception as e:
            self.logger.error(f"[ NOSTR ] Connection failed: {e}")
            return False

    async def _subscribe_events(self):
        """Listens for DMs and Mentions targeting this sovereign identity."""
        if not self.client: return
        
        # Filter for DMs (Kind 4) and Mentions (Kind 1)
        dm_filter = Filter().pubkey(self.keys.public_key()).kind(Kind(4))
        mention_filter = Filter().pubkey(self.keys.public_key()).kind(Kind(1))
        
        await self.client.subscribe([dm_filter, mention_filter])
        self.logger.info("[ NOSTR ] Subscription active for DMs and Mentions.")

        # Real implementation of notification handler
        async for notification in self.client.notifications():
            try:
                if notification.is_event():
                    event = notification.as_event()
                    if event.kind() == Kind(4):
                        # Decrypt and dispatch DM
                        decrypted = await self.client.decrypt_nip04(event.author(), event.content())
                        normalized = {
                            "id": event.id().to_hex(),
                            "from": event.author().to_bech32(),
                            "body": decrypted,
                            "protocol": "NOSTR",
                            "kind": 4,
                            "timestamp": datetime.fromtimestamp(event.created_at().as_secs(), timezone.utc).isoformat()
                        }
                        await self._dispatch_inbound(normalized)
                    elif event.kind() == Kind(1):
                        # Dispatch mention
                        normalized = {
                            "id": event.id().to_hex(),
                            "from": event.author().to_bech32(),
                            "body": event.content(),
                            "protocol": "NOSTR",
                            "kind": 1,
                            "timestamp": datetime.fromtimestamp(event.created_at().as_secs(), timezone.utc).isoformat()
                        }
                        await self._dispatch_inbound(normalized)
                    
                    self.last_activity = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                self.logger.error(f"[ NOSTR ] Notification processing error: {e}")

    async def send_message(self, recipient: str, content: str) -> Dict[str, Any]:
        """Legacy shim for BridgeAdapter compatibility. Defaults to public note."""
        return await self.send(recipient, content)

    async def send(self, recipient: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Publishes an event to the Nostr network.
        If recipient is provided as npub/hex, it sends an encrypted DM (NIP-04).
        Otherwise, it publishes a public note (NIP-01).
        """
        if not self.is_connected or not self.client:
            return {"status": "failed", "error": "Bridge Disconnected"}

        try:
            kind = kwargs.get("kind", 1)
            
            if recipient and (recipient.startswith("npub") or len(recipient) == 64):
                # NIP-04 Encrypted DM
                from nostr_sdk import PublicKey
                target_pubkey = PublicKey.from_bech32(recipient) if recipient.startswith("npub") else PublicKey.from_hex(recipient)
                event_id = await self.client.send_direct_msg(target_pubkey, content, None)
                res_type = "dm"
            else:
                # NIP-01 Public Note
                event_id = await self.client.publish_text_note(content, [])
                res_type = "note"

            self._persist_to_vault("sent_buffer", {
                "type": res_type,
                "recipient": recipient,
                "content": content,
                "event_id": event_id.to_hex(),
                "timestamp": datetime.now().isoformat()
            })
            
            return {"status": "success", "event_id": event_id.to_hex()}
        except Exception as e:
            self.logger.error(f"[ NOSTR ] Send failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def update_metadata(self, name: str, about: str, picture: str = "") -> bool:
        """Updates NIP-01 Profile Metadata."""
        if not self.client: return False
        try:
            metadata = Metadata().set_name(name).set_about(about).set_picture(picture)
            await self.client.set_metadata(metadata)
            return True
        except Exception as e:
            self.logger.error(f"[ NOSTR ] Metadata update failed: {e}")
            return False

    async def fetch_unread(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent DMs for this identity."""
        if not self.client: return []
        try:
            f = Filter().pubkey(self.keys.public_key()).kind(Kind(4)).limit(limit)
            events = await self.client.get_events_of([f], None)
            
            processed = []
            for ev in events:
                try:
                    # Decrypt NIP-04 content
                    decrypted = await self.client.decrypt_nip04(ev.author(), ev.content())
                    processed.append({
                        "id": ev.id().to_hex(),
                        "from": ev.author().to_bech32(),
                        "content": decrypted,
                        "timestamp": ev.created_at().as_secs(),
                        "kind": 4
                    })
                except:
                    continue
            return processed
        except Exception as e:
            self.logger.error(f"[ NOSTR ] Fetch failed: {e}")
            return []

    async def validate_integrity(self) -> bool:
        return self.is_connected and self.client is not None

    def _persist_state(self):
        path = os.path.join(self.vault_path, "identity.json")
        try:
            with open(path, "w") as f:
                json.dump({
                    "npub": self.npub,
                    "nsec": self.nsec,
                    "relays": self.relays
                }, f)
        except Exception as e:
            self.logger.error(f"[ NOSTR ] Vault Write Error: {e}")

    def _load_config_from_vault(self):
        path = os.path.join(self.vault_path, "identity.json")
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    self.npub = data.get("npub")
                    self.nsec = data.get("nsec")
                    self.relays = data.get("relays", self.relays)
                    # We don't auto-connect here to avoid I/O in __init__
            except Exception as e:
                self.logger.error(f"[ NOSTR ] Config load error: {e}")

    def _persist_to_vault(self, box: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_path, f"{box}.jsonl")
        try:
            with open(path, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            self.logger.error(f"[ NOSTR ] Vault Write Error: {e}")

    def get_health(self) -> Dict[str, Any]:
        health = super().get_health()
        health.update({
            "npub": self.npub,
            "relay_count": len(self.relays),
            "identity_anchored": self.nsec is not None
        })
        return health
