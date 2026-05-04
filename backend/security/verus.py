import logging
from ..logging_config import get_logger
import hashlib
import json
from typing import Dict, Any

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    from cryptography.hazmat.primitives import serialization
    ED25519_AVAILABLE = True
except ImportError:
    ED25519_AVAILABLE = False

from ..config import Settings

logger = get_logger("SovereignSecurity")

class SovereignIdentity:
    """
    Manages VerusID authentication and cryptographic signing of 
    Executive Manifests. Uses Ed25519 when keys are available,
    falls back to SHA256 hash for unsigned local mode.
    """
    def __init__(self, settings: Settings, vault=None):
        self.verus_id = settings.VERUS_ID_IDENTITY
        self.private_key_hex = settings.VERUS_ID_PRIVATE_KEY
        self.enabled = bool(self.verus_id)
        self._private_key = None
        self._vault = vault
        
        # If key missing from settings, check vault
        if self.enabled and not self.private_key_hex and vault:
            logger.info(f"[SOVEREIGN] Private key missing in settings, checking vault for '{self.verus_id}'")
            # This is a bit of a chicken-and-egg, but we assume the vault 
            # might have the key stored under 'verusid_signing'
            try:
                # We need to run this sync if possible or handle it in a different way
                # For now, we'll look for a dedicated secret
                pass 
            except Exception:
                pass

        if self.enabled and (self.private_key_hex or self._vault) and ED25519_AVAILABLE:
            try:
                if self.private_key_hex:
                    seed_bytes = bytes.fromhex(self.private_key_hex)
                    self._private_key = Ed25519PrivateKey.from_private_bytes(seed_bytes[:32])
                    logger.info(f"Sovereign Identity Active (Ed25519): {self.verus_id}")
            except Exception as e:
                logger.warning(f"Ed25519 key load failed, falling back to hash: {e}")
                self._private_key = None
        elif self.enabled:
            logger.warning("Sovereign Identity Active (Hash-only — cryptography ed25519 not available)")
        else:
            logger.warning("Sovereign Identity Inactive (Standard Mode)")

    async def load_keys(self):
        """Asynchronously loads keys from vault if not already loaded from settings."""
        if self._private_key or not self._vault or not self.enabled:
            return

        try:
            secrets = await self._vault.retrieve_secret("sovereign_identity")
            if secrets and "private_key" in secrets:
                self.private_key_hex = secrets["private_key"]
                seed_bytes = bytes.fromhex(self.private_key_hex)
                self._private_key = Ed25519PrivateKey.from_private_bytes(seed_bytes[:32])
                logger.info(f"[SOVEREIGN] Identity key loaded from Vault for {self.verus_id}")
        except Exception as e:
            logger.error(f"[SOVEREIGN] Failed to load identity key from Vault: {e}")

    def sign_manifest(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cryptographically signs an execution plan (Manifest).
        Uses Ed25519 if available, otherwise standard SHA256 hash.
        """
        payload_str = json.dumps(manifest, sort_keys=True)
        payload_bytes = payload_str.encode()
        
        if self._private_key and ED25519_AVAILABLE:
            # Real Ed25519 signature
            signature = self._private_key.sign(payload_bytes).hex()
            public_key = self._private_key.public_key().public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw
            ).hex()
            return {
                "manifest": manifest,
                "signature": signature,
                "signer": self.verus_id,
                "publicKey": public_key,
                "method": "ED25519_VDXF_V1"
            }
        
        # Fallback: Standard Hash (unsigned local mode)
        signature = hashlib.sha256(payload_bytes).hexdigest()
        return {
            "manifest": manifest,
            "signature": signature,
            "signer": "LOCAL_DAEMON",
            "method": "SHA256"
        }

    def verify_manifest(self, signed_manifest: Dict[str, Any]) -> bool:
        """
        Verifies the integrity of a signed manifest.
        """
        manifest = signed_manifest.get("manifest")
        sig = signed_manifest.get("signature")
        method = signed_manifest.get("method")
        
        payload_str = json.dumps(manifest, sort_keys=True)
        payload_bytes = payload_str.encode()
        
        if method == "SHA256":
             check = hashlib.sha256(payload_bytes).hexdigest()
             return check == sig
        
        if method == "ED25519_VDXF_V1" and ED25519_AVAILABLE:
            try:
                public_key_bytes = bytes.fromhex(signed_manifest.get("publicKey", ""))
                public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
                sig_bytes = bytes.fromhex(sig)
                public_key.verify(sig_bytes, payload_bytes)
                return True
            except Exception as e:
                logger.error(f"Ed25519 verification failed: {e}")
                return False
             
        return False
