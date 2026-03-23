
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from ..config import load_settings

settings = load_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    # Default to 24 hours for local sovereign agent usage
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    # Use dedicated JWT secret — NOT the vault master key
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verifies a JWT token signature and returns the payload."""
    try:
        # SEC-004: Added 60s leeway for clock skew between agent and client
        payload = jwt.decode(
            token, 
            settings.JWT_SECRET_KEY, 
            algorithms=["HS256"],
            options={"leeway": 60}
        )
        if payload.get("sub") is None:
            raise JWTError("Missing subject")
        return payload
    except JWTError:
        raise

async def verify_authenticated(request: Request, token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # If header is missing or empty, check cookies
    if not token or token == "undefined":
        token = request.cookies.get("alluci_daemon_token")
    
    if not token:
        raise credentials_exception

    try:
        verify_token(token)
    except JWTError:
        raise credentials_exception
    return True
