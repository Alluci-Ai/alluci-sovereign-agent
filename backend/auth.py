from fastapi import Depends, HTTPException, status, Request
from .security.auth import verify_authenticated

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
