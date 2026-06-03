import os
import json
import stat
import shutil
import asyncio
import contextlib
import hashlib
import platform
import struct
import tempfile
import logging
from typing import Dict, Any, Set, Optional, List
from datetime import datetime, timezone
# ── Logger MUST be initialized before any conditional imports ─────────────────
# The keyring import below may fail on environments without the package, and
# its except block references logger. If logger is defined after that block,
# Python raises NameError at module load time, preventing the app from starting.
from ..logging_config import get_logger
import uuid
logger = get_logger("VaultManager")

# ── Platform-specific optional dependencies ───────────────────────────────────
try:
    import keyring
except ImportError:
    keyring = None
    logger.warning(
        "[Vault] 'keyring' library not importable. "
        "OS Keychain integration disabled — falling back to environment variable. "
        "Install 'keyring' to enable OS keychain integration."
    )

try:
    import resource
except ImportError:
    resource = None

try:
    import signal as _signal
except ImportError:
    _signal = None

# ── Cryptography ──────────────────────────────────────────────────────────────
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

from ..config import settings
from .vdxf_store import VDXFStore

class VaultManager:
    def __init__(self, master_key: str, vault_root: Optional[str] = None):
        
        # P4-004: macOS Keychain Integration
        sync_key = self._ensure_keychain_sync(master_key)
        
        # Security Hardening: Store master key in a mutable bytearray to allow secure RAM wiping
        self.master_key = bytearray(sync_key.encode('utf-8')) if isinstance(sync_key, str) else bytearray(sync_key)
        
        self.vault_root = vault_root or os.path.expanduser("~/.polytope/vaults")
        
    def lock_vault(self):
        """Securely wipes the master key and derived keys from RAM."""
        if hasattr(self, 'master_key') and self.master_key:
            for i in range(len(self.master_key)):
                self.master_key[i] = 0
        if hasattr(self, 'fernet_key') and self.fernet_key:
            self.fernet_key = None
        if hasattr(self, 'aes_key') and self.aes_key:
            self.aes_key = None
        self.private_key = None
        logger.info("[SECURITY] Vault locked. Cryptographic material securely wiped from RAM.")
        self._ensure_vault_root_sync()
        
        # Salt Management for PBKDF2 (P1-004)
        self.salt = self._get_or_create_salt()
        
        # Load or generate RSA keypair for asymmetric operations
        self.private_key, self.public_key = self._get_rsa_keys()
        
        # P1-004: Hardened Key Derivation
        # Derive two distinct keys from the master key to avoid cross-use
        self.fernet_key = self._derive_key("fernet_v1")
        import base64
        self.fernet = Fernet(base64.urlsafe_b64encode(self.fernet_key))
        
        self.aes_key = self._derive_key("aes_v2")
        self.aes_gcm = AESGCM(self.aes_key)
        self.VAULT_V2_PREFIX = b"\x01"
        
        # Tier 1 & 3: VDXF Store (Integrity Anchoring)
        self.vdxf = None
        if settings.VERUS_AUTH_ENABLED and settings.VERUS_ID_IDENTITY:
            self.vdxf = VDXFStore(settings.VERUS_ID_IDENTITY)

    def _get_rsa_keys(self):
        """Retrieves or generates RSA keys protected by the master key."""
        key_path = os.path.join(self.vault_root, "identity.pem")
        if os.path.exists(key_path):
            try:
                with open(key_path, "rb") as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=self.master_key.encode() if isinstance(self.master_key, str) else bytes(self.master_key),
                        backend=default_backend()
                    )
                return private_key, private_key.public_key()
            except (ValueError, InvalidToken, Exception) as e:
                logger.error(f"Failed to decrypt RSA identity key: {e}. Asymmetric operations will be disabled.")
                return None, None
        else:
            try:
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=4096,
                    backend=default_backend()
                )
                pem = private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.BestAvailableEncryption(
                        self.master_key.encode() if isinstance(self.master_key, str) else bytes(self.master_key)
                    )
                )
                with open(key_path, "wb") as f:
                    f.write(pem)
                os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)
                return private_key, private_key.public_key()
            except Exception as e:
                return None, None

    def _get_or_create_salt(self) -> bytes:
        """Loads or generates a persistent salt for PBKDF2."""
        salt_path = os.path.join(self.vault_root, "salt.bin")
        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                return f.read()
        else:
            salt = os.urandom(16)
            with open(salt_path, "wb") as f:
                f.write(salt)
            return salt

    def _derive_key(self, purpose: str, salt: Optional[bytes] = None, iterations: int = 100_000, master_key: Optional[str] = None) -> bytes:
        """Secure PBKDF2 key derivation."""
        target_master = master_key or self.master_key
        target_salt = salt or self.salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=target_salt + purpose.encode(), # Purpose-specific salt domain separation
            iterations=iterations,
            backend=default_backend()
        )
        return kdf.derive(target_master.encode() if isinstance(target_master, str) else bytes(target_master))

    def _ensure_vault_root_sync(self):
        """Sync version of ensure vault root."""
        if not os.path.exists(self.vault_root):
            os.makedirs(self.vault_root, mode=0o700, exist_ok=True)
        else:
            try:
                os.chmod(self.vault_root, stat.S_IRWXU)
            except OSError:
                pass

    def _ensure_keychain_sync(self, provided_key: str) -> str:
        """
        Attempts to retrieve master key from OS keychain.
        If provided_key is valid and not in keychain, migrates it.
        """
        system = platform.system()
        service_name = "alluci-sovereign"
        username = "POLYTOPE_MASTER_KEY"
        
        if not keyring:
            logger.warning("keyring library not found. Falling back to environment.")
            return provided_key

        try:
            # Attempt retrieval
            keychain_key = keyring.get_password(service_name, username)
            
            if keychain_key:
                logger.info("Master key retrieved from OS Keychain.")
                return keychain_key
            
            # If not in keychain but we have a valid provided key, migrate
            if provided_key and "PLACEHOLDER" not in provided_key:
                logger.info(f"Migrating master key to {system} Keychain...")
                keyring.set_password(service_name, username, provided_key)
                return provided_key
                
        except Exception as e:
            logger.error(f"Keychain sync failed: {e}")
            
        return provided_key

    def get_active_vaults(self) -> Set[str]:
        try:
            return {f.split(".")[0] for f in os.listdir(self.vault_root) if f.endswith(".vault")}
        except OSError:
            return set()

    async def store_secret(self, bridge_id: str, data: Dict[str, Any]):
        """Encrypted storage of API keys or session tokens with on-chain anchoring."""
        await asyncio.to_thread(self._store_secret_sync, bridge_id, data)

        # Tier 3: Warm memory cache
        if self.vdxf:
            self.vdxf.set_memory(bridge_id, data)
            # Tier 1: Anchor the NEW aggregate state hash on-chain
            vault_aggregate = await self._get_full_vault_state()
            await self.vdxf.anchor_vault_hash(vault_aggregate)

        # Audit Logging
        from .audit_ledger import sync_audit_entry
        from ..models import AuditEntry
        await sync_audit_entry(AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event="VAULT_SECRET_STORE",
            details={"bridge_id": bridge_id},
            status="INFO"
        ))

    def _store_secret_sync(self, bridge_id: str, data: Dict[str, Any]):
        raw_data = json.dumps(data).encode()
        nonce = os.urandom(12)
        # AES-GCM: prefix + nonce + ciphertext (includes tag at the end in cryptography's AESGCM)
        encrypted = self.VAULT_V2_PREFIX + nonce + self.aes_gcm.encrypt(nonce, raw_data, None)
        path = os.path.join(self.vault_root, f"{bridge_id}.vault")
        
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(encrypted)
        os.replace(tmp_path, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    async def _get_full_vault_state(self) -> str:
        """Returns a stable string representation of all vault files for hashing."""
        return await asyncio.to_thread(self._get_full_vault_state_sync)

    def _get_full_vault_state_sync(self) -> str:
        """Memory-efficient streaming hash of all vault content."""
        hasher = hashlib.sha256()
        for vfile in sorted(os.listdir(self.vault_root)):
            if vfile.endswith(".vault"):
                with open(os.path.join(self.vault_root, vfile), "rb") as f:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
        return hasher.hexdigest()

    async def retrieve_secret(self, bridge_id: str) -> Dict[str, Any]:
        """Decrypts and returns data for a specific manifold bridge with integrity check."""
        # Tier 3: Memory Cache hit? 
        if self.vdxf:
            cached = self.vdxf.get_from_memory(bridge_id)
            if cached:
                return cached

        data = await asyncio.to_thread(self._retrieve_secret_sync, bridge_id)
        
        # Optional Integrity Check?
        if self.vdxf and data:
            vault_aggregate = await self._get_full_vault_state()
            if not await self.vdxf.verify_integrity(vault_aggregate):
                # Integrity mismatch — vault may have been tampered with externally
                logger.error(
                    f"[SECURITY] VDXF integrity verification FAILED for bridge '{bridge_id}'. "
                    f"Vault data may have been tampered with. ACCESS DENIED."
                )
                return {} # Return empty for security

        # Populate cache
        if self.vdxf and data:
            self.vdxf.set_memory(bridge_id, data)
                
        # Audit Logging
        from .audit_ledger import sync_audit_entry
        from ..models import AuditEntry
        await sync_audit_entry(AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event="VAULT_SECRET_RETRIEVAL",
            details={"bridge_id": bridge_id, "success": bool(data)},
            status="INFO" if data else "WARNING"
        ))

        return data or {}

    def _retrieve_secret_sync(self, bridge_id: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.vault_root, f"{bridge_id}.vault")
        if not os.path.exists(path):
            return None
        
        with open(path, "rb") as f:
            secret_data = f.read()
            if not secret_data: return None

            # 1. Try V2 (AES-GCM)
            if secret_data.startswith(self.VAULT_V2_PREFIX):
                try:
                    nonce = secret_data[1:13]
                    ciphertext = secret_data[13:]
                    decrypted = self.aes_gcm.decrypt(nonce, ciphertext, None)
                    return json.loads(decrypted.decode())
                except Exception as e:
                    logger.error(f"AES-GCM decryption failed for {bridge_id}: {e}")
                    return None

            # 2. Try V1 Fallback (Fernet)
            try:
                decrypted = self.fernet.decrypt(secret_data)
                data = json.loads(decrypted.decode())
                # 3. Lazy Migration to V2
                logger.info(f"Migrating {bridge_id} to AES-256-GCM...")
                self._store_secret_sync(bridge_id, data)
                return data
            except (InvalidToken, Exception):
                return None

    # --- Connection-Specific Secrets (OAuth, Tokens, etc.) ---

    async def store_connection_secret(self, bridge_id: str, account_id: str, data: Dict[str, Any]):
        """Securely stores bridge-specific credentials (tokens, client_ids) in a dedicated hierarchy."""
        rel_path = f"connections/{bridge_id}/{account_id}.vault"
        await asyncio.to_thread(self._store_secret_by_path_sync, rel_path, data)
        
        # Anchoring (if enabled)
        if self.vdxf:
            anchor_key = f"conn:{bridge_id}:{account_id}"
            self.vdxf.set_memory(anchor_key, data)
            vault_aggregate = await self._get_full_vault_state()
            await self.vdxf.anchor_vault_hash(vault_aggregate)

    async def retrieve_connection_secret(self, bridge_id: str, account_id: str) -> Dict[str, Any]:
        """Retrieves and decrypts bridge credentials."""
        # Check cache if VDXF enabled
        if self.vdxf:
            anchor_key = f"conn:{bridge_id}:{account_id}"
            cached = self.vdxf.get_from_memory(anchor_key)
            if cached:
                return cached

        rel_path = f"connections/{bridge_id}/{account_id}.vault"
        data = await asyncio.to_thread(self._retrieve_secret_by_path_sync, rel_path)
        
        # Populate cache
        if self.vdxf and data:
            anchor_key = f"conn:{bridge_id}:{account_id}"
            self.vdxf.set_memory(anchor_key, data)
            
        return data or {}

    async def list_connections(self, bridge_id: str) -> List[str]:
        """Returns a list of account IDs currently stored for a specific bridge."""
        return await asyncio.to_thread(self._list_connections_sync, bridge_id)

    def _list_connections_sync(self, bridge_id: str) -> List[str]:
        path = os.path.join(self.vault_root, "connections", bridge_id)
        if not os.path.exists(path):
            return []
        try:
            return [f.replace(".vault", "") for f in os.listdir(path) if f.endswith(".vault")]
        except OSError:
            return []

    async def delete_connection_secret(self, bridge_id: str, account_id: str) -> bool:
        rel_path = f"connections/{bridge_id}/{account_id}.vault"
        return await asyncio.to_thread(self._delete_secret_by_path_sync, rel_path)

    # --- Low-level Path-based Helpers ---

    def _store_secret_by_path_sync(self, rel_path: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_root, rel_path)
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        
        if not self.public_key:
            logger.error(f"Cannot store secret at {rel_path}: RSA Public Key unavailable.")
            return

        # 1. Generate a random 256-bit key for this specific secret
        session_key = os.urandom(32)
        aes_gcm = AESGCM(session_key)
        nonce = os.urandom(12)
        
        # 2. Encrypt the data with the session key
        raw_data = json.dumps(data).encode()
        encrypted_data = aes_gcm.encrypt(nonce, raw_data, None)
        
        # 3. Encrypt the session key with the RSA Public Key
        encrypted_key = self.public_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # 4. Pack together: [VERSION(1)][len_key(4)][encrypted_key][nonce(12)][encrypted_data]
        final_payload = b"\x02" + struct.pack(">I", len(encrypted_key)) + encrypted_key + nonce + encrypted_data
        
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(final_payload)
        os.replace(tmp_path, path)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    def _retrieve_secret_by_path_sync(self, rel_path: str) -> Optional[Dict[str, Any]]:
        path = os.path.join(self.vault_root, rel_path)
        if not os.path.exists(path):
            return None
        
        with open(path, "rb") as f:
            payload = f.read()
            if not payload: return None
            
            # --- New AES-GCM V2 Hybrid Flow ---
            if payload.startswith(b"\x02"):
                if not self.private_key:
                    logger.error(f"Cannot retrieve hybrid secret at {rel_path}: RSA Private Key unavailable.")
                    return None
                try:
                    key_len = struct.unpack(">I", payload[1:5])[0]
                    encrypted_key = payload[5:5+key_len]
                    nonce = payload[5+key_len : 5+key_len+12]
                    encrypted_data = payload[5+key_len+12:]
                    
                    # Decrypt key
                    session_key = self.private_key.decrypt(
                        encrypted_key,
                        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                    )
                    
                    # Decrypt data
                    aes_gcm = AESGCM(session_key)
                    decrypted = aes_gcm.decrypt(nonce, encrypted_data, None)
                    return json.loads(decrypted.decode())
                except Exception as e:
                    logger.error(f"V2 hybrid decryption failed for {rel_path}: {e}")
                    return None

            # --- Legacy Fernet V1 Hybrid Fallback ---
            try:
                if not self.private_key:
                    logger.error(f"Cannot retrieve legacy hybrid secret at {rel_path}: RSA Private Key unavailable.")
                    return None

                key_len = struct.unpack(">I", payload[:4])[0]
                encrypted_key = payload[4:4+key_len]
                encrypted_data = payload[4+key_len:]
                
                session_key = self.private_key.decrypt(
                    encrypted_key,
                    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                )
                
                f = Fernet(session_key)
                decrypted = f.decrypt(encrypted_data)
                data = json.loads(decrypted.decode())
                
                # Lazy migration to hybrid V2
                self._store_secret_by_path_sync(rel_path, data)
                return data
            except Exception as e:
                logger.error(f"V1 hybrid fallback failed for {rel_path}: {e}")
                return None

    def _delete_secret_by_path_sync(self, rel_path: str) -> bool:
        path = os.path.join(self.vault_root, rel_path)
        if os.path.exists(path):
            # Secure overwrite before delete
            with open(path, "wb") as f:
                f.write(os.urandom(os.path.getsize(path)))
            os.remove(path)
            return True
        return False

    async def update_vault_status(self, bridge_id: str, status: str):
        await asyncio.to_thread(self._update_vault_status_sync, bridge_id, status)

    def _update_vault_status_sync(self, bridge_id: str, status: str):
        path = os.path.join(self.vault_root, f"{bridge_id}.status")
        with open(path, "w") as f:
            f.write(status)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    async def get_vault_status(self, bridge_id: str) -> str:
        return await asyncio.to_thread(self._get_vault_status_sync, bridge_id)

    def _get_vault_status_sync(self, bridge_id: str) -> str:
        path = os.path.join(self.vault_root, f"{bridge_id}.status")
        if not os.path.exists(path):
            return "UNKNOWN"
        with open(path, "r") as f:
            return f.read().strip()

    async def delete_secret(self, bridge_id: str) -> bool:
        return await asyncio.to_thread(self._delete_secret_sync, bridge_id)

    def _delete_secret_sync(self, bridge_id: str) -> bool:
        path = os.path.join(self.vault_root, f"{bridge_id}.vault")
        if os.path.exists(path):
            with open(path, "wb") as f:
                f.write(os.urandom(os.path.getsize(path)))
            os.remove(path)
            return True
        return False

    async def rotate_keys(self, new_master_key: str) -> bool:
        """
        Deep rotation of all cryptographic material:
        1. Generates new RSA keypair.
        2. Re-encrypts all symmetric root vaults.
        3. Re-encrypts all hybrid connection secrets with the new RSA key.
        4. Updates identity.pem with the new master key protection.
        """
        return await asyncio.to_thread(self._rotate_keys_sync, new_master_key)

    def _rotate_keys_sync(self, new_master_key: str) -> bool:
        success = False
        try:
            # 1. Prepare new materials
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            import base64

            new_salt = os.urandom(16)
            new_fernet_key = self._derive_key("fernet_v1", salt=new_salt, master_key=new_master_key)
            new_fernet = Fernet(base64.urlsafe_b64encode(new_fernet_key))
            new_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            new_public_key = new_private_key.public_key()

            # 2. Rotate Root Symmetric Vaults
            vaults = [f for f in os.listdir(self.vault_root) if f.endswith(".vault")]
            for vault_file in vaults:
                path = os.path.join(self.vault_root, vault_file)
                data = self._retrieve_secret_sync(vault_file.replace(".vault", ""))
                if data is None:
                    continue
                
                # Encrypt with NEW materials
                # We use the new PBKDF2-derived key
                new_aes_key = self._derive_key("aes_v2", salt=new_salt, master_key=new_master_key)
                new_aes_gcm = AESGCM(new_aes_key)
                
                raw_data = json.dumps(data).encode()
                nonce = os.urandom(12)
                encrypted = self.VAULT_V2_PREFIX + nonce + new_aes_gcm.encrypt(nonce, raw_data, None)
                
                tmp_path = path + ".tmp"
                with open(tmp_path, "wb") as f: f.write(encrypted)
                os.replace(tmp_path, path)
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

            # 3. Rotate Hybrid Connection Secrets (connections/**/*)
            conn_root = os.path.join(self.vault_root, "connections")
            if os.path.exists(conn_root):
                for root, dirs, files in os.walk(conn_root):
                    for fname in files:
                        if fname.endswith(".vault"):
                            fpath = os.path.join(root, fname)
                            rel_path = os.path.relpath(fpath, self.vault_root)
                            
                            # Decrypt with OLD RSA
                            data = self._retrieve_secret_by_path_sync(rel_path)
                            if data:
                                # Re-encrypt with NEW RSA/Fernet
                                # We need a transient helper or temporary state update
                                self._store_secret_by_path_helper_sync(fpath, data, new_public_key)
                                os.chmod(fpath, stat.S_IRUSR | stat.S_IWUSR) # Ensure permissions are set

            # 4. Save New RSA Identity
            key_path = os.path.join(self.vault_root, "identity.pem")
            pem = new_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(
                    new_master_key.encode() if isinstance(new_master_key, str) else new_master_key
                )
            )
            with open(key_path, "wb") as f: f.write(pem)
            os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

            # 5. Update Keychain if applicable
            if keyring:
                try:
                    service_name = "alluci-sovereign"
                    username = "POLYTOPE_MASTER_KEY"
                    keyring.set_password(service_name, username, new_master_key)
                    logger.info("Master key updated in OS Keychain.")
                except Exception as e:
                    logger.error(f"Failed to update Keychain during rotation: {e}")

            # 7. Update salt on disk
            salt_path = os.path.join(self.vault_root, "salt.bin")
            with open(salt_path, "wb") as f:
                f.write(new_salt)

            # 8. Commit to memory
            self.master_key = bytearray(new_master_key.encode('utf-8')) if isinstance(new_master_key, str) else bytearray(new_master_key)
            self.salt = new_salt
            self.fernet_key = new_fernet_key
            self.fernet = new_fernet
            self.aes_key = new_aes_key
            self.aes_gcm = new_aes_gcm
            self.private_key = new_private_key
            self.public_key = new_public_key
            
            success = True
            return True
        except Exception as e:
            logger.error(f"Critical Failure during Key Rotation: {e}")
            return False
        finally:
            # Audit Logging (Critical Event)
            try:
                from .audit_ledger import sync_audit_entry
                from ..models import AuditEntry
                import asyncio
                loop = asyncio.new_event_loop() # key rotation is often sync/background
                loop.run_until_complete(sync_audit_entry(AuditEntry(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    event="VAULT_KEY_ROTATION",
                    details={"success": success},
                    status="CRITICAL"
                )))
            except Exception:
                pass

    def _store_secret_by_path_helper_sync(self, absolute_path: str, data: Dict[str, Any], pub_key):
        """Internal helper for rotation without modifying global state."""
        session_key = os.urandom(32)
        aes_gcm = AESGCM(session_key)
        nonce = os.urandom(12)
        
        raw_data = json.dumps(data).encode()
        encrypted_data = aes_gcm.encrypt(nonce, raw_data, None)
        
        encrypted_key = pub_key.encrypt(
            session_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
        )
        
        payload = b"\x02" + struct.pack(">I", len(encrypted_key)) + encrypted_key + nonce + encrypted_data
        with open(absolute_path, "wb") as f_out: f_out.write(payload)

    async def get_or_create_jwt_keypair(self) -> tuple:
        """
        Retrieves or generates a dedicated RSA-4096 keypair for JWT signing.
        """
        return await asyncio.to_thread(self._get_or_create_jwt_keypair_sync)

    def _get_or_create_jwt_keypair_sync(self):
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        key_path = os.path.join(self.vault_root, "jwt_signing.pem")
        pub_path  = os.path.join(self.vault_root, "jwt_signing_pub.pem")

        if os.path.exists(key_path):
            try:
                with open(key_path, "rb") as f:
                    private_key = serialization.load_pem_private_key(
                        f.read(),
                        password=bytes(self.master_key),
                        backend=default_backend()
                    )
                return private_key, private_key.public_key()
            except Exception as e:
                logger.error(f"Failed to load JWT keypair: {e}")

        # Generate new keypair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend()
        )
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                bytes(self.master_key)
            )
        )
        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        with open(key_path, "wb") as f: f.write(pem)
        with open(pub_path, "wb") as f: f.write(pub_pem)
        os.chmod(key_path, 0o600)
        os.chmod(pub_path, 0o600)

        logger.info("[ JWT ] Generated new RS256 keypair for JWT signing.")
        return private_key, private_key.public_key()

    def export_identity_pem(self, export_passphrase: str) -> str:
        """
        Exports the RSA private key encrypted with a caller-supplied passphrase.
        """
        if not self.private_key:
            raise ValueError("No RSA private key loaded in vault.")

        if not export_passphrase or len(export_passphrase) < 16:
            raise ValueError("Export passphrase must be at least 16 characters.")

        if export_passphrase == self.master_key:
            raise ValueError("Export passphrase must not be the same as the vault master key.")

        from cryptography.hazmat.primitives import serialization
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                export_passphrase.encode()
            )
        ).decode()

    async def flush_cache(self) -> bool:
        return await asyncio.to_thread(self._flush_cache_sync)

    def _flush_cache_sync(self) -> bool:
        try:
            cache_path = os.path.join(self.vault_root, "cache")
            if os.path.exists(cache_path):
                for root, dirs, files in os.walk(cache_path, topdown=False):
                    for file in files:
                        p = os.path.join(root, file)
                        try:
                            with open(p, "wb") as f:
                                f.write(os.urandom(os.path.getsize(p)))
                            os.remove(p)
                        except OSError: pass
                    for dname in dirs:
                        try: os.rmdir(os.path.join(root, dname))
                        except OSError: pass
                shutil.rmtree(cache_path, ignore_errors=True)
            return True
        except Exception:
            return False

class Sandbox:
    """
    Handle for a sandboxed environment.
    Provides methods to execute commands or code within the sandbox directory
    with restricted environment and resource limits, without affecting the main process.
    """
    def __init__(self, sandbox_dir: str, env: Dict[str, str]):
        self.path = sandbox_dir
        self.env = env.copy()
        # Poison network environment for any spawned subprocesses
        self.env["http_proxy"] = "http://0.0.0.0:0"
        self.env["https_proxy"] = "http://0.0.0.0:0"
        self.env["no_proxy"] = ""
        self.env["POLYTOPE_SANDBOXED"] = "1"

    def run_command(self, cmd: List[str], timeout: int = 30) -> Any:
        """
        Runs a command in a subprocess isolated within this sandbox.
        Resource limits and environment poisoning are applied only to the child.
        """
        import subprocess
        
        def preexec_fn():
            if resource is None:
                return
            # Apply resource limits to the child process only
            # The 'resource' module is imported at the top of the file
            try:
                # Max 512 MB virtual memory
                try: resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, resource.RLIM_INFINITY))
                except (AttributeError, ValueError, Exception): pass
                
                # Max 30 seconds CPU time
                try: resource.setrlimit(resource.RLIMIT_CPU, (30, 60))
                except (AttributeError, ValueError, Exception): pass
                
                # Max 256 open file descriptors
                try:
                    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
                    resource.setrlimit(resource.RLIMIT_NOFILE, (min(256, hard), hard))
                except (AttributeError, ValueError, Exception): pass
            except Exception:
                pass

        return subprocess.run(
            cmd,
            cwd=self.path,
            env=self.env,
            preexec_fn=preexec_fn if os.name != "nt" else None,
            capture_output=True,
            text=True,
            timeout=timeout
        )

@contextlib.contextmanager
def SandboxedExecutionEnv():
    """
    Context manager to enforce zero-trust local execution for agents.
    Yields a Sandbox object that provides safe command execution in an isolated directory.
    This implementation is thread-safe and safe for async concurrency as it avoids
    modifying the main process's CWD, environment, or resource limits.
    """
    sandbox_dir = tempfile.mkdtemp(prefix="polytope_sandbox_")
    
    try:
        os.chmod(sandbox_dir, 0o700)
        yield Sandbox(sandbox_dir, dict(os.environ))
    finally:
        # Secure cleanup: overwrite sandbox contents before deletion
        try:
            for root, dirs, files in os.walk(sandbox_dir, topdown=False):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    try:
                        size = os.path.getsize(fpath)
                        with open(fpath, "wb") as f:
                            f.write(os.urandom(size))
                        os.remove(fpath)
                    except OSError:
                        pass
                for dname in dirs:
                    try:
                        os.rmdir(os.path.join(root, dname))
                    except OSError:
                        pass
            shutil.rmtree(sandbox_dir, ignore_errors=True)
        except Exception:
            pass  # Best-effort cleanup
