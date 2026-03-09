
import os
import json
import stat
import shutil
import asyncio
import contextlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from typing import Dict, Any, Set, Optional
from backend.security.vdxf_store import VDXFStore

class VaultManager:
    def __init__(self, master_key: str, vault_root: Optional[str] = None):
        from ..config import settings
        self.master_key = master_key
        self.vault_root = vault_root or os.path.expanduser("~/.polytope/vaults")
        self._ensure_vault_root_sync()
        
        # Load or generate RSA keypair for asymmetric operations
        self.private_key, self.public_key = self._get_rsa_keys()
        
        # Legacy symmetric Fernet for simple local state (non-asymmetric)
        self.fernet = Fernet(master_key.encode() if isinstance(master_key, str) else master_key)
        
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
        raw_data = json.dumps(data)
        encrypted = self.fernet.encrypt(raw_data.encode())
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
            decrypted = self.fernet.decrypt(secret_data)
            return json.loads(decrypted.decode())

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

    async def delete_connection_secret(self, bridge_id: str, account_id: str) -> bool:
        rel_path = f"connections/{bridge_id}/{account_id}.vault"
        return await asyncio.to_thread(self._delete_secret_by_path_sync, rel_path)

    # --- Low-level Path-based Helpers ---

    def _store_secret_by_path_sync(self, rel_path: str, data: Dict[str, Any]):
        path = os.path.join(self.vault_root, rel_path)
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        
        # 1. Generate a random AES key for this specific secret
        session_key = Fernet.generate_key()
        f = Fernet(session_key)
        
        # 2. Encrypt the data with the session key
        raw_data = json.dumps(data)
        encrypted_data = f.encrypt(raw_data.encode())
        
        # 3. Encrypt the session key with the RSA Public Key
        encrypted_key = self.public_key.encrypt(
            session_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # 4. Pack together: [len_key (4 bytes)][encrypted_key][encrypted_data]
        import struct
        final_payload = struct.pack(">I", len(encrypted_key)) + encrypted_key + encrypted_data
        
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
            if len(payload) < 4:
                return None
                
            try:
                import struct
                key_len = struct.unpack(">I", payload[:4])[0]
                encrypted_key = payload[4:4+key_len]
                encrypted_data = payload[4+key_len:]
                
                # Decrypt the session key with RSA Private Key
                session_key = self.private_key.decrypt(
                    encrypted_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                # Decrypt the data with the session key
                f = Fernet(session_key)
                decrypted = f.decrypt(encrypted_data)
                return json.loads(decrypted.decode())
            except Exception as e:
                import logging
                logging.getLogger("VaultManager").error(f"Hybrid decryption failed for {rel_path}: {e}")
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
        return await asyncio.to_thread(self._rotate_keys_sync, new_master_key)

    def _rotate_keys_sync(self, new_master_key: str) -> bool:
        try:
            new_fernet = Fernet(new_master_key.encode() if isinstance(new_master_key, str) else new_master_key)
            vaults = [f for f in os.listdir(self.vault_root) if f.endswith(".vault")]
            
            for vault_file in vaults:
                path = os.path.join(self.vault_root, vault_file)
                with open(path, "rb") as f:
                    decrypted = self.fernet.decrypt(f.read())
                encrypted = new_fernet.encrypt(decrypted)
                
                tmp_path = path + ".tmp"
                with open(tmp_path, "wb") as f:
                    f.write(encrypted)
                os.replace(tmp_path, path)
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            
            self.fernet = new_fernet
            return True
        except Exception:
            return False

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
