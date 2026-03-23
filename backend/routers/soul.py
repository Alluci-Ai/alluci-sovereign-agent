
import logging
from ..logging_config import get_logger
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from ..security.auth import verify_authenticated
from ..models import SoulManifest, SoulPreferences
from .. import services
from fastapi_limiter.depends import RateLimiter
from fastapi_csrf_protect import CsrfProtect
from ..config import settings

logger = get_logger("SoulRouter")

router = APIRouter(tags=["Soul Manifest"])

@router.get("/soul/manifest", dependencies=[Depends(verify_authenticated)])
async def get_soul_manifest():
    """Retrieves the current Soul Manifest."""
    # Logic to load from vault or file
    if services.vault:
        manifest = await services.vault.retrieve_secret("soul_manifest")
        if manifest:
            return manifest
    return SoulManifest()

@router.put("/soul/manifest", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def update_soul_manifest(request: Request, manifest: SoulManifest, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Updates the Soul Manifest."""
    if services.vault:
        await services.vault.store_secret("soul_manifest", manifest.dict())
        return {"status": "SUCCESS"}
    raise HTTPException(status_code=503, detail="Vault not ready")

@router.post("/soul/preview", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=5, seconds=60))])
async def preview_soul_response(request: Request, prompt: str = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Previews how the current soul manifest would respond to a prompt."""
    if not services.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    return await services.orchestrator.preview_soul_response(prompt)

@router.get("/soul/preferences", dependencies=[Depends(verify_authenticated)])
async def get_soul_preferences():
    if services.vault:
        prefs = await services.vault.retrieve_secret("soul_preferences")
        if prefs: return prefs
    return SoulPreferences()
