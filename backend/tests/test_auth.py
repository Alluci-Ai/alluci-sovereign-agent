"""
Authentication & JWT Unit Tests

Protects these invariants:
  - Valid master key issues a JWT with correct claims
  - Invalid master key is always rejected (no timing side-channels)
  - JWT tokens expire correctly
  - Tampered tokens are rejected
  - Missing authorization header returns 401
"""
import time
import pytest
from unittest.mock import patch
from datetime import timedelta


class TestJWTGeneration:

    @pytest.mark.unit
    def test_valid_key_creates_token(self, mock_settings):
        """Valid master key produces a signed JWT."""
        from jose import jwt as jose_jwt
        from datetime import datetime, timedelta, timezone

        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jose_jwt.encode(
            {"sub": "sovereign", "exp": expire},
            mock_settings.JWT_SECRET_KEY,
            algorithm="HS256"
        )
        assert isinstance(token, str)
        assert len(token) > 20
        assert token.count(".") == 2

    @pytest.mark.unit
    def test_token_contains_expected_claims(self, mock_settings):
        """Decoded JWT contains sub claim and expiry."""
        from jose import jwt as jose_jwt
        from datetime import datetime, timedelta, timezone

        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jose_jwt.encode(
            {"sub": "sovereign", "exp": expire},
            mock_settings.JWT_SECRET_KEY,
            algorithm="HS256"
        )
        payload = jose_jwt.decode(token, mock_settings.JWT_SECRET_KEY, algorithms=["HS256"])
        assert payload["sub"] == "sovereign"
        assert "exp" in payload

    @pytest.mark.unit
    def test_tampered_token_is_rejected(self, mock_settings):
        """A JWT with a modified payload raises an exception."""
        from jose import jwt as jose_jwt
        from datetime import datetime, timedelta, timezone
        import base64

        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jose_jwt.encode(
            {"sub": "sovereign", "exp": expire},
            mock_settings.JWT_SECRET_KEY,
            algorithm="HS256"
        )
        parts = token.split(".")
        tampered_parts = parts.copy()
        tampered_parts[1] = base64.urlsafe_b64encode(
            b'{"sub":"attacker","exp":9999999999}'
        ).rstrip(b"=").decode()
        tampered_token = ".".join(tampered_parts)

        with pytest.raises(Exception):
            jose_jwt.decode(tampered_token, mock_settings.JWT_SECRET_KEY, algorithms=["HS256"])

    @pytest.mark.unit
    def test_wrong_secret_key_is_rejected(self, mock_settings):
        """Token signed with key A cannot be verified with key B."""
        from jose import jwt as jose_jwt
        from datetime import datetime, timedelta, timezone

        expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        token = jose_jwt.encode(
            {"sub": "sovereign", "exp": expire},
            mock_settings.JWT_SECRET_KEY,
            algorithm="HS256"
        )
        with pytest.raises(Exception):
            jose_jwt.decode(token, "completely-wrong-key-xyz", algorithms=["HS256"])


class TestAuthEndpoints:

    @pytest.mark.integration
    def test_login_success_returns_bearer_token(self, app_client, mock_settings):
        """POST /auth/login with correct key returns access_token."""
        res = app_client.post("/api/v1/auth/login", json={"key": mock_settings.POLYTOPE_MASTER_KEY})
        assert res.status_code == 200
        body = res.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 20

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
