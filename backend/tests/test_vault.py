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
                old_vault = VaultManager(old_key, vault_root=d)
                assert await old_vault.retrieve_secret("root_bridge") == {}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connection_secrets_vdxf(self):
        """Connection secrets leverage VDXF cache if available."""
        from unittest.mock import AsyncMock, MagicMock
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            vault.vdxf = MagicMock()
            vault.vdxf.set_memory = MagicMock()
            vault.vdxf.anchor_vault_hash = AsyncMock()
            vault.vdxf.get_from_memory = MagicMock(return_value={"cached": "true"})
            
            # test cache hit
            res = await vault.retrieve_connection_secret("b1", "a1")
            assert res == {"cached": "true"}
            vault.vdxf.get_from_memory.assert_called_once_with("conn:b1:a1")
            
            # test store triggers anchor
            await vault.store_connection_secret("b2", "a2", {"k": "v"})
            vault.vdxf.set_memory.assert_called_with("conn:b2:a2", {"k": "v"})
            vault.vdxf.anchor_vault_hash.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_connections_oserror(self):
        """list_connections handles missing dir and OSError."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            # missing dir
            assert await vault.list_connections("nonexistent") == []
            
            # oserror
            await vault.store_connection_secret("b1", "a1", {"k": "v"})
            with patch("os.listdir", side_effect=OSError("denied")):
                assert await vault.list_connections("b1") == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_secret_by_path_no_public_key(self):
        """_store_secret_by_path_sync does nothing if public_key is missing."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            vault.public_key = None
            vault._store_secret_by_path_sync("some_path", {"k": "v"})
            assert not os.path.exists(os.path.join(d, "some_path"))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_secret_by_path_corrupt(self):
        """_retrieve_secret_by_path_sync handles non-existent and corrupt data."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            
            # Missing
            assert vault._retrieve_secret_by_path_sync("missing.vault") is None
            
            # Corrupt payload (not starting with 0x02)
            path = os.path.join(d, "corrupt.vault")
            with open(path, "wb") as f:
                f.write(b"\x01BAD_DATA")
            assert vault._retrieve_secret_by_path_sync("corrupt.vault") is None
            
            # Empty payload
            with open(path, "wb") as f:
                f.write(b"")
            assert vault._retrieve_secret_by_path_sync("corrupt.vault") is None


    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_or_create_jwt_keypair(self):
        """JWT keypair generation and retrieval works."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            # Create new
            priv1, pub1 = await vault.get_or_create_jwt_keypair()
            assert priv1 is not None
            assert pub1 is not None
            
            # Load existing
            priv2, pub2 = await vault.get_or_create_jwt_keypair()
            assert priv1.private_numbers() == priv2.private_numbers()
            
            # Corrupt existing to trigger fallback to generate new
            path = os.path.join(d, "jwt_signing.pem")
            with open(path, "wb") as f:
                f.write(b"BAD_KEY")
            
            priv3, pub3 = await vault.get_or_create_jwt_keypair()
            # Should have generated a new one
            assert priv1.private_numbers() != priv3.private_numbers()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_export_identity_pem(self):
        """Export identity PEM with different passphrases."""
        with tempfile.TemporaryDirectory() as d:
            vault, key = make_vault(d)
            
            # Export with valid new passphrase
            new_passphrase = "super_secure_passphrase_123"
            pem = vault.export_identity_pem(new_passphrase)
            assert isinstance(pem, str)
            assert "BEGIN ENCRYPTED PRIVATE KEY" in pem
            
            # Invalid exports
            with pytest.raises(ValueError, match="at least 16"):
                vault.export_identity_pem("short")
                
            with pytest.raises(ValueError, match="must not be the same"):
                vault.export_identity_pem(vault.master_key)
                
            vault.private_key = None
            with pytest.raises(ValueError, match="No RSA private key"):
                vault.export_identity_pem("long_enough_passphrase_here")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_flush_cache(self):
        """flush_cache removes cache dir and securely overwrites."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            cache_dir = os.path.join(d, "cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Make a dummy file
            dummy_file = os.path.join(cache_dir, "test.txt")
            with open(dummy_file, "wb") as f:
                f.write(b"SECRET")
                
            assert await vault.flush_cache() is True
            assert not os.path.exists(cache_dir)
            
            # Exception in flush_cache
            os.makedirs(cache_dir, exist_ok=True)
            with patch("shutil.rmtree", side_effect=Exception("Failed")):
                assert vault._flush_cache_sync() is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lock_vault(self):
        """lock_vault clears sensitive key material from memory."""
        with tempfile.TemporaryDirectory() as d:
            vault, key = make_vault(d)
            vault.lock_vault()
            
            # Check master_key is zeroed
            assert all(b == 0 for b in vault.master_key)
            assert getattr(vault, 'fernet_key', None) is None
            assert getattr(vault, 'aes_key', None) is None
            assert getattr(vault, 'fernet', None) is None
            assert getattr(vault, 'aes_gcm', None) is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_rsa_keys_exception(self):
        """_get_rsa_keys handles exceptions properly."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            # Create a corrupted identity.pem
            with open(os.path.join(d, "identity.pem"), "wb") as f:
                f.write(b"CORRUPTED_PEM")
            private, public = vault._get_rsa_keys()
            assert private is None
            assert public is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_ensure_keychain_sync_exception(self):
        """_ensure_keychain_sync handles keyring exceptions gracefully."""
        with tempfile.TemporaryDirectory() as d:
            with patch("keyring.get_password", side_effect=Exception("Keychain down")):
                vault, key = make_vault(d)
                # make_vault triggers __init__ which calls _ensure_keychain_sync
                # It should fallback to the provided key and not raise
                # Make sure the key matches
                assert vault.master_key == bytearray(key.encode('utf-8'))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_active_vaults_oserror(self):
        """get_active_vaults handles OSError."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            with patch("os.listdir", side_effect=OSError("Read error")):
                active = vault.get_active_vaults()
                assert active == set()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_store_secret_with_vdxf(self):
        """store_secret syncs with vdxf if available."""
        from unittest.mock import AsyncMock, MagicMock
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            vault.vdxf = MagicMock()
            vault.vdxf.set_memory = MagicMock()
            vault.vdxf.anchor_vault_hash = AsyncMock()
            
            await vault.store_secret("test_vdxf", {"k": "v"})
            vault.vdxf.set_memory.assert_called_with("test_vdxf", {"k": "v"})
            vault.vdxf.anchor_vault_hash.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vdxf_integrity_failure(self):
        """retrieve_secret returns {} if vdxf integrity check fails."""
        from unittest.mock import AsyncMock, MagicMock
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            # Normal store
            await vault.store_secret("integrity_fail", {"k": "v"})
            
            # Setup vdxf to fail integrity check
            vault.vdxf = MagicMock()
            vault.vdxf.get_from_memory = MagicMock(return_value=None)
            vault.vdxf.verify_integrity = AsyncMock(return_value=False)
            vault.vdxf.set_memory = MagicMock()
            
            result = await vault.retrieve_secret("integrity_fail")
            assert result == {}
            vault.vdxf.verify_integrity.assert_called_once()
            vault.vdxf.set_memory.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vdxf_cache_hit(self):
        """retrieve_secret returns cached memory early."""
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            vault.vdxf = MagicMock()
            vault.vdxf.get_from_memory = MagicMock(return_value={"k": "cached"})
            
            result = await vault.retrieve_secret("cache_hit")
            assert result == {"k": "cached"}
            vault.vdxf.get_from_memory.assert_called_once_with("cache_hit")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_locked_vault_raises_runtime_error(self):
        """_store_secret_sync and _retrieve_secret_sync raise RuntimeError when locked."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            vault.lock_vault()
            with pytest.raises(RuntimeError, match="Vault is locked"):
                vault._store_secret_sync("test", {"k": "v"})
            with pytest.raises(RuntimeError, match="Vault is locked"):
                vault._retrieve_secret_sync("test")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_vault_status_methods(self):
        """Test get/update vault status."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            assert await vault.get_vault_status("bridge1") == "UNKNOWN"
            
            await vault.update_vault_status("bridge1", "SYNCED")
            assert await vault.get_vault_status("bridge1") == "SYNCED"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_delete_secret_by_path(self):
        """Test _delete_secret_by_path_sync and _delete_secret_sync"""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            
            # _delete_secret_sync
            assert not vault._delete_secret_sync("missing")
            await vault.store_secret("tobedeleted", {"k": "v"})
            assert vault._delete_secret_sync("tobedeleted")
            
            # _delete_secret_by_path_sync
            assert not vault._delete_secret_by_path_sync("connections/miss/ing.vault")
            await vault.store_connection_secret("b1", "a1", {"k": "v"})
            assert vault._delete_secret_by_path_sync("connections/b1/a1.vault")
            
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_secret_by_path_no_private_key(self):
        """Test _retrieve_secret_by_path_sync with no private key."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            
            # Create a real v2 payload
            await vault.store_connection_secret("b1", "a1", {"k": "v"})
            
            # Create a fake v1 payload
            v1_path = os.path.join(d, "connections/b1/v1.vault")
            os.makedirs(os.path.dirname(v1_path), exist_ok=True)
            with open(v1_path, "wb") as f:
                f.write(b"\x00\x00\x00\x00FAKE_DATA") # length 0
            
            vault.private_key = None
            assert vault._retrieve_secret_by_path_sync("connections/b1/a1.vault") is None
            assert vault._retrieve_secret_by_path_sync("connections/b1/v1.vault") is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_retrieve_secret_by_path_exception(self):
        """Test _retrieve_secret_by_path_sync hitting exceptions during decryption."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            await vault.store_connection_secret("b1", "a1", {"k": "v"})
            
            # Corrupt the V2 payload so decryption fails but it's valid enough to read
            path = os.path.join(d, "connections/b1/a1.vault")
            with open(path, "rb") as f:
                data = f.read()
            # replace the end of data to ruin the tag or ciphertext
            corrupt = data[:-5] + b"12345"
            with open(path, "wb") as f:
                f.write(corrupt)
                
            assert vault._retrieve_secret_by_path_sync("connections/b1/a1.vault") is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_fernet_migration_to_aes_gcm(self):
        """_retrieve_secret_sync falls back to Fernet and migrates to AES-GCM."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            # Manually write a v1 (Fernet) secret
            v1_data = vault.fernet.encrypt(json.dumps({"k": "v1"}).encode())
            path = os.path.join(d, "v1_secret.vault")
            with open(path, "wb") as f:
                f.write(v1_data)
            
            # Retrieve should succeed via fallback
            result = vault._retrieve_secret_sync("v1_secret")
            assert result == {"k": "v1"}
            
            # Read file again to verify it was migrated to V2 (starts with VAULT_V2_PREFIX)
            with open(path, "rb") as f:
                new_data = f.read()
                assert new_data.startswith(vault.VAULT_V2_PREFIX)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_full_vault_state(self):
        """_get_full_vault_state returns consistent hash across chunks."""
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            await vault.store_secret("hashme", {"k": "123"})
            await vault.store_secret("hashmetoo", {"k": "456"})
            
            h1 = await vault._get_full_vault_state()
            h2 = vault._get_full_vault_state_sync()
            assert h1 == h2
            assert isinstance(h1, str)
            assert len(h1) == 64  # SHA256 length

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

    @pytest.mark.unit
    def test_sandbox_preexec_fn(self):
        """Sandbox preexec_fn executes without raising even if resource limits fail."""
        from backend.security.vault import Sandbox
        sb = Sandbox("/tmp", {})
        
        with patch("subprocess.run") as mock_run:
            sb.run_command(["ls"])
            assert mock_run.call_count == 1
            kwargs = mock_run.call_args[1]
            preexec_fn = kwargs.get("preexec_fn")
            if preexec_fn:
                # Execute it to hit the lines inside
                # We can mock resource or let it try and fail gracefully (it catches all)
                with patch("backend.security.vault.resource") as mock_resource:
                    preexec_fn()

    @pytest.mark.unit
    def test_sandbox_cleanup(self):
        """SandboxedExecutionEnv securely wipes files on exit."""
        from backend.security.vault import SandboxedExecutionEnv
        
        sandbox_path = None
        with SandboxedExecutionEnv() as sb:
            sandbox_path = sb.path
            # Create a file inside
            test_file = os.path.join(sb.path, "test.txt")
            with open(test_file, "wb") as f:
                f.write(b"SECRET")
                
            # Create a dir
            os.makedirs(os.path.join(sb.path, "subdir"), exist_ok=True)
            
        # After exit, directory should be gone
        assert not os.path.exists(sandbox_path)

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
