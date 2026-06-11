import pytest
pytestmark = pytest.mark.unit

from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
import hmac
from backend.routers.auth import router, _pad
from backend.security.auth import verify_authenticated
from backend.config import settings

async def mock_auth():
    return True

app = FastAPI()
app.include_router(router)
app.dependency_overrides[verify_authenticated] = mock_auth

client = TestClient(app)

def test_pad():
    assert _pad("abc") == "abc="
    assert _pad("abcd") == "abcd"

@patch("fastapi_csrf_protect.CsrfProtect.generate_csrf_tokens")
def test_get_csrf_token(mock_generate):
    mock_generate.return_value = ("csrf1", "signed1")
    res = client.get("/auth/csrf-token")
    assert res.status_code == 200
    assert res.json() == {"status": "SUCCESS", "csrf_token": "csrf1"}
    assert "fastapi-csrf-token" in res.cookies

@patch("backend.routers.auth.hmac.compare_digest")
@patch("backend.routers.auth.create_access_token")
def test_login_success(mock_create_token, mock_compare):
    mock_compare.return_value = True
    mock_create_token.return_value = "token"
    res = client.post("/auth/login", json={"key": "master"})
    assert res.status_code == 200
    assert res.json()["access_token"] == "token"
    assert settings.AUTH_COOKIE_NAME in res.cookies
    assert "alluci_session" in res.cookies

@patch("backend.routers.auth.hmac.compare_digest")
def test_login_fail(mock_compare):
    mock_compare.return_value = False
    res = client.post("/auth/login", json={"key": "wrong"})
    assert res.status_code == 401

@patch("fastapi_csrf_protect.CsrfProtect.validate_csrf", new_callable=AsyncMock)
def test_logout(mock_csrf):
    client.cookies.set(settings.AUTH_COOKIE_NAME, "token")
    client.cookies.set("alluci_session", "1")
    res = client.post("/auth/logout")
    assert res.status_code == 200
    assert not res.cookies.get(settings.AUTH_COOKIE_NAME)
    assert not res.cookies.get("alluci_session")

def test_get_verusid_login_request_disabled():
    with patch("backend.routers.auth.settings.VERUS_AUTH_ENABLED", False):
        res = client.get("/auth/verusid/login-request")
        assert res.status_code == 501

@pytest.mark.asyncio
@patch("backend.routers.auth.verus_auth.get_verusid_login_request")
def test_get_verusid_login_request(mock_get):
    with patch("backend.routers.auth.settings.VERUS_AUTH_ENABLED", True):
        mock_get.return_value = {"qr": "code"}
        res = client.get("/auth/verusid/login-request")
        assert res.status_code == 200
        assert res.json() == {"qr": "code"}

@pytest.mark.asyncio
@patch("backend.routers.auth.verus_auth.get_verusid_login_request")
def test_get_verusid_login_request_error(mock_get):
    with patch("backend.routers.auth.settings.VERUS_AUTH_ENABLED", True):
        mock_get.side_effect = Exception("failed")
        res = client.get("/auth/verusid/login-request")
        assert res.status_code == 500

@pytest.mark.asyncio
@patch("backend.routers.auth.verus_auth.get_login_status")
def test_get_verusid_login_status_pending(mock_status):
    mock_status.return_value = None
    res = client.get("/auth/verusid/status/123")
    assert res.status_code == 200
    assert res.json() == {"status": "PENDING"}

@pytest.mark.asyncio
@patch("backend.routers.auth.verus_auth.get_login_status")
@patch("backend.routers.auth.create_access_token")
def test_get_verusid_login_status_success(mock_create_token, mock_status):
    mock_status.return_value = {"identity": "user1"}
    mock_create_token.return_value = "token123"
    res = client.get("/auth/verusid/status/123")
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"
    assert res.json()["identity"] == "user1"
    assert settings.AUTH_COOKIE_NAME in res.cookies

@pytest.mark.asyncio
@patch("backend.routers.auth.verus_auth.verify_login_response")
def test_verusid_webhook(mock_verify):
    mock_verify.return_value = True
    res = client.post("/auth/verusid/webhook", json={"data": "test"})
    assert res.status_code == 200
    assert res.json() == {"status": "accepted"}

@pytest.mark.asyncio
@patch("backend.routers.auth.get_provider_config")
def test_oauth_authorize_not_found(mock_get_provider):
    mock_get_provider.return_value = None
    res = client.get("/auth/oauth/authorize?provider_id=test")
    assert res.status_code == 404

@pytest.mark.asyncio
@patch("backend.routers.auth.get_provider_config")
@patch("backend.routers.auth.get_client_credentials")
def test_oauth_authorize_no_client_id(mock_creds, mock_get_provider):
    mock_get_provider.return_value = {"redirect_path": "/cb"}
    mock_creds.return_value = (None, None)
    res = client.get("/auth/oauth/authorize?provider_id=test")
    assert res.status_code == 500

@pytest.mark.asyncio
@patch("backend.routers.auth.get_provider_config")
@patch("backend.routers.auth.get_client_credentials")
@patch("backend.routers.auth.oauth_store.store_state")
def test_oauth_authorize_success(mock_store, mock_creds, mock_get_provider):
    mock_get_provider.return_value = {"redirect_path": "/cb", "scopes": ["read"], "auth_url": "http://auth", "extra_params": {"prompt": "consent"}}
    mock_creds.return_value = ("client_id", "secret")
    res = client.get("/auth/oauth/authorize?provider_id=test")
    assert res.status_code == 200
    assert "authorize_url" in res.json()
    assert "state" in res.json()
    mock_store.assert_called_once()

@pytest.mark.asyncio
@patch("backend.routers.auth.get_provider_config")
@patch("backend.routers.auth.get_client_credentials")
@patch("backend.routers.auth.oauth_store.store_state")
@patch("backend.security.oauth_handler.OAuthHandler.generate_pkce_pair")
def test_oauth_authorize_pkce(mock_pkce, mock_store, mock_creds, mock_get_provider):
    mock_get_provider.return_value = {"redirect_path": "/cb", "scopes": ["read"], "auth_url": "http://auth", "pkce": True}
    mock_creds.return_value = ("client_id", "secret")
    mock_pkce.return_value = ("verifier", "challenge")
    res = client.get("/auth/oauth/authorize?provider_id=test")
    assert res.status_code == 200
    assert "authorize_url" in res.json()
    assert "code_challenge=challenge" in res.json()["authorize_url"]

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.create_challenge")
def test_get_webauthn_challenge(mock_create_challenge):
    mock_create_challenge.return_value = ("c_id", "c_b64")
    res = client.get("/auth/webauthn/challenge")
    assert res.status_code == 200
    assert res.json()["challengeId"] == "c_id"
    assert res.json()["challenge"] == "c_b64"

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.create_challenge")
@patch("backend.routers.auth.credential_store.list_credentials")
def test_get_webauthn_assertion_challenge(mock_list, mock_create):
    mock_list.return_value = ["cred1"]
    mock_create.return_value = ("c_id", "c_b64")
    res = client.post("/auth/webauthn/assertion/challenge")
    assert res.status_code == 200
    assert res.json()["allowCredentials"][0]["id"] == "cred1"
    
    res = client.post("/auth/webauthn/assertion/challenge", json={"credentialId": "cred2"})
    assert res.status_code == 200
    assert res.json()["allowCredentials"][0]["id"] == "cred2"

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
def test_verify_webauthn_response_invalid(mock_consume):
    res = client.post("/auth/webauthn/verify", json={})
    assert res.status_code == 400
    
    res = client.post("/auth/webauthn/verify", json={"challengeId": "123"})
    assert res.status_code == 400

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
def test_verify_webauthn_response_expired(mock_consume):
    mock_consume.return_value = None
    res = client.post("/auth/webauthn/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "raw1",
        "response": {"attestationObject": "att", "clientDataJSON": "client"}
    })
    assert res.status_code == 400

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
@patch("webauthn.verify_registration_response")
@patch("backend.routers.auth.credential_store.store_credential")
@patch("backend.routers.auth.create_access_token")
def test_verify_webauthn_response_success(mock_token, mock_store, mock_verify, mock_consume):
    mock_consume.return_value = b"challenge"
    mock_verify.return_value = MagicMock(credential_public_key=b"pub", sign_count=0)
    mock_token.return_value = "token"
    res = client.post("/auth/webauthn/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "YmFzZTY0",
        "response": {"attestationObject": "YmFzZTY0", "clientDataJSON": "YmFzZTY0"}
    })
    assert res.status_code == 200
    assert res.json()["token"] == "token"

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
def test_verify_webauthn_assertion_invalid(mock_consume):
    res = client.post("/auth/webauthn/assertion/verify", json={})
    assert res.status_code == 400

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
def test_verify_webauthn_assertion_expired(mock_consume):
    mock_consume.return_value = None
    res = client.post("/auth/webauthn/assertion/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "raw1",
        "response": {"authenticatorData": "auth", "clientDataJSON": "client", "signature": "sig"}
    })
    assert res.status_code == 400

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
@patch("backend.routers.auth.credential_store.get_credential")
def test_verify_webauthn_assertion_unregistered(mock_get, mock_consume):
    mock_consume.return_value = b"challenge"
    mock_get.return_value = None
    res = client.post("/auth/webauthn/assertion/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "YmFzZTY0",
        "response": {"authenticatorData": "YmFzZTY0", "clientDataJSON": "YmFzZTY0", "signature": "YmFzZTY0"}
    })
    assert res.status_code == 401

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
@patch("backend.routers.auth.credential_store.get_credential")
@patch("webauthn.verify_authentication_response")
@patch("backend.routers.auth.credential_store.update_sign_count")
@patch("backend.routers.auth.create_access_token")
def test_verify_webauthn_assertion_success(mock_token, mock_update, mock_verify, mock_get, mock_consume):
    mock_consume.return_value = b"challenge"
    mock_get.return_value = {"public_key": b"pub", "sign_count": 0}
    mock_verify.return_value = MagicMock(new_sign_count=1)
    mock_token.return_value = "token"
    res = client.post("/auth/webauthn/assertion/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "YmFzZTY0",
        "response": {"authenticatorData": "YmFzZTY0", "clientDataJSON": "YmFzZTY0", "signature": "YmFzZTY0"}
    })
    assert res.status_code == 200
    assert res.json()["token"] == "token"

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
def test_verify_webauthn_response_missing_payload(mock_consume):
    res = client.post("/auth/webauthn/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "raw1",
        "response": {"attestationObject": 123, "clientDataJSON": 456}
    })
    assert res.status_code == 400

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
def test_verify_webauthn_assertion_missing_payload(mock_consume):
    res = client.post("/auth/webauthn/assertion/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "raw1",
        "response": {"authenticatorData": 123, "clientDataJSON": 456, "signature": 789}
    })
    assert res.status_code == 400

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
@patch("webauthn.verify_registration_response")
def test_verify_webauthn_response_exception(mock_verify, mock_consume):
    mock_consume.return_value = b"challenge"
    mock_verify.side_effect = Exception("failed")
    res = client.post("/auth/webauthn/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "YmFzZTY0",
        "response": {"attestationObject": "YmFzZTY0", "clientDataJSON": "YmFzZTY0"}
    })
    assert res.status_code == 401

@pytest.mark.asyncio
@patch("backend.security.webauthn_store.webauthn_store.consume_challenge")
@patch("backend.routers.auth.credential_store.get_credential")
@patch("webauthn.verify_authentication_response")
def test_verify_webauthn_assertion_exception(mock_verify, mock_get, mock_consume):
    mock_consume.return_value = b"challenge"
    mock_get.return_value = {"public_key": b"pub", "sign_count": 0}
    mock_verify.side_effect = Exception("failed")
    res = client.post("/auth/webauthn/assertion/verify", json={
        "challengeId": "123",
        "id": "cred1",
        "rawId": "YmFzZTY0",
        "response": {"authenticatorData": "YmFzZTY0", "clientDataJSON": "YmFzZTY0", "signature": "YmFzZTY0"}
    })
    assert res.status_code == 401

def test_verify_webauthn_import_error():
    with patch.dict('sys.modules', {'webauthn': None}):
        res = client.post("/auth/webauthn/verify", json={})
        assert res.status_code == 501
        
        res = client.post("/auth/webauthn/assertion/verify", json={})
        assert res.status_code == 501

@pytest.mark.asyncio
def test_verify_webauthn_assertion_invalid_metadata():
    res = client.post("/auth/webauthn/assertion/verify", json={
        "challengeId": "123",
        "id": 123,
        "rawId": 456
    })
    assert res.status_code == 400

