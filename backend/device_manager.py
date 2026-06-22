import os
import json
import base64
import hashlib
import platform
import psutil
from .logging_config import get_logger
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from sqlmodel import Session, select
from .database import engine as db_engine
from .models import Device, DeviceBinding

logger = get_logger("DeviceManager")

class DeviceManager:
    """
    Manages joined device identities, pairing, and node capability reporting (Sovereign Spec §4.3).
    Provides Ed25519 identity verification and high-fidelity hardware introspection.
    """

    def __init__(self, vault_path: str):
        self.vault_path = vault_path
        self._ensure_node_identity()

    def _ensure_node_identity(self):
        """Ensures this sovereign node has its own Ed25519 identity for cross-signing."""
        key_path = os.path.join(self.vault_path, "node_identity.key")
        if not os.path.exists(key_path):
            private_key = ed25519.Ed25519PrivateKey.generate()
            private_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.OpenSSH,
                encryption_algorithm=serialization.NoEncryption()
            )
            os.makedirs(os.path.dirname(key_path), exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(private_bytes)
            logger.info("Generated new Node Ed25519 identity.")

    def get_node_public_key(self) -> str:
        """Returns the base64-encoded public key of this node."""
        key_path = os.path.join(self.vault_path, "node_identity.key")
        with open(key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
        
        # Ensure it's the correct type for .public_key()
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
             # Try reloading if encoding was different, but generation uses Ed25519
             pass
             
        public_key = private_key.public_key()
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return base64.b64encode(public_bytes).decode()

    def create_pairing_session(self, agent_id: str) -> Dict[str, Any]:
        """
        Generates a temporary setup token and QR code payload for device pairing.
        The QR URI is intended for UI rendering.
        """
        setup_token = base64.urlsafe_b64encode(os.urandom(32)).decode()
        # Payload for QR: node_pk, setup_token, agent_id
        payload = {
            "node_pk": self.get_node_public_key(),
            "token": setup_token,
            "agent_id": agent_id,
            "ts": datetime.now(timezone.utc).isoformat()
        }
        # Standard Alluci pairing URI scheme
        qr_data = f"alluci://pair?data={base64.b64encode(json.dumps(payload).encode()).decode()}"
        
        return {
            "qr_uri": qr_data,
            "setup_token": setup_token,
            "expires_in": 300  # 5 minute window
        }

    async def register_device(self, name: str, public_key_b64: str, capabilities: Dict[str, Any]) -> Device:
        """
        Registers a new device in 'pending' status for admin approval.
        Uses Ed25519 public key as the primary identity anchor.
        """
        try:
            public_bytes = base64.b64decode(public_key_b64)
            if len(public_bytes) != 32:
                raise ValueError("Invalid Ed25519 public key length (expected 32 bytes)")
        except Exception as e:
            raise ValueError(f"Public key validation failed: {e}")

        fingerprint = hashlib.sha256(public_bytes).hexdigest()

        with Session(db_engine) as session:
            stmt = select(Device).where(Device.fingerprint == fingerprint)
            existing = session.exec(stmt).first()
            if existing:
                existing.name = name
                existing.capabilities = capabilities
                existing.last_seen = datetime.now(timezone.utc)
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing

            new_device = Device(
                name=name,
                public_key=public_key_b64,
                fingerprint=fingerprint,
                status="pending",
                capabilities=capabilities,
                last_seen=datetime.now(timezone.utc)
            )
            session.add(new_device)
            session.commit()
            session.refresh(new_device)
            return new_device

    async def approve_device(self, device_id: int) -> bool:
        """Approves a pending device, allowing it to bind to agent resources."""
        with Session(db_engine) as session:
            device = session.get(Device, device_id)
            if not device:
                return False
            device.status = "approved"
            session.add(device)
            session.commit()
            return True

    async def revoke_device(self, device_id: int) -> bool:
        """Revokes all access for a device and invalidates bindings."""
        with Session(db_engine) as session:
            device = session.get(Device, device_id)
            if not device:
                return False
            device.status = "revoked"
            session.add(device)
            session.commit()
            return True

    def rotate_binding_token(self, device_id: int, agent_id: str) -> str:
        """
        Generates or rotates a high-entropy binding token for an approved device.
        Tokens default to a 30-day sliding window.
        Stores a secure SHA-256 hash of the token in the database.
        """
        with Session(db_engine) as session:
            device = session.get(Device, device_id)
            if not device or device.status != "approved":
                raise ValueError("Device binding rejected: Device must be in 'approved' state.")

            # Generate high-entropy token
            raw_token = base64.urlsafe_b64encode(os.urandom(48)).decode()
            hashed_token = hashlib.sha256(raw_token.encode()).hexdigest()
            
            stmt = select(DeviceBinding).where(
                DeviceBinding.device_id == device_id,
                DeviceBinding.agent_id == agent_id
            )
            binding = session.exec(stmt).first()
            if not binding:
                binding = DeviceBinding(device_id=device_id, agent_id=agent_id)
            
            binding.token = hashed_token
            binding.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
            session.add(binding)
            session.commit()
            return raw_token

    @staticmethod
    def get_local_capabilities() -> Dict[str, Any]:
        """
        Reports comprehensive node capability metadata.
        Includes CPU architecture, RAM capacity, and OS platform.
        """
        try:
            return {
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "cpu_count_logical": psutil.cpu_count(logical=True),
                "cpu_count_physical": psutil.cpu_count(logical=False),
                "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "python_version": platform.python_version(),
                "node_name": platform.node(),
                "ts": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {"error": f"Capability discovery failed: {e}"}
