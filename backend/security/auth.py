
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from ..config import load_settings

settings = load_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

from cryptography.hazmat.primitives import serialization

_jwt_private_key_pem: bytes = b""
_jwt_public_key_pem: bytes = b""

def init_jwt_keys(private_key, public_key):
    """Called once at app startup after VaultManager is initialized."""
    global _jwt_private_key_pem, _jwt_public_key_pem
    _jwt_private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    _jwt_public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    if not _jwt_private_key_pem:
        raise RuntimeError("JWT private key not initialized.")
    return jwt.encode(to_encode, _jwt_private_key_pem, algorithm="RS256")

def verify_token(token: str) -> dict:
    if not _jwt_public_key_pem:
        raise RuntimeError("JWT public key not initialized.")
    try:
        payload = jwt.decode(
            token, 
            _jwt_public_key_pem, 
            algorithms=["RS256"],
            options={"leeway": 60}
        )
        if payload.get("sub") is None:
            raise JWTError("Missing subject")
        return payload
    except JWTError:
        raise

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def verify_authenticated(request: Request):
    token: Optional[str] = None
    
    # 1. Check Authorization Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    
    # 2. Check Cookie Fallback
    if not token or token == "undefined":
        token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        verify_token(token)
    except JWTError:
        raise credentials_exception
    return True

async def get_current_user(auth: bool = Depends(verify_authenticated)):
    """
    Dependency that returns the current authenticated user.
    Since we only have one root user for the sovereign agent, we return a fixed record if authenticated.
    """
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"id": "root", "name": "Sovereign User"}
