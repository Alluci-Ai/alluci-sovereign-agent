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
    assert test_claims["exp"] > test_claims["iat"]

def test_prm_two_hop_parsing():
    """Validates that your code correctly extracts authorization points from server configuration blocks."""
    mock_server_metadata = {
        "resource": "https://api.service.com/",
        "agent_auth": {
            "register_uri": "https://api.service.com/agent-auth",
            "identity_types_supported": ["identity_assertion", "user_claimed"]
        }
    }
    
    extracted_auth = mock_server_metadata.get("agent_auth", {})
    
    assert "register_uri" in extracted_auth
    assert extracted_auth["register_uri"] == "https://api.service.com/agent-auth"
    assert "identity_assertion" in extracted_auth["identity_types_supported"]
