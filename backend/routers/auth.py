
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Response
from typing import Dict, Any
import hmac
from ..config import settings
from ..models import LoginRequest
from ..security.auth import create_access_token, verify_authenticated
from ..security.verusid_auth import verus_auth
from fastapi_limiter.depends import RateLimiter
from ..logging_config import get_logger
from ..security.credential_store import credential_store
from ..security.oauth_config import get_provider_config, get_client_credentials
from ..security.oauth_store import oauth_store
import secrets
import os
import urllib.parse

logger = get_logger("AuthRouter")

from ..security.oauth_config import get_provider_config, get_client_credentials
from ..security.oauth_store import oauth_store
import secrets
import os
import urllib.parse

from fastapi_csrf_protect import CsrfProtect
router = APIRouter(tags=["Authentication"])

@router.get("/auth/csrf-token")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
    """Generates a CSRF token for the frontend to include in subsequent mutations."""
    token, result = csrf_protect.generate_csrf_tokens()
    return {"status": "SUCCESS", "token": token}

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
            secure=settings.APP_ENV != "development",
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400  # 24 hours
        )
        response.set_cookie(
            key="alluci_session",
            value="1",
            httponly=False,
            secure=settings.APP_ENV != "development",
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        return {"access_token": token, "token_type": "bearer", "status": "SUCCESS"}
    
    raise HTTPException(status_code=401, detail="Invalid Sovereign Master Key")

@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(settings.AUTH_COOKIE_NAME)
    response.delete_cookie("alluci_session")
    return {"status": "SUCCESS", "message": "Logged out."}

@router.get("/auth/verusid/challenge")
async def get_verusid_challenge(identity: str = Query("")):
    """Generates a login challenge for Verus Mobile scan."""
    if not settings.VERUS_AUTH_ENABLED:
        raise HTTPException(status_code=501, detail="VerusID Authentication not enabled")
    return verus_auth.create_login_challenge(identity)

@router.post("/auth/verusid/callback", dependencies=[Depends(RateLimiter(times=20, minutes=1))])
async def verusid_callback(response: Response, payload: Dict[str, str] = Body(...)):
    """Verifies the signed challenge and issues a JWT."""
    identity = payload.get("identity")
    signature = payload.get("signature")
    challenge_id = payload.get("challenge_id")
    
    if not all([identity, signature, challenge_id]):
        raise HTTPException(status_code=400, detail="Missing identity, signature, or challenge_id")
    
    is_valid = await verus_auth.verify_login_response({"identity": identity, "signature": signature, "challenge_id": challenge_id})
    if is_valid:
        token = create_access_token(data={"sub": identity, "vauth": True})
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.APP_ENV != "development",
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        response.set_cookie(
            key="alluci_session",
            value="1",
            httponly=False,
            secure=settings.APP_ENV != "development",
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        return {"access_token": token, "token_type": "bearer", "identity": identity}
    
    raise HTTPException(status_code=401, detail="VerusID signature verification failed")

@router.get("/wallet/login/status/{challenge_id}")
async def get_wallet_login_status(challenge_id: str):
    """Polls for the result of a specific login challenge."""
    result = await verus_auth.get_login_status(challenge_id)
    if result:
        return result
    return {"status": "pending"}
@router.get("/auth/webauthn/challenge")
async def get_webauthn_challenge():
    """Generates a cryptographic challenge for WebAuthn/FIDO2."""
    from ..security.webauthn_store import webauthn_store
    challenge_id, b64_challenge = await webauthn_store.create_challenge()

    return {
        "challengeId": challenge_id,          # browser sends this back on verify
        "challenge": b64_challenge,
        "timeout": 120_000,                   # 2 minutes, matches TTL
        "rp": {
            "name": "Alluci Sovereign Agent",
            "id": getattr(settings, "WEBAUTHN_RP_ID", "localhost"),
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
async def verify_webauthn_response(response: Response, payload: Dict[str, Any] = Body(...)):
    """Verifies the WebAuthn attestation/assertion using py_webauthn."""
    from ..security.webauthn_store import webauthn_store
    import base64
    
    try:
        from webauthn import verify_registration_response
        from webauthn.helpers.structs import RegistrationCredential
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="WebAuthn library not installed. Run: pip install webauthn>=2.0.0"
        )

    challenge_id = payload.get("challengeId")
    credential_id = payload.get("id")
    raw_id = payload.get("rawId")
    response_data = payload.get("response", {})

    if not all([challenge_id, credential_id, raw_id,
                response_data.get("attestationObject"),
                response_data.get("clientDataJSON")]):
        raise HTTPException(status_code=400, detail="Missing required WebAuthn fields")

    # Atomically consume the challenge — prevents replay
    expected_challenge = await webauthn_store.consume_challenge(challenge_id)
    if expected_challenge is None:
        raise HTTPException(status_code=400, detail="Challenge not found or expired.")

    rp_id = getattr(settings, "WEBAUTHN_RP_ID", "localhost")
    expected_origin = getattr(settings, "WEBAUTHN_ORIGIN", "http://localhost:5173")

    try:
        credential = RegistrationCredential(
            id=credential_id,
            raw_id=base64.urlsafe_b64decode(raw_id + "=="),
            response={
                "attestation_object": base64.urlsafe_b64decode(
                    response_data["attestationObject"] + "=="
                ),
                "client_data_json": base64.urlsafe_b64decode(
                    response_data["clientDataJSON"] + "=="
                ),
            },
            type="public-key",
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
            secure=settings.APP_ENV != "development",
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400
        )
        response.set_cookie(
            key="alluci_session",
            value="1",
            httponly=False,
            secure=settings.APP_ENV != "development",
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
async def get_webauthn_assertion_challenge(payload: Dict[str, Any] = Body(default={})):
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
            for cid in credential_store.list_credentials()
        ]

    return {
        "challengeId": challenge_id,
        "challenge": b64_challenge,
        "timeout": 120_000,
        "rpId": getattr(settings, "WEBAUTHN_RP_ID", "localhost"),
        "allowCredentials": allow_credentials,
        "userVerification": "preferred",
    }


@router.post(
    "/auth/webauthn/assertion/verify",
    dependencies=[Depends(RateLimiter(times=10, minutes=1))],
)
async def verify_webauthn_assertion(
    response: Response, payload: Dict[str, Any] = Body(...)
):
    """
    Step 2 of WebAuthn login: verify the signed assertion and issue a JWT.
    This is the login path — uses verify_authentication_response.
    """
    from ..security.webauthn_store import webauthn_store
    import base64

    try:
        from webauthn import verify_authentication_response
        from webauthn.helpers.structs import AuthenticationCredential
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="WebAuthn library not installed. Run: pip install webauthn>=2.0.0",
        )

    challenge_id = payload.get("challengeId")
    credential_id = payload.get("id")
    raw_id = payload.get("rawId")
    response_data = payload.get("response", {})

    if not all(
        [
            challenge_id,
            credential_id,
            raw_id,
            response_data.get("authenticatorData"),
            response_data.get("clientDataJSON"),
            response_data.get("signature"),
        ]
    ):
        raise HTTPException(status_code=400, detail="Missing required assertion fields")

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

    rp_id = getattr(settings, "WEBAUTHN_RP_ID", "localhost")
    expected_origin = getattr(settings, "WEBAUTHN_ORIGIN", "http://localhost:5173")

    try:

        def _pad(s: str) -> str:
            return s + "=" * (-len(s) % 4)

        credential = AuthenticationCredential(
            id=credential_id,
            raw_id=base64.urlsafe_b64decode(_pad(raw_id)),
            response={
                "authenticator_data": base64.urlsafe_b64decode(
                    _pad(response_data["authenticatorData"])
                ),
                "client_data_json": base64.urlsafe_b64decode(
                    _pad(response_data["clientDataJSON"])
                ),
                "signature": base64.urlsafe_b64decode(_pad(response_data["signature"])),
            },
            type="public-key",
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
            secure=settings.APP_ENV != "development",
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400,
        )
        response.set_cookie(
            key="alluci_session",
            value="1",
            httponly=False,
            secure=settings.APP_ENV != "development",
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
    daemon_url = os.getenv("DAEMON_PUBLIC_URL", "http://localhost:8000").rstrip("/")
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

