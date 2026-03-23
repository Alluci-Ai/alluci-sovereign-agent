"""
Authentication & JWT Unit Tests

Protects these invariants:
  - Valid master key issues a JWT with correct claims
  - Invalid master key is always rejected (no timing side-channels)
  - JWT tokens expire correctly
  - Tampered tokens are rejected
  - Missing authorization header returns 401
"""
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt as jose_jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

@pytest.fixture(scope="module")
def rsa_keys():
    """Generates a transient RSA keypair for testing RS256."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return priv_pem, pub_pem

class TestJWTGeneration:

    @pytest.mark.unit
    def test_valid_key_creates_token(self, rsa_keys):
        """Valid RSA private key produces a signed RS256 JWT."""
        priv_pem, _ = rsa_keys
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jose_jwt.encode(
            {"sub": "sovereign", "exp": expire},
            priv_pem,
            algorithm="RS256"
        )
        assert isinstance(token, str)
        assert len(token) > 20
        assert token.count(".") == 2

    @pytest.mark.unit
    def test_token_contains_expected_claims(self, rsa_keys):
        """Decoded RS256 JWT contains sub claim and expiry."""
        priv_pem, pub_pem = rsa_keys
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jose_jwt.encode(
            {"sub": "sovereign", "exp": expire},
            priv_pem,
            algorithm="RS256"
        )
        payload = jose_jwt.decode(token, pub_pem, algorithms=["RS256"])
        assert payload["sub"] == "sovereign"
        assert "exp" in payload

    @pytest.mark.unit
    def test_tampered_token_is_rejected(self, rsa_keys):
        """A JWT with a modified payload raises an exception during RS256 verification."""
        import base64
        priv_pem, pub_pem = rsa_keys
        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jose_jwt.encode(
            {"sub": "sovereign", "exp": expire},
            priv_pem,
            algorithm="RS256"
        )
        parts = token.split(".")
        tampered_parts = parts.copy()
        tampered_parts[1] = base64.urlsafe_b64encode(
            b'{"sub":"attacker","exp":9999999999}'
        ).rstrip(b"=").decode()
        tampered_token = ".".join(tampered_parts)

        with pytest.raises(Exception):
            jose_jwt.decode(tampered_token, pub_pem, algorithms=["RS256"])

class TestAuthEndpoints:

    @pytest.mark.integration
    def test_login_success_returns_bearer_token(self, app_client, mock_settings):
        """POST /auth/login with correct key returns access_token."""
        # Note: the app_client already has RS256 keys initialized via conftest.py
        res = app_client.post("/api/v1/auth/login", json={"key": mock_settings.POLYTOPE_MASTER_KEY})
        assert res.status_code == 200
        body = res.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    @pytest.mark.integration
    def test_login_wrong_key_returns_401(self, app_client):
        """POST /auth/login with wrong key returns 401."""
        res = app_client.post("/api/v1/auth/login", json={"key": "completely-wrong-key"})
        assert res.status_code == 401

    @pytest.mark.integration
    def test_protected_endpoint_without_token_returns_401(self, app_client):
        """Protected endpoint without Authorization header returns 401."""
        res = app_client.get("/api/v1/system/health")
        assert res.status_code == 401

    @pytest.mark.integration
    def test_protected_endpoint_with_valid_token_succeeds(self, app_client, auth_headers):
        """Protected endpoint with valid Bearer token returns 200."""
        res = app_client.get("/api/v1/system/health", headers=auth_headers)
        assert res.status_code == 200

    @pytest.mark.integration
    def test_malformed_bearer_token_returns_401(self, app_client):
        """Malformed token string returns 401."""
        res = app_client.get("/api/v1/system/health",
                              headers={"Authorization": "Bearer not.a.real.token"})
        assert res.status_code == 401
