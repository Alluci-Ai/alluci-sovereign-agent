
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Response
from typing import Dict, Any
import hmac
from ..config import settings
from ..models import LoginRequest
from ..security.auth import create_access_token
from ..security.verusid_auth import verus_auth
from fastapi_limiter.depends import RateLimiter

router = APIRouter(tags=["Authentication"])

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
        return {"access_token": token, "token_type": "bearer", "status": "SUCCESS"}
    
    raise HTTPException(status_code=401, detail="Invalid Sovereign Master Key")

@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie(settings.AUTH_COOKIE_NAME)
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
        return {"access_token": token, "token_type": "bearer", "identity": identity}
    
    raise HTTPException(status_code=401, detail="VerusID signature verification failed")

@router.get("/api/wallet/login/status/{challenge_id}")
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
    import logging
    logger = logging.getLogger("AuthRouter")
    
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

        verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
        )

        logger.info(f"[WEBAUTHN] Verification successful: {credential_id}")
        token = create_access_token({"sub": "sovereign_admin", "webauthn": True})
        
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
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
