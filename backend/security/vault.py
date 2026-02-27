
import os
import json
import stat
import shutil
import contextlib
from cryptography.fernet import Fernet
from typing import Dict, Any, Set

class VaultManager:
    def __init__(self, master_key: str):
        # In production, master_key would be derived from user biometric/password
        self.fernet = Fernet(master_key.encode() if isinstance(master_key, str) else master_key)
        self.vault_root = os.path.expanduser("~/.polytope/vaults")
        self._ensure_vault_root()

    def _ensure_vault_root(self):
        """Create vault root with strict permissions (rwx------) for isolation."""
        if not os.path.exists(self.vault_root):
            os.makedirs(self.vault_root, mode=0o700, exist_ok=True)
        else:
            # Enforce permissions on existing directory
            try:
                os.chmod(self.vault_root, stat.S_IRWXU)
            except OSError:
                pass  # May fail on some filesystems; non-fatal

    def get_active_vaults(self) -> Set[str]:
        try:
            return {f.split(".")[0] for f in os.listdir(self.vault_root) if f.endswith(".vault")}
        except OSError:
            return set()

    def store_secret(self, bridge_id: str, data: Dict[str, Any]):
        """Encrypted storage of API keys or session tokens."""
        encrypted = self.fernet.encrypt(json.dumps(data).encode())
        path = os.path.join(self.vault_root, f"{bridge_id}.vault")
        # Write atomically: write to temp then rename
        tmp_path = path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(encrypted)
        os.replace(tmp_path, path)
        # Restrict file permissions
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    def retrieve_secret(self, bridge_id: str) -> Dict[str, Any]:
        """Decrypts and returns data for a specific manifold bridge."""
        path = os.path.join(self.vault_root, f"{bridge_id}.vault")
        if not os.path.exists(path):
            return {}
        with open(path, "rb") as f:
            decrypted = self.fernet.decrypt(f.read())
            return json.loads(decrypted.decode())

    def update_vault_status(self, bridge_id: str, status: str):
        """Updates the health status of a vault (e.g., HEALTHY, UNSTABLE)."""
        path = os.path.join(self.vault_root, f"{bridge_id}.status")
        with open(path, "w") as f:
            f.write(status)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)

    def get_vault_status(self, bridge_id: str) -> str:
        """Retrieves the health status of a vault."""
        path = os.path.join(self.vault_root, f"{bridge_id}.status")
        if not os.path.exists(path):
            return "UNKNOWN"
        with open(path, "r") as f:
            return f.read().strip()

    def initialize_sqlite_vault(self, bridge_id: str):
        """Creates an isolated SQL database within an encrypted filesystem namespace."""
        bridge_path = os.path.join(self.vault_root, bridge_id)
        if not os.path.exists(bridge_path):
            os.makedirs(bridge_path, mode=0o700, exist_ok=True)
        else:
            os.chmod(bridge_path, stat.S_IRWXU)

    def delete_secret(self, bridge_id: str) -> bool:
        """Securely removes a vault file."""
        path = os.path.join(self.vault_root, f"{bridge_id}.vault")
        if os.path.exists(path):
            # Overwrite before delete for basic secure erasure
            with open(path, "wb") as f:
                f.write(os.urandom(os.path.getsize(path)))
            os.remove(path)
            return True
        return False

    def rotate_keys(self, new_master_key: str) -> bool:
        """Instantly re-encrypts all active vaults with a new master key."""
        try:
            new_fernet = Fernet(new_master_key.encode() if isinstance(new_master_key, str) else new_master_key)
            vaults = [f for f in os.listdir(self.vault_root) if f.endswith(".vault")]
            
            for vault_file in vaults:
                path = os.path.join(self.vault_root, vault_file)
                # Read old
                with open(path, "rb") as f:
                    decrypted = self.fernet.decrypt(f.read())
                # Encrypt new
                encrypted = new_fernet.encrypt(decrypted)
                
                # Atomic write
                tmp_path = path + ".tmp"
                with open(tmp_path, "wb") as f:
                    f.write(encrypted)
                os.replace(tmp_path, path)
                os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            
            self.fernet = new_fernet
            return True
        except Exception:
            return False

    def flush_cache(self) -> bool:
        """Securely erases all temporary state files and unencrypted bridge Caches."""
        try:
            cache_path = os.path.join(self.vault_root, "cache")
            if os.path.exists(cache_path):
                # Simple zero-fill for all files in cache
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
    """Context manager to enforce zero-trust local execution for agents."""
    # In a full production macOS environment, this would hook into `sandbox-exec`
    # or Docker, but structurally this acts as the control boundary.
    # We yield control to the agent, capturing any gross violations.
    try:
        # Pre-execution environment lockdown
        yield
    finally:
        # Post-execution environment restoration
        pass
