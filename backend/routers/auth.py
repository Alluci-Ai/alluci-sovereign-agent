
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Response, Request
from typing import Dict, Any
import hmac
from ..config import settings
from ..models import LoginRequest
from ..security.auth import create_access_token, verify_authenticated
from ..security.verusid_auth import verus_auth
from ..security.verus_rpc import verus_rpc
from ..security.rate_limit import RateLimiter
from ..logging_config import get_logger
from ..security.credential_store import credential_store
from ..security.oauth_config import get_provider_config, get_client_credentials
from ..security.oauth_store import oauth_store
import secrets
import os
import urllib.parse

logger = get_logger("AuthRouter")


def _pad(s: str) -> str:
    """Ensure safe base64url padding."""
    s = s.rstrip("=")
    return s + "=" * (-len(s) % 4)



try:
    from fastapi_csrf_protect import CsrfProtect
except ImportError:
    # Minimal stub for CsrfProtect when the package is not installed
    class CsrfProtect:
        def __init__(self, *args, **kwargs):
            pass
        def generate_csrf_tokens(self):
            # Return placeholder tokens
            return ("dummy_csrf_token", "dummy_signed_token")
        async def validate_csrf(self, request):
            # No validation performed in stub
            return None
router = APIRouter(tags=["Authentication"])

@router.get("/auth/csrf-token")
async def get_csrf_token(request: Request, response: Response, csrf_protect: CsrfProtect = Depends()):
    """
    Generates a CSRF token pair.
    Returns the token for use in X-CSRF-Token header.
    Also sets the signed token in a cookie for double-submit validation.
    """
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    # Set the signed token in an HTTP-only cookie
    response.set_cookie(
        key="fastapi-csrf-token",
        value=signed_token,
        httponly=True,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        secure=settings.AUTH_COOKIE_SECURE,
    )
    return {"status": "SUCCESS", "csrf_token": csrf_token}

@router.post("/auth/login", dependencies=[Depends(RateLimiter(times=5, minutes=1))])
async def login(response: Response, payload: LoginRequest):
    """Sovereign Master Key Authentication."""
    if hmac.compare_digest(payload.key, settings.POLYTOPE_MASTER_KEY):
        token = create_access_token(data={"sub": "sovereign_admin"})
        # Set HttpOnly, Secure, SameSite cookie
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400  # 24 hours
        )
        response.set_cookie(
            key="alluci_session",
            value="1",
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        return {"access_token": token, "token_type": "bearer", "status": "SUCCESS"}
    
    raise HTTPException(status_code=401, detail="Invalid Sovereign Master Key")

@router.post("/auth/logout")
async def logout(response: Response, request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    response.delete_cookie(
        key=settings.AUTH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key="alluci_session",
        path="/",
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )
    return {"status": "SUCCESS", "message": "Logged out."}

@router.get("/auth/verusid/login-request")
async def get_verusid_login_request(request: Request):
    """Generates a full LoginConsentRequest with QR deeplink."""
    if settings.VERUS_INTEGRATION_MODE == "off":
        raise HTTPException(status_code=501, detail="VerusID Authentication not enabled")
        
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", str(request.base_url).rstrip("/api/v1"))
    redirect_uri = f"{daemon_url}/api/v1/auth/verusid/webhook"

    try:
        signing_id = settings.VERUS_ID_IDENTITY or "Alluci@"
        if signing_id.endswith("@") or "." in signing_id:
            id_data = await verus_rpc.get_identity(signing_id)
            if id_data and id_data.get("identity"):
                signing_id = id_data["identity"]["identityaddress"]

        result = await verus_auth.get_verusid_login_request(
            signing_id=signing_id,
            redirect_uri=redirect_uri
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/auth/verusid/status/{challenge_id}")
async def get_verusid_login_status(challenge_id: str, response: Response):
    """Checks if a login has been completed for the given challenge_id."""
    status_data = await verus_auth.get_login_status(challenge_id)
    if status_data:
        identity = status_data.get("identity")
        token = create_access_token(data={"sub": identity, "vauth": True})
        
        # Set cookies just like other successful authentication flows
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400,
        )
        response.set_cookie(
            key="alluci_session",
            value="1",
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        
        return {
            "status": "SUCCESS", 
            "identity": identity,
            "access_token": token
        }
    return {"status": "PENDING"}

@router.post("/auth/verusid/webhook")
async def verusid_webhook(payload: Dict[str, Any] = Body(...)):
    """Webhook for Verus Mobile to POST the signed LoginConsentResponse."""
    is_valid = await verus_auth.verify_login_response(payload)
    return {"status": "accepted" if is_valid else "rejected"}

@router.get("/auth/webauthn/challenge")
async def get_webauthn_challenge(request: Request):
    """Generates a cryptographic challenge for WebAuthn/FIDO2."""
    from ..security.webauthn_store import webauthn_store
    challenge_id, b64_challenge = await webauthn_store.create_challenge()

    return {
        "challengeId": challenge_id,          # browser sends this back on verify
        "challenge": b64_challenge,
        "timeout": 120_000,                   # 2 minutes, matches TTL
        "rp": {
            "name": "Alluci Sovereign Agent",
            "id": settings.WEBAUTHN_RP_ID or request.url.hostname,
        },
        "user": {
            "id": "ALLUCI_SOVEREIGN_001",
            "name": "sovereign_admin",
            "displayName": "Sovereign Administrator",
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},   # ES256
            {"type": "public-key", "alg": -257},  # RS256
        ],
    }


@router.post("/auth/webauthn/verify", dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def verify_webauthn_response(request: Request, response: Response, payload: Dict[str, Any] = Body(...)):
    """Verifies the WebAuthn attestation/assertion using py_webauthn."""
    from ..security.webauthn_store import webauthn_store
    import base64
    
    try:
        from webauthn import verify_registration_response
        from webauthn.helpers.structs import (
            RegistrationCredential,
            AuthenticatorAttestationResponse,
            PublicKeyCredentialType,
        )
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="WebAuthn library not installed. Run: pip install webauthn>=2.0.0"
        )

    challenge_id = payload.get("challengeId")
    credential_id = payload.get("id")
    raw_id = payload.get("rawId")
    response_data = payload.get("response", {})

    if not isinstance(challenge_id, str):
        raise HTTPException(status_code=400, detail="Invalid or missing challengeId")

    if not isinstance(credential_id, str) or not isinstance(raw_id, str) or not isinstance(response_data, dict):
        raise HTTPException(status_code=400, detail="Invalid WebAuthn metadata fields")

    attestation_object = response_data.get("attestationObject")
    client_data_json = response_data.get("clientDataJSON")

    if not isinstance(attestation_object, str) or not isinstance(client_data_json, str):
        raise HTTPException(status_code=400, detail="Missing or invalid WebAuthn response payload")

    # Atomically consume the challenge — prevents replay
    expected_challenge = await webauthn_store.consume_challenge(challenge_id)
    if expected_challenge is None:
        raise HTTPException(status_code=400, detail="Challenge not found or expired.")

    rp_id = settings.WEBAUTHN_RP_ID or request.url.hostname or "localhost"
    expected_origin = settings.WEBAUTHN_ORIGIN or f"{request.url.scheme}://{request.url.netloc}"

    try:
        credential = RegistrationCredential(
            id=credential_id,
            raw_id=base64.urlsafe_b64decode(_pad(raw_id)),
            response=AuthenticatorAttestationResponse(
                attestation_object=base64.urlsafe_b64decode(
                    _pad(attestation_object)
                ),
                client_data_json=base64.urlsafe_b64decode(
                    _pad(client_data_json)
                ),
            ),
            type=PublicKeyCredentialType.PUBLIC_KEY,
        )

        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
        )

        logger.info(f"[WEBAUTHN] Verification successful: {credential_id}")

        # Persist the credential so it can be used for future logins
        await credential_store.store_credential(
            credential_id=credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
        )

        token = create_access_token({"sub": "sovereign_admin", "webauthn": True})
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        response.set_cookie(
            key="alluci_session",
            value="1",
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        
        return {
            "status": "SUCCESS",
            "token": token,
            "credential_id": credential_id,
        }

    except Exception as e:
        logger.warning(f"[WEBAUTHN] Verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"WebAuthn verification failed: {type(e).__name__}"
        )


@router.post(
    "/auth/webauthn/assertion/challenge",
    dependencies=[Depends(RateLimiter(times=20, minutes=1))],
)
async def get_webauthn_assertion_challenge(request: Request, payload: Dict[str, Any] = Body(default={})):
    """
    Step 1 of WebAuthn login: generate a challenge for an existing registered credential.
    The browser sends back credentialId (optional) to restrict which credential to use.
    """
    from ..security.webauthn_store import webauthn_store

    credential_id = payload.get("credentialId")
    challenge_id, b64_challenge = await webauthn_store.create_challenge()

    allow_credentials = []
    if credential_id:
        allow_credentials = [{"type": "public-key", "id": credential_id}]
    else:
        # Allow any registered credential
        allow_credentials = [
            {"type": "public-key", "id": cid}
            for cid in await credential_store.list_credentials()
        ]

    return {
        "challengeId": challenge_id,
        "challenge": b64_challenge,
        "timeout": 120_000,
        "rpId": settings.WEBAUTHN_RP_ID or request.url.hostname,
        "allowCredentials": allow_credentials,
        "userVerification": "preferred",
    }


@router.post(
    "/auth/webauthn/assertion/verify",
    dependencies=[Depends(RateLimiter(times=10, minutes=1))],
)
async def verify_webauthn_assertion(
    request: Request, response: Response, payload: Dict[str, Any] = Body(...)
):
    """
    Step 2 of WebAuthn login: verify the signed assertion and issue a JWT.
    This is the login path — uses verify_authentication_response.
    """
    from ..security.webauthn_store import webauthn_store
    import base64

    try:
        from webauthn import verify_authentication_response
        from webauthn.helpers.structs import (
            AuthenticationCredential,
            AuthenticatorAssertionResponse,
            PublicKeyCredentialType,
        )
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="WebAuthn library not installed. Run: pip install webauthn>=2.0.0",
        )

    challenge_id = payload.get("challengeId")
    credential_id = payload.get("id")
    raw_id = payload.get("rawId")
    response_data = payload.get("response", {})

    if not isinstance(challenge_id, str):
        raise HTTPException(status_code=400, detail="Invalid or missing challengeId")

    if not isinstance(credential_id, str) or not isinstance(raw_id, str) or not isinstance(response_data, dict):
        raise HTTPException(status_code=400, detail="Invalid WebAuthn metadata fields")

    authenticator_data = response_data.get("authenticatorData")
    client_data_json = response_data.get("clientDataJSON")
    signature = response_data.get("signature")

    if not isinstance(authenticator_data, str) or not isinstance(client_data_json, str) or not isinstance(signature, str):
        raise HTTPException(status_code=400, detail="Missing or invalid WebAuthn assertion payload")

    # Atomically consume the challenge — prevents replay attacks
    expected_challenge = await webauthn_store.consume_challenge(challenge_id)
    if expected_challenge is None:
        raise HTTPException(status_code=400, detail="Challenge not found or expired.")

    # Retrieve the stored credential
    stored_credential = await credential_store.get_credential(credential_id)
    if not stored_credential:
        raise HTTPException(
            status_code=401,
            detail="Credential not registered. Please register your passkey first.",
        )

    rp_id = settings.WEBAUTHN_RP_ID or request.url.hostname or "localhost"
    expected_origin = settings.WEBAUTHN_ORIGIN or f"{request.url.scheme}://{request.url.netloc}"

    try:
        credential = AuthenticationCredential(
            id=credential_id,
            raw_id=base64.urlsafe_b64decode(_pad(raw_id)),
            response=AuthenticatorAssertionResponse(
                authenticator_data=base64.urlsafe_b64decode(
                    _pad(authenticator_data)
                ),
                client_data_json=base64.urlsafe_b64decode(
                    _pad(client_data_json)
                ),
                signature=base64.urlsafe_b64decode(_pad(signature)),
            ),
            type=PublicKeyCredentialType.PUBLIC_KEY,
        )

        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
            credential_public_key=stored_credential["public_key"],
            credential_current_sign_count=stored_credential["sign_count"],
        )

        # Update sign counter to prevent replay
        await credential_store.update_sign_count(
            credential_id, verification.new_sign_count
        )

        logger.info(f"[WEBAUTHN] Assertion verified: {credential_id[:16]}...")
        token = create_access_token({"sub": "sovereign_admin", "webauthn": True})

        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400,
        )
        response.set_cookie(
            key="alluci_session",
            value="1",
            httponly=True,
            secure=settings.AUTH_COOKIE_SECURE,
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        return {"status": "SUCCESS", "token": token}

    except Exception as e:
        logger.warning(f"[WEBAUTHN] Assertion failed: {e}")
        raise HTTPException(status_code=401, detail=f"Assertion failed: {type(e).__name__}")

@router.get("/auth/oauth/authorize", dependencies=[Depends(verify_authenticated)])
async def oauth_authorize(provider_id: str = Query(...)):
    """Starts an OAuth 2.0 flow for a specific provider."""
    provider = get_provider_config(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider {provider_id} not found")
    
    client_id, _ = get_client_credentials(provider_id)
    if not client_id:
        raise HTTPException(status_code=500, detail=f"Client ID for {provider_id} not configured")
        
    state = secrets.token_urlsafe(32)
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://127.0.0.1:8000").rstrip("/")
    redirect_uri = f"{daemon_url}{provider['redirect_path']}"
    
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(provider["scopes"]),
        "state": state,
    }
    
    if provider.get("extra_params"):
        params.update(provider["extra_params"])
        
    if provider.get("pkce"):
        from ..security.oauth_handler import OAuthHandler
        verifier, challenge = OAuthHandler.generate_pkce_pair()
        params.update({
            "code_challenge": challenge,
            "code_challenge_method": "S256"
        })
        await oauth_store.store_state(state, {"verifier": verifier, "redirect_uri": redirect_uri})
    else:
        await oauth_store.store_state(state, {"redirect_uri": redirect_uri})
        
    authorize_url = f"{provider['auth_url']}?{urllib.parse.urlencode(params)}"
    return {"authorize_url": authorize_url, "state": state}
