"""
Unit tests for Security modules: Vault, Auth, DPK.
"""
import pytest
import os
import tempfile
from unittest.mock import patch
from datetime import timedelta
from cryptography.fernet import Fernet


# ═══════════════════════════════════════════════════════════════════
# Vault Tests
# ═══════════════════════════════════════════════════════════════════

class TestVaultManager:
    """Tests for encrypted vault storage."""

    def _make_vault(self, tmpdir):
        from backend.security.vault import VaultManager
        key = Fernet.generate_key().decode()
        with patch('backend.config.settings') as mock_settings:
            mock_settings.VERUS_AUTH_ENABLED = False
            return VaultManager(key, vault_root=tmpdir)

    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self._make_vault(tmpdir)
            data = {"api_key": "sk-test-123", "token": "abc"}
            
            await vault.store_secret("test_bridge", data)
            retrieved = await vault.retrieve_secret("test_bridge")
            
            assert retrieved == data
            assert retrieved["api_key"] == "sk-test-123"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self._make_vault(tmpdir)
            result = await vault.retrieve_secret("nonexistent")
            assert result == {}

    @pytest.mark.asyncio
    async def test_overwrite_existing_secret(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self._make_vault(tmpdir)
            
            await vault.store_secret("bridge", {"key": "old"})
            await vault.store_secret("bridge", {"key": "new"})
            
            result = await vault.retrieve_secret("bridge")
            assert result["key"] == "new"

    @pytest.mark.asyncio
    async def test_get_active_vaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self._make_vault(tmpdir)
            
            await vault.store_secret("bridge_a", {"k": "v"})
            await vault.store_secret("bridge_b", {"k": "v"})
            
            active = vault.get_active_vaults()
            assert "bridge_a" in active
            assert "bridge_b" in active

    @pytest.mark.asyncio
    async def test_delete_secret(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self._make_vault(tmpdir)
            
            await vault.store_secret("to_delete", {"secret": "data"})
            assert await vault.retrieve_secret("to_delete") != {}
            
            result = await vault.delete_secret("to_delete")
            assert result is True
            assert await vault.retrieve_secret("to_delete") == {}

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self._make_vault(tmpdir)
            result = await vault.delete_secret("nope")
            assert result is False

    @pytest.mark.asyncio
    async def test_vault_file_permissions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            vault = self._make_vault(tmpdir)
            await vault.store_secret("perm_test", {"k": "v"})
            
            path = os.path.join(tmpdir, "perm_test.vault")
            mode = os.stat(path).st_mode & 0o777
            # Should be readable/writable by owner only (0o600)
            assert mode == 0o600


# ═══════════════════════════════════════════════════════════════════
# Auth Tests
# ═══════════════════════════════════════════════════════════════════

class TestAuth:
    """Tests for JWT token creation and verification."""

    def test_create_and_decode_token(self, mock_settings):
        from jose import jwt as jose_jwt
        
        with patch('backend.config.settings', mock_settings):
            from backend.security.auth import create_access_token
            
            token = create_access_token({"sub": "sovereign_admin"})
            
            payload = jose_jwt.decode(
                token, mock_settings.JWT_SECRET_KEY, algorithms=["HS256"]
            )
            assert payload["sub"] == "sovereign_admin"
            assert "exp" in payload

    def test_token_expires(self, mock_settings):
        from jose import jwt as jose_jwt
        
        with patch('backend.config.settings', mock_settings):
            from backend.security.auth import create_access_token
            
            # Create token that expires in 1 second
            token = create_access_token(
                {"sub": "sovereign_admin"},
                expires_delta=timedelta(seconds=-1)  # Already expired
            )
            
            with pytest.raises(jose_jwt.ExpiredSignatureError):
                jose_jwt.decode(token, mock_settings.JWT_SECRET_KEY, algorithms=["HS256"])


# ═══════════════════════════════════════════════════════════════════
# DPK Tests
# ═══════════════════════════════════════════════════════════════════

class TestDPK:
    """Tests for the Discrete Projection Kernel manifold validator."""

    def _make_state(self, sig=1, V=4, E=6, F=4, betti=None, psi=0.5):
        from backend.security.dpk import PolytopeState
        return PolytopeState(
            signature_hash=sig,
            vertices_V=V, edges_E=E, faces_F=F,
            betti=betti or [1.0, 0.0, 0.0, 0.0],
            affective_tension_psi=psi
        )

    def test_valid_manifold_passes(self):
        from backend.security.dpk import DiscreteProjectionKernel
        dpk = DiscreteProjectionKernel()
        
        # Tetrahedron: V=4, E=6, F=4, χ=2, Betti(0)=1 → χ from betti=1
        state = self._make_state(V=4, E=6, F=4, betti=[2.0, 0.0, 0.0, 0.0])
        assert dpk.validate_manifold_integrity(state) is True

    def test_unsigned_manifold_blocked(self):
        from backend.security.dpk import DiscreteProjectionKernel
        dpk = DiscreteProjectionKernel()
        
        state = self._make_state(sig=0)
        assert dpk.validate_manifold_integrity(state) is False

    def test_euler_mismatch_blocked(self):
        from backend.security.dpk import DiscreteProjectionKernel
        dpk = DiscreteProjectionKernel()
        
        # Geometric χ = 4-6+4 = 2, Betti χ = 10-0+0-0 = 10 → mismatch of 8
        state = self._make_state(V=4, E=6, F=4, betti=[10.0, 0.0, 0.0, 0.0])
        assert dpk.validate_manifold_integrity(state) is False

    def test_manifold_tearing_detected(self):
        from backend.security.dpk import DiscreteProjectionKernel
        dpk = DiscreteProjectionKernel()
        
        # First state
        state1 = self._make_state(betti=[1.0, 0.0, 0.0, 0.0], psi=0.5)
        dpk.validate_manifold_integrity(state1)
        
        # Sudden jump in Betti numbers with low tension
        state2 = self._make_state(betti=[10.0, 5.0, 3.0, 2.0], psi=0.3)
        assert dpk.validate_manifold_integrity(state2) is False

    def test_authorize_valid(self):
        from backend.security.dpk import DiscreteProjectionKernel
        dpk = DiscreteProjectionKernel()
        
        state = self._make_state(V=4, E=6, F=4, betti=[2.0, 0.0, 0.0, 0.0])
        assert dpk.authorize_execution(state) is True

    def test_authorize_invalid(self):
        from backend.security.dpk import DiscreteProjectionKernel
        dpk = DiscreteProjectionKernel()
        
        state = self._make_state(sig=0)
        assert dpk.authorize_execution(state) is False
