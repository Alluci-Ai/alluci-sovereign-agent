import pytest
pytestmark = pytest.mark.unit

# -*- coding: utf-8 -*-
"""
Test suite for backend/auth/autonomous_discoverer.py
Ensures core discovery and registration flows behave correctly under mocked network and vault interactions.
"""

from unittest.mock import AsyncMock, patch

from backend.auth.autonomous_discoverer import AlluciAutonomousDiscoverer

# Helper mock response class
class MockResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
    def json(self):
        return self._json

@pytest.mark.asyncio
async def test_discover_and_register_fallback_to_auth_md():
    # Simulate PRM 404 then auth.md 200
    mock_prm = MockResponse(status_code=404)
    mock_auth_md = MockResponse(status_code=200, json_data={})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.side_effect = [mock_prm, mock_auth_md]

    discoverer = AlluciAutonomousDiscoverer(manifest_path="dummy")
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await discoverer.discover_and_register("https://example.com")
    assert result == {"flow_type": "user_claimed_otp", "status": "awaiting_user_token_input"}

@pytest.mark.asyncio
async def test_discover_and_register_agent_verified_handshake_success():
    # Mock PRM response with proper agent_auth config
    agent_auth_cfg = {
        "register_uri": "https://example.com/register",
        "identity_types_supported": ["identity_assertion"]
    }
    prm_response = MockResponse(status_code=200, json_data={"agent_auth": agent_auth_cfg})
    post_response = MockResponse(status_code=201, json_data={"token": "abc123"})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = prm_response
    mock_client.__aenter__.return_value.post.return_value = post_response

    # Mock vault keypair retrieval
    mock_vault = AsyncMock()
    mock_vault.get_or_create_jwt_keypair.return_value = ("---PRIVATE KEY---", "---PUBLIC KEY---")

    discoverer = AlluciAutonomousDiscoverer(manifest_path="dummy")
    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("backend.services.vault", mock_vault), \
         patch("jwt.encode", return_value="signed.jwt"):
        result = await discoverer.discover_and_register("https://example.com")
    assert result == {"token": "abc123"}

@pytest.mark.asyncio
async def test_discover_and_register_no_agent_auth_fallback():
    # PRM returns 200 but without agent_auth config
    prm_response = MockResponse(status_code=200, json_data={})
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.get.return_value = prm_response

    discoverer = AlluciAutonomousDiscoverer(manifest_path="dummy")
    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await discoverer.discover_and_register("https://example.com")
    assert result == {"flow_type": "user_claimed_otp", "status": "awaiting_user_token_input"}

@pytest.mark.asyncio
async def test_execute_agent_verified_handshake_failure_raises():
    # Mock client post returning error status
    post_response = MockResponse(status_code=400, text="Bad Request")
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value.post.return_value = post_response

    # Mock vault for keypair
    mock_vault = AsyncMock()
    mock_vault.get_or_create_jwt_keypair.return_value = ("---PRIVATE KEY---", "---PUBLIC KEY---")

    discoverer = AlluciAutonomousDiscoverer(manifest_path="dummy")
    with patch("backend.services.vault", mock_vault), \
         patch("jwt.encode", return_value="signed.jwt"):
        with pytest.raises(ConnectionRefusedError):
            await discoverer.execute_agent_verified_handshake(
                mock_client.__aenter__.return_value,
                "https://example.com/register",
                "example.com"
            )
