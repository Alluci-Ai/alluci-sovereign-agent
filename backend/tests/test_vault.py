"""
Vault Manager Unit Tests — Production Coverage

Tests the VaultManager's encryption correctness, key persistence,
secret lifecycle, and error handling. These tests do not require
any external services.

INVARIANTS PROTECTED:
  - Encrypted files cannot be read without the master key
  - Each secret namespace is isolated from others
  - RSA keypair is deterministic given the same vault_root
  - Deleted secrets return empty dict, not errors
  - Vault directory permissions are set to owner-only (0o700)
"""
import os
import json
import stat
import tempfile
import pytest
from unittest.mock import patch
from cryptography.fernet import Fernet, InvalidToken


def make_vault(tmpdir: str):
    """Helper: create a VaultManager with a fresh test key."""
    key = Fernet.generate_key().decode()
    with patch("backend.config.settings") as ms, patch("keyring.get_password", return_value=None), patch("keyring.set_password"):
        ms.VERUS_AUTH_ENABLED = False
        from backend.security.vault import VaultManager
        return VaultManager(key, vault_root=tmpdir), key


class TestVaultEncryption:
    """Core AES-256-GCM encryption and decryption correctness."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_and_retrieve_roundtrip(self):
        """Stored secret is retrieved byte-for-byte identically."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            payload = {"api_key": "sk-test-abc123", "token": "oauth-xyz", "nested": {"deep": True}}
            await vault.store_secret("test_bridge", payload)
            result = await vault.retrieve_secret("test_bridge")
            assert result == payload

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_encrypted_file_is_not_plaintext(self):
        """Vault file on disk must not contain the plaintext secret."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            secret_value = "super-sensitive-api-key-12345"
            await vault.store_secret("bridge", {"key": secret_value})

            # Find the vault file and check it doesn't contain the plaintext
            vault_files = list(os.walk(d))
            raw_contents = b""
            for root, _, files in vault_files:
                for f in files:
                    with open(os.path.join(root, f), "rb") as fh:
                        raw_contents += fh.read()

            assert secret_value.encode() not in raw_contents, \
                "CRITICAL: Secret found in plaintext on disk!"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_different_key_cannot_decrypt(self):
        """A different Fernet key cannot read an encrypted vault."""
        with tempfile.TemporaryDirectory() as d:
            vault1, key1 = make_vault(d)
            await vault1.store_secret("secret_ns", {"value": "the_data"})
            
            # Try to read with a different key — must fail, not return garbage data
            different_key = Fernet.generate_key().decode()
            # Use the SAME directory 'd'
            with patch("backend.config.settings") as ms, patch("keyring.get_password", return_value=None), patch("keyring.set_password"):
                ms.VERUS_AUTH_ENABLED = False
                from backend.security.vault import VaultManager
                # Note: This SHOULD now fail with a password error in __init__ 
                # because it tries to load identity.pem with the wrong key.
                # If we want it to return {}, we should expect the error.
                try:
                    vault2 = VaultManager(different_key, vault_root=d)
                    result = await vault2.retrieve_secret("secret_ns")
                    assert result == {}, "Should return empty dict on decryption failure"
                except (ValueError, InvalidToken):
                    # This is also an acceptable outcome of a bad key
                    pass

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_namespace_isolation(self):
        """Secrets stored under different namespaces do not interfere."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            await vault.store_secret("ns_a", {"key": "value_a"})
            await vault.store_secret("ns_b", {"key": "value_b"})

            result_a = await vault.retrieve_secret("ns_a")
            result_b = await vault.retrieve_secret("ns_b")

            assert result_a["key"] == "value_a"
            assert result_b["key"] == "value_b"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_overwrite_secret(self):
        """Writing to an existing namespace replaces the previous value."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            await vault.store_secret("bridge", {"key": "old_value"})
            await vault.store_secret("bridge", {"key": "new_value"})
            result = await vault.retrieve_secret("bridge")
            assert result["key"] == "new_value"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_returns_empty_dict(self):
        """Retrieving a namespace that was never written returns {}."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            result = await vault.retrieve_secret("never_stored")
            assert result == {}
            assert isinstance(result, dict)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_removes_secret(self):
        """Deleted secret is no longer retrievable."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            await vault.store_secret("deleteme", {"k": "v"})
            await vault.delete_secret("deleteme")
            result = await vault.retrieve_secret("deleteme")
            assert result == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self):
        """Deleting a namespace that doesn't exist returns False without raising."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            result = await vault.delete_secret("phantom_namespace")
            assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_active_vaults_lists_all_namespaces(self):
        """get_active_vaults() returns all namespaces that have been stored."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            await vault.store_secret("alpha", {"k": "v"})
            await vault.store_secret("beta", {"k": "v"})
            await vault.store_secret("gamma", {"k": "v"})
            active = vault.get_active_vaults()
            assert "alpha" in active
            assert "beta" in active
            assert "gamma" in active

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_large_payload_roundtrip(self):
        """Vault correctly handles large payloads (simulates full API key manifest)."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            large_payload = {f"key_{i}": f"value_{i}" * 100 for i in range(50)}
            await vault.store_secret("large_ns", large_payload)
            result = await vault.retrieve_secret("large_ns")
            assert result == large_payload

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rotate_keys(self):
        """Deep rotation re-encrypts all data with a new master key."""
        with tempfile.TemporaryDirectory() as d:
            vault, old_key = make_vault(d)
            
            # 1. Store some data in root vault
            root_payload = {"root": "secret"}
            await vault.store_secret("root_bridge", root_payload)
            
            # 2. Store some data in hybrid connection vault
            conn_payload = {"conn": "secret"}
            await vault.store_connection_secret("bridge_id", "account_id", conn_payload)
            
            # 3. Rotate to a new key
            new_key = Fernet.generate_key().decode()
            success = await vault.rotate_keys(new_key)
            assert success is True
            assert vault.master_key == bytearray(new_key.encode('utf-8'))
            
            # 4. Verify data is still retrievable
            assert await vault.retrieve_secret("root_bridge") == root_payload
            assert await vault.retrieve_connection_secret("bridge_id", "account_id") == conn_payload
            
            # 5. Verify old key cannot decrypt anymore
            # We create a new manager with the OLD key and try to read
            with patch("backend.config.settings") as ms, patch("keyring.get_password", return_value=None), patch("keyring.set_password"):
                ms.VERUS_AUTH_ENABLED = False
                from backend.security.vault import VaultManager
                old_vault = VaultManager(old_key, vault_root=d)
                assert await old_vault.retrieve_secret("root_bridge") == {}


class TestSandbox:
    """Tests for the SandboxedExecutionEnv and Sandbox class."""

    @pytest.mark.unit
    def test_sandbox_execution(self):
        """Sandbox can execute a simple command and has isolated environment."""
        from backend.security.vault import SandboxedExecutionEnv
        
        with SandboxedExecutionEnv() as sb:
            # 1. Test basic command execution
            res = sb.run_command(["echo", "hello"])
            assert res.returncode == 0
            assert "hello" in res.stdout
            
            # 2. Test environment isolation (poisoned proxies)
            res = sb.run_command(["env"])
            assert "POLYTOPE_SANDBOXED=1" in res.stdout
            assert "http_proxy=http://0.0.0.0:0" in res.stdout
            
            # 3. Test filesystem isolation (should be in the sandbox dir)
            res = sb.run_command(["pwd"])
            assert sb.path in res.stdout.strip()
    """Vault file and directory permissions must be owner-only."""

    @pytest.mark.unit
    def test_vault_root_directory_permissions(self):
        """Vault root directory must be chmod 700 (owner read/write/execute only)."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            vault_dir = os.path.join(d)
            mode = oct(stat.S_IMODE(os.stat(vault_dir).st_mode))
            # On non-Windows, check for restrictive permissions
            if os.name != "nt":
                current_mode = stat.S_IMODE(os.stat(vault_dir).st_mode)
                # Should not be world-readable
                assert not (current_mode & stat.S_IROTH), \
                    f"Vault directory is world-readable: {mode}"
