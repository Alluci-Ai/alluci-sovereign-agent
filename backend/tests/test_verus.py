import pytest
import json
import hashlib
from unittest.mock import AsyncMock, patch, MagicMock
from backend.security.verus import SovereignIdentity

@pytest.fixture
def mock_settings():
    settings = MagicMock()
    settings.VERUS_ID_IDENTITY = "test_id"
    # Provide a valid 32-byte hex seed (64 chars) for Ed25519
    settings.VERUS_ID_PRIVATE_KEY = "0" * 64
    return settings

@pytest.fixture
def mock_vault():
    vault = AsyncMock()
    return vault

def test_init_ed25519(mock_settings, mock_vault):
    identity = SovereignIdentity(settings=mock_settings, vault=mock_vault)
    assert identity.enabled is True
    assert identity.verus_id == "test_id"
    assert identity._private_key is not None

def test_init_fallback_hash(mock_settings):
    mock_settings.VERUS_ID_PRIVATE_KEY = "invalid_hex"
    identity = SovereignIdentity(settings=mock_settings)
    assert identity.enabled is True
    assert identity._private_key is None

def test_init_inactive(mock_settings):
    mock_settings.VERUS_ID_IDENTITY = None
    identity = SovereignIdentity(settings=mock_settings)
    assert identity.enabled is False

@pytest.mark.asyncio
async def test_load_keys_from_vault(mock_settings, mock_vault):
    mock_settings.VERUS_ID_PRIVATE_KEY = None
    mock_vault.retrieve_secret.return_value = {"private_key": "1" * 64}
    
    identity = SovereignIdentity(settings=mock_settings, vault=mock_vault)
    assert identity._private_key is None
    
    await identity.load_keys()
    assert identity._private_key is not None
    assert identity.private_key_hex == "1" * 64

@pytest.mark.asyncio
async def test_load_keys_exception(mock_settings, mock_vault):
    mock_settings.VERUS_ID_PRIVATE_KEY = None
    mock_vault.retrieve_secret.side_effect = Exception("vault error")
    
    identity = SovereignIdentity(settings=mock_settings, vault=mock_vault)
    await identity.load_keys()
    assert identity._private_key is None

def test_sign_and_verify_manifest_ed25519(mock_settings):
    identity = SovereignIdentity(settings=mock_settings)
    manifest = {"action": "test", "value": 1}
    
    signed = identity.sign_manifest(manifest)
    assert signed["method"] == "ED25519_VDXF_V1"
    assert "signature" in signed
    assert "publicKey" in signed
    
    assert identity.verify_manifest(signed) is True

def test_sign_and_verify_manifest_hash(mock_settings):
    mock_settings.VERUS_ID_PRIVATE_KEY = "invalid"
    identity = SovereignIdentity(settings=mock_settings)
    manifest = {"action": "test", "value": 1}
    
    signed = identity.sign_manifest(manifest)
    assert signed["method"] == "SHA256"
    
    assert identity.verify_manifest(signed) is True

def test_verify_manifest_invalid_hash(mock_settings):
    mock_settings.VERUS_ID_PRIVATE_KEY = "invalid"
    identity = SovereignIdentity(settings=mock_settings)
    signed = {
        "manifest": {"a": 1},
        "method": "SHA256",
        "signature": "bad_sig"
    }
    assert identity.verify_manifest(signed) is False

def test_verify_manifest_invalid_ed25519(mock_settings):
    identity = SovereignIdentity(settings=mock_settings)
    signed = {
        "manifest": {"a": 1},
        "method": "ED25519_VDXF_V1",
        "publicKey": "0" * 64,
        "signature": "bad_sig"
    }
    assert identity.verify_manifest(signed) is False

def test_verify_manifest_unknown_method(mock_settings):
    identity = SovereignIdentity(settings=mock_settings)
    signed = {
        "manifest": {"a": 1},
        "method": "UNKNOWN",
        "signature": "sig"
    }
    assert identity.verify_manifest(signed) is False
