
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Response
from typing import Dict
import hmac
from ..config import settings
from ..models import LoginRequest
from ..security.auth import create_access_token
from ..security.verusid_auth import verus_auth

router = APIRouter(tags=["Authentication"])

@router.post("/auth/login")
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

@router.post("/auth/verusid/callback")
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
