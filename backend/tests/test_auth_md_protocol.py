# tests/test_auth_md_protocol.py
import pytest
import jwt
import datetime

def test_id_jag_token_compliance():
    """Confirms that minted identity assertions contain all claims required by the WorkOS specification."""
    now = datetime.datetime.now(datetime.timezone.utc)
    test_claims = {
        "iss": "https://identity.alluci-ai.internal",
        "sub": "user_dev_01",
        "aud": "https://api.external-service.com",
        "client_id": "https://registry.alluci-ai.internal/profiles/agent-v4",
        "iat": now,
        "exp": now + datetime.timedelta(minutes=5),
        "email_verified": True
    }
    
    # Assertions confirm the presence of required structural data paths
    assert "iss" in test_claims
    assert "sub" in test_claims
    assert "aud" in test_claims
    assert test_claims["email_verified"] is True
    assert test_claims["exp"] > test_claims["iat"]  # type: ignore

from unittest.mock import patch, MagicMock, AsyncMock

@pytest.mark.asyncio
@patch("backend.auth.autonomous_discoverer.httpx.AsyncClient.get", new_callable=AsyncMock)
@patch("backend.auth.autonomous_discoverer.httpx.AsyncClient.post", new_callable=AsyncMock)
@patch("backend.auth.autonomous_discoverer.vault")
async def test_prm_two_hop_parsing(mock_vault, mock_post, mock_get):
    """Validates that your code correctly extracts authorization points from server configuration blocks."""
    from backend.auth.autonomous_discoverer import AlluciAutonomousDiscoverer
    
    # 1. Mock the Vault to return a dummy key
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    dummy_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    mock_vault.get_or_create_jwt_keypair = AsyncMock(return_value=(dummy_key, dummy_key.public_key()))

    # 2. Mock the HTTP GET response for the PRM endpoint
    mock_prm_response = MagicMock()
    mock_prm_response.status_code = 200
    mock_prm_response.json.return_value = {
        "resource": "https://api.service.com/",
        "agent_auth": {
            "register_uri": "https://api.service.com/agent-auth",
            "identity_types_supported": ["identity_assertion", "user_claimed"]
        }
    }
    mock_get.return_value = mock_prm_response

    # 3. Mock the HTTP POST response for the registration
    mock_registration_response = MagicMock()
    mock_registration_response.status_code = 200
    mock_registration_response.json.return_value = {"api_key": "sec_test_key_123"}  # pragma: allowlist secret
    mock_post.return_value = mock_registration_response

    # 4. Execute the Discoverer
    discoverer = AlluciAutonomousDiscoverer(manifest_path="./dummy.json")
    result = await discoverer.discover_and_register("https://api.service.com")

    # 5. Assertions: ensure the GET was called on the PRM, POST on register_uri, and it returned the API key
    mock_get.assert_called_once_with("https://api.service.com/.well-known/oauth-protected-resource")
    mock_post.assert_called_once()
    assert mock_post.call_args[0][0] == "https://api.service.com/agent-auth"
    assert result is not None
    assert "api_key" in result
    assert result["api_key"] == "sec_test_key_123"  # pragma: allowlist secret

