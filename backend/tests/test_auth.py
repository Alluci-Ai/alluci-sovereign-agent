import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import Request

# Import the module under test
import backend.security.auth as auth_mod

# Helper to create a dummy FastAPI Request
class DummyRequest:
    def __init__(self, headers=None, cookies=None):
        self.headers = headers or {}
        self.cookies = cookies or {}

# Generate dummy RSA keys for testing init_jwt_keys
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()

def test_init_and_create_access_token(monkeypatch):
    """Test that init_jwt_keys stores PEMs and create_access_token uses them."""
    # Ensure globals are reset
    auth_mod._jwt_private_key_pem = b""
    auth_mod._jwt_public_key_pem = b""

    # Initialize keys
    auth_mod.init_jwt_keys(_private_key, _public_key)
    assert auth_mod._jwt_private_key_pem.startswith(b"-----BEGIN PRIVATE KEY")
    assert auth_mod._jwt_public_key_pem.startswith(b"-----BEGIN PUBLIC KEY")

    # Mock jwt.encode to capture payload
    captured = {}
    def fake_encode(to_encode, key, algorithm):
        captured['payload'] = to_encode
        captured['key'] = key
        captured['algorithm'] = algorithm
        return "signed-token"
    monkeypatch.setattr(auth_mod, "jwt", MagicMock(encode=fake_encode))

    token = auth_mod.create_access_token({"sub": "test_user"}, expires_delta=None)
    assert token == "signed-token"
    # Verify payload includes required fields
    payload = captured['payload']
    assert payload["sub"] == "test_user"
    assert "exp" in payload and "iat" in payload
    assert captured['algorithm'] == "RS256"

def test_verify_token_success(monkeypatch):
    """Verify that verify_token returns payload when jwt.decode succeeds."""
    expected_payload = {"sub": "test_user", "exp": 9999999999}
    def fake_decode(token, key, algorithms, options):
        assert token == "signed-token"
        return expected_payload
    monkeypatch.setattr(auth_mod, "jwt", MagicMock(decode=fake_decode))
    # Ensure public key is set
    auth_mod._jwt_public_key_pem = b"dummy-pub"
    payload = auth_mod.verify_token("signed-token")
    assert payload == expected_payload

@pytest.mark.asyncio
async def test_verify_authenticated_header(monkeypatch):
    """Token should be taken from Authorization header and verified."""
    request = DummyRequest(headers={"Authorization": "Bearer mytoken"})
    mock_verify = MagicMock(return_value={"sub": "x"})
    monkeypatch.setattr(auth_mod, "verify_token", mock_verify)
    result = await auth_mod.verify_authenticated(request)
    assert result is True

@pytest.mark.asyncio
async def test_verify_authenticated_cookie(monkeypatch):
    """When no Authorization header, token should be taken from cookie."""
    dummy_settings = MagicMock()
    dummy_settings.AUTH_COOKIE_NAME = "auth_cookie"
    monkeypatch.setattr(auth_mod, "settings", dummy_settings)

    request = DummyRequest(cookies={"auth_cookie": "cookietoken"})
    mock_verify = MagicMock(return_value={"sub": "x"})
    monkeypatch.setattr(auth_mod, "verify_token", mock_verify)
    result = await auth_mod.verify_authenticated(request)
    assert result is True

@pytest.mark.asyncio
async def test_get_current_user(monkeypatch):
    """get_current_user should return a static user dict when auth dependency passes."""
    result = await auth_mod.get_current_user()
    assert result == {"id": "root", "name": "Sovereign User"}
