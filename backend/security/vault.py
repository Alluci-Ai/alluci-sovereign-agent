
import os
import json
import stat
import shutil
import asyncio
import contextlib
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Set, Optional
from backend.security.vdxf_store import VDXFStore

class VaultManager:
    def __init__(self, master_key: str, vault_root: Optional[str] = None):
        from ..config import settings
        
        # P4-004: macOS Keychain Integration
        self.master_key = self._ensure_keychain_sync(master_key)
        
        self.vault_root = vault_root or os.path.expanduser("~/.polytope/vaults")
        self._ensure_vault_root_sync()
        
        # Load or generate RSA keypair for asymmetric operations
        self.private_key, self.public_key = self._get_rsa_keys()
        
        # Legacy symmetric Fernet for simple local state (non-asymmetric)
        self.fernet = Fernet(master_key.encode() if isinstance(master_key, str) else master_key)
        
        # New AES-256-GCM for hardened storage (P1-004)
        import hashlib
        self.aes_key = hashlib.sha256(master_key.encode() if isinstance(master_key, str) else master_key).digest()
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
            with open(key_path, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=self.master_key.encode() if isinstance(self.master_key, str) else self.master_key,
                    backend=default_backend()
                )
        else:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096,
                backend=default_backend()
            )
            pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(
                    self.master_key.encode() if isinstance(self.master_key, str) else self.master_key
                )
            )
            with open(key_path, "wb") as f:
                f.write(pem)
            os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR)

        return private_key, private_key.public_key()

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
        import platform
        system = platform.system()
        service_name = "alluci-sovereign"
        username = "master-key"
        
        try:
            import keyring
            # Attempt retrieval
            keychain_key = keyring.get_password(service_name, username)
            
            if keychain_key:
                import logging
                logging.getLogger("VaultManager").info("Master key retrieved from OS Keychain.")
                return keychain_key
            
            # If not in keychain but we have a valid provided key, migrate
            if provided_key and "PLACEHOLDER" not in provided_key:
                import logging
                logging.getLogger("VaultManager").info(f"Migrating master key to {system} Keychain...")
                keyring.set_password(service_name, username, provided_key)
                return provided_key
                
        except ImportError:
            import logging
            logging.getLogger("VaultManager").warning("keyring library not found. Falling back to environment.")
        except Exception as e:
            import logging
            logging.getLogger("VaultManager").error(f"Keychain sync failed: {e}")
            
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
        all_content = []
        for vfile in sorted(os.listdir(self.vault_root)):
            if vfile.endswith(".vault"):
                with open(os.path.join(self.vault_root, vfile), "rb") as f:
                    all_content.append(f.read().hex())
        return "".join(all_content)

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
                import logging
                logging.getLogger("VaultManager").critical(
                    f"[SECURITY] VDXF integrity verification FAILED for bridge '{bridge_id}'. "
                    f"Vault data may have been tampered with. Investigate immediately."
                )
                
        # Populate cache
        if self.vdxf and data:
            self.vdxf.set_memory(bridge_id, data)
                
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
                    import logging
                    logging.getLogger("VaultManager").error(f"AES-GCM decryption failed for {bridge_id}: {e}")
                    return None

            # 2. Try V1 Fallback (Fernet)
            try:
                decrypted = self.fernet.decrypt(secret_data)
                data = json.loads(decrypted.decode())
                # 3. Lazy Migration to V2
                import logging
                logging.getLogger("VaultManager").info(f"Migrating {bridge_id} to AES-256-GCM...")
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
        import struct
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
                try:
                    import struct
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
                    import logging
                    logging.getLogger("VaultManager").error(f"V2 hybrid decryption failed for {rel_path}: {e}")
                    return None

            # --- Legacy Fernet V1 Hybrid Fallback ---
            try:
                import struct
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
                import logging
                logging.getLogger("VaultManager").error(f"V1 hybrid fallback failed for {rel_path}: {e}")
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
        try:
            # 1. Prepare new materials
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization

            new_fernet = Fernet(new_master_key.encode() if isinstance(new_master_key, str) else new_master_key)
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
                with open(path, "rb") as f:
                    decrypted = self.fernet.decrypt(f.read())
                encrypted = new_fernet.encrypt(decrypted)
                
                tmp_path = path + ".tmp"
                with open(tmp_path, "wb") as f: f.write(encrypted)
                os.replace(tmp_path, path)
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR) # Ensure permissions are set

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
            os.chmod(key_path, stat.S_IRUSR | stat.S_IWUSR) # Ensure permissions are set

            # 5. Commit to memory
            self.master_key = new_master_key
            self.fernet = new_fernet
            self.private_key = new_private_key
            self.public_key = new_public_key
            
            return True
        except Exception as e:
            import logging
            logging.getLogger("VaultManager").error(f"Critical Failure during Key Rotation: {e}")
            return False

    def _store_secret_by_path_helper_sync(self, absolute_path: str, data: Dict[str, Any], pub_key):
        """Internal helper for rotation without modifying global state."""
        import struct
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

    def export_identity_pem(self) -> str:
        """Exports the current RSA private key in PEM format for recovery/backup."""
        from cryptography.hazmat.primitives import serialization
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

    async def flush_cache(self) -> bool:
        return await asyncio.to_thread(self._flush_cache_sync)

    def _flush_cache_sync(self) -> bool:
        try:
            cache_path = os.path.join(self.vault_root, "cache")
            if os.path.exists(cache_path):
                for root, dirs, files in os.walk(cache_path):
                    for file in files:
                        p = os.path.join(root, file)
                        with open(p, "wb") as f:
                            f.write(os.urandom(os.path.getsize(p)))
                        os.remove(p)
                shutil.rmtree(cache_path)
            return True
        except Exception:
            return False

@contextlib.contextmanager
def SandboxedExecutionEnv():
    """
    Context manager to enforce zero-trust local execution for agents.
    Creates a restricted environment with:
    - Isolated temporary workspace (chroot-like)
    - Network access blocked via environment override
    - Resource limits on memory, CPU time, and file descriptors
    - Secure cleanup with overwrite on exit
    """
    import tempfile
    import resource
    import signal as _signal

    sandbox_dir = tempfile.mkdtemp(prefix="polytope_sandbox_")
    original_cwd = os.getcwd()
    original_env = os.environ.copy()

    # ── Pre-execution environment lockdown ──────────────────────────
    try:
        # 1. Restrict filesystem: set CWD to sandbox
        os.chmod(sandbox_dir, 0o700)
        os.chdir(sandbox_dir)

        # 2. Block outbound network by poisoning proxy env vars
        #    (subprocess-level isolation; full network namespace requires root/Docker)
        os.environ["http_proxy"] = "http://0.0.0.0:0"
        os.environ["https_proxy"] = "http://0.0.0.0:0"
        os.environ["no_proxy"] = ""
        os.environ["POLYTOPE_SANDBOXED"] = "1"

        # 3. Set resource limits (soft limits; hard limits require root)
        try:
            # Max 512 MB virtual memory
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, resource.RLIM_INFINITY))
        except (ValueError, resource.error):
            pass  # Some platforms don't support RLIMIT_AS

        try:
            # Max 30 seconds CPU time
            resource.setrlimit(resource.RLIMIT_CPU, (30, 60))
        except (ValueError, resource.error):
            pass

        try:
            # Max 256 open file descriptors
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            resource.setrlimit(resource.RLIMIT_NOFILE, (min(256, hard), hard))
        except (ValueError, resource.error):
            pass

        yield sandbox_dir

    finally:
        # ── Post-execution environment restoration ──────────────────
        # 1. Restore CWD
        try:
            os.chdir(original_cwd)
        except OSError:
            pass

        # 2. Restore environment
        os.environ.clear()
        os.environ.update(original_env)

        # 3. Secure cleanup: overwrite sandbox contents before deletion
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
