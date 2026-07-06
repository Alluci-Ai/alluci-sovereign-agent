
from ..logging_config import get_logger
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from ..security.auth import verify_authenticated
from ..models import SoulManifest, SoulPreferences, SoulProfileRecord
from ..database import get_session
from sqlmodel import Session, select
from .. import services
from ..security.rate_limit import RateLimiter
from fastapi_csrf_protect import CsrfProtect
from ..config import settings

logger = get_logger("SoulRouter")

router = APIRouter(tags=["Soul Manifest"])

@router.get("/soul/manifest", dependencies=[Depends(verify_authenticated)])
async def get_soul_manifest():
    """Retrieves the current Soul Manifest from VDXF or Vault."""
    from ..verus_wallet import wallet_service
    
    # Try VDXF first (Decentralized/Sovereign source)
    if settings.VERUS_INTEGRATION_MODE != "off":
        manifest = await wallet_service.get_manifest()
        if manifest:
            return manifest

    # Fallback to Vault (Local/Encrypted source)
    if services.vault:
        manifest = await services.vault.retrieve_secret("soul_manifest")
        if manifest:
            return manifest
            
    return SoulManifest()

@router.put("/soul/manifest", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def update_soul_manifest(request: Request, manifest: SoulManifest, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Updates the Soul Manifest in both VDXF and Vault."""
    from ..verus_wallet import wallet_service
    
    # Update local vault
    if services.vault:
        await services.vault.store_secret("soul_manifest", manifest.model_dump(exclude_none=True))
    
    # Update sovereign VDXF (if enabled)
    if settings.VERUS_INTEGRATION_MODE != "off" and settings.VERUS_ID_IDENTITY:
        await wallet_service.update_manifest(manifest.model_dump())
        
    # Invalidate cached soul manifest memory in orchestrator
    if services.orchestrator:
        services.orchestrator._cached_soul = None

    return {"status": "SUCCESS"}

@router.post("/soul/preview", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=5, seconds=60))])
async def preview_soul_response(request: Request, prompt: str = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Previews how the current soul manifest would respond to a prompt."""
    if not services.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
    return await services.orchestrator.preview_soul_response(prompt)  # type: ignore

@router.get("/soul/preferences", dependencies=[Depends(verify_authenticated)])
async def get_soul_preferences():
    if services.vault:
        prefs = await services.vault.retrieve_secret("soul_preferences")
        if prefs: return prefs
    return SoulPreferences()

@router.get("/soul/profiles", dependencies=[Depends(verify_authenticated)])
async def list_soul_profiles(session: Session = Depends(get_session)):
    """List all configured Soul Profiles."""
    profiles = session.exec(select(SoulProfileRecord)).all()
    return {"profiles": [p.model_dump() for p in profiles]}

@router.post("/soul/profiles", dependencies=[Depends(verify_authenticated)])
async def create_soul_profile(request: Request, data: dict = Body(...), session: Session = Depends(get_session), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Create a new Soul Profile."""
    profile = SoulProfileRecord(
        name=data.get("name", "New Profile"),
        description=data.get("description", ""),
        manifest=data.get("manifest", {})
    )
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return {"status": "SUCCESS", "profile": profile.model_dump()}

@router.put("/soul/profiles/{profile_id}", dependencies=[Depends(verify_authenticated)])
async def update_soul_profile(request: Request, profile_id: str, data: dict = Body(...), session: Session = Depends(get_session), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Update an existing Soul Profile."""
    profile = session.get(SoulProfileRecord, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if "name" in data:
        profile.name = data["name"]
    if "description" in data:
        profile.description = data["description"]
    if "manifest" in data:
        profile.manifest = data["manifest"]
        
    session.add(profile)
    session.commit()
    session.refresh(profile)
    return {"status": "SUCCESS", "profile": profile.model_dump()}

@router.delete("/soul/profiles/{profile_id}", dependencies=[Depends(verify_authenticated)])
async def delete_soul_profile(request: Request, profile_id: str, session: Session = Depends(get_session), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Delete a Soul Profile."""
    profile = session.get(SoulProfileRecord, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
        
    session.delete(profile)
    session.commit()
    return {"status": "SUCCESS"}
