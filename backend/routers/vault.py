
import logging
from ..logging_config import get_logger
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from ..security.auth import verify_authenticated
from ..security.utils import log_system_event
from .. import services
from fastapi_limiter.depends import RateLimiter
from fastapi_csrf_protect import CsrfProtect
from ..config import settings

logger = get_logger("VaultRouter")
MASK = "••••••••••••"

router = APIRouter(tags=["Vault Operations"])

@router.post("/vault/rotate", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=10, minutes=1))])
async def rotate_vault_keys(request: Request, payload: Dict[str, str] = Body(...),
    csrf_protect: CsrfProtect = Depends(),):
    await csrf_protect.validate_csrf(request)
    """[ ROTATE_KEYS ] Instantly re-encrypts all vaults with a new key."""
    new_key = payload.get("new_key")
    if not new_key:
        raise HTTPException(status_code=400, detail="Missing new_key")
    
    if not services.vault:
        raise HTTPException(status_code=503, detail="Vault not ready")

    success = await services.vault.rotate_keys(new_key)
    if not success:
        await log_system_event("VAULT_ROTATE", "Failed to rotate vault keys.", "ERROR")
        raise HTTPException(status_code=500, detail="Vault key rotation failed")
    
    await log_system_event("VAULT_ROTATE", "All Active Vaults Cryptographically Rotated", "SUCCESS")
    return {"status": "success", "message": "All Active Vaults Cryptographically Rotated"}

@router.post("/vault/flush", dependencies=[Depends(verify_authenticated)])
async def flush_vault():
    if not services.vault:
        raise HTTPException(status_code=503, detail="Vault not ready")
    await services.vault.flush_cache()
    return {"status": "success", "message": "Cache flushed."}

@router.post("/check-health", dependencies=[Depends(verify_authenticated)])
async def check_health():
    """Triggers a health check across all model manifolds."""
    if not services.router:
        raise HTTPException(status_code=503, detail="Router not ready")
    results = await services.router.check_health()
    if services.vault:
        for provider, status in results.items():
            await services.vault.update_vault_status(provider, status)
    return {"status": "success", "results": results}

@router.get("/vault/keys", dependencies=[Depends(verify_authenticated)])
async def get_vault_keys():
    """Retrieves masked API keys for UI display. Prevents raw secret exposure."""
    if not services.vault:
        return {}
    try:
        keys = await services.vault.retrieve_secret("alluci_api_keys") or {}
        masked = {}
        for cat, providers in keys.items():
            if isinstance(providers, dict):
                masked[cat] = {k: MASK if v else "" for k, v in providers.items()}
            else:
                masked[cat] = providers
        return masked
    except Exception as e:
        logger.error(f"Failed to retrieve vault keys: {e}")
        return {}

@router.post("/vault/keys", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def save_vault_keys(new_keys: Dict[str, Any] = Body(...)):
    """Persists API keys, merging with existing values to preserve masked secrets."""
    if not services.vault:
        raise HTTPException(status_code=503, detail="Vault not ready")
    try:
        existing = await services.vault.retrieve_secret("alluci_api_keys") or {}
        
        # Deep merge: if new value is MASK, use existing value
        merged = {}
        categories = ["llm", "audio", "music", "image", "video"]
        for cat in categories:
            merged[cat] = {}
            ex_cat = existing.get(cat, {})
            nw_cat = new_keys.get(cat, {})
            
            all_providers = set(list(ex_cat.keys()) + list(nw_cat.keys()))
            for k in all_providers:
                nw_val = nw_cat.get(k)
                if nw_val == MASK:
                    merged[cat][k] = ex_cat.get(k, "")
                else:
                    merged[cat][k] = nw_val
                    
        await services.vault.store_secret("alluci_api_keys", merged)
        return {"status": "SUCCESS", "message": "API Manifold Persisted to Vault."}
    except Exception as e:
        logger.error(f"Failed to store vault keys: {e}")
        raise HTTPException(status_code=500, detail="Vault storage failure.")
