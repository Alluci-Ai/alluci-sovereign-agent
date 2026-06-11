import pytest
pytestmark = pytest.mark.unit

import os
import shutil
import tempfile
import asyncio
from unittest.mock import patch
from backend.security.vault import VaultManager, SandboxedExecutionEnv

def make_vault(tmpdir: str):
    """Helper: create a VaultManager with a fresh test key."""
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    with patch("backend.config.settings") as ms, patch("keyring.get_password", return_value=None), patch("keyring.set_password"):
        ms.VERUS_AUTH_ENABLED = False
        return VaultManager(key, vault_root=tmpdir), key

class TestVaultExtended:
    @pytest.mark.asyncio
    async def test_connection_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            # Store
            await vault.store_connection_secret("bridge_abc", "acct_1", {"token": "123"})
            # Retrieve
            val = await vault.retrieve_connection_secret("bridge_abc", "acct_1")
            assert val == {"token": "123"}
            # List
            conns = await vault.list_connections("bridge_abc")
            assert "acct_1" in conns
            # Delete
            res = await vault.delete_connection_secret("bridge_abc", "acct_1")
            assert res is True
            # List again
            conns = await vault.list_connections("bridge_abc")
            assert "acct_1" not in conns
            
            # Sync variants
            assert vault._list_connections_sync("bridge_abc") == []

    def test_custom_paths(self):
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            vault._store_secret_by_path_sync("my/custom.json", {"a": 1})
            assert vault._retrieve_secret_by_path_sync("my/custom.json") == {"a": 1}
            assert vault._delete_secret_by_path_sync("my/custom.json") is True
            assert vault._retrieve_secret_by_path_sync("my/custom.json") is None

    @pytest.mark.asyncio
    async def test_vault_status(self):
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            await vault.update_vault_status("b1", "active")
            assert await vault.get_vault_status("b1") == "active"
            vault._update_vault_status_sync("b1", "idle")
            assert vault._get_vault_status_sync("b1") == "idle"

    @pytest.mark.asyncio
    async def test_jwt_keypair(self):
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            priv, pub = await vault.get_or_create_jwt_keypair()
            assert priv is not None
            assert pub is not None
            
            # Export
            pem = vault.export_identity_pem("password1234567890")
            assert "-----BEGIN ENCRYPTED PRIVATE KEY-----" in pem

    @pytest.mark.asyncio
    async def test_flush_cache(self):
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            res = await vault.flush_cache()
            assert res is True
            res_sync = vault._flush_cache_sync()
            assert res_sync is True

    def test_lock_vault(self):
        with tempfile.TemporaryDirectory() as d:
            vault, _ = make_vault(d)
            vault.lock_vault()
            # Keys should be wiped
            assert all(x == 0 for x in vault.master_key)

    def test_sandbox_execution(self):
        with SandboxedExecutionEnv() as sandbox:
            res = sandbox.run_command(["echo", "sandbox_test"])
            assert res.returncode == 0
            assert "sandbox_test" in res.stdout
