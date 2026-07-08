
from ..logging_config import get_logger
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from ..security.auth import verify_authenticated
from fastapi_csrf_protect import CsrfProtect
from .. import services

logger = get_logger("MemoryRouter")

router = APIRouter(tags=["Sovereign Memory"])

@router.get("/memory", dependencies=[Depends(verify_authenticated)])
async def list_memory(limit: int = 50, offset: int = 0, tier: int = Query(None)):
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    return await services.memory.list_entries(limit=limit, offset=offset, tier=tier)

@router.get("/memory/search", dependencies=[Depends(verify_authenticated)])
async def search_memory(q: str = Query(...), limit: int = 10):
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    return await services.memory.search(q, limit=limit)

@router.post("/memory/store", dependencies=[Depends(verify_authenticated)])
async def store_memory(request: Request, data: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    content = data.get("content")
    metadata = data.get("metadata", {})
    return await services.memory.store(content=content, metadata=metadata)  # type: ignore

@router.get("/memory/stats", dependencies=[Depends(verify_authenticated)])
async def get_memory_stats():
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    return await services.memory.get_stats()

@router.delete("/memory/{entry_id}", dependencies=[Depends(verify_authenticated)])
async def delete_memory_entry(request: Request, entry_id: str, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    success = await services.memory.delete(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"status": "SUCCESS"}

@router.post("/memory/consolidate", dependencies=[Depends(verify_authenticated)])
async def trigger_consolidation(request: Request, csrf_protect: CsrfProtect = Depends()):
    """Manually trigger the H-LSM consolidation cycle (Decay, Promotion, Pruning)."""
    await csrf_protect.validate_csrf(request)
    if not services.hlsm_manager:
        raise HTTPException(status_code=503, detail="H-LSM manager not ready")
    
    summary = await services.hlsm_manager.consolidation_sweep()
    return {
        "status": "SUCCESS",
        "cycle_summary": summary,
        "message": "H-LSM consolidation sweep completed successfully."
    }

@router.patch("/memory/{entry_id}/pin", dependencies=[Depends(verify_authenticated)])
async def pin_memory(entry_id: str, request: Request, data: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    from sqlmodel import Session
    from ..models import HLSMEpisodicEntry
    from ..database import engine
    
    with Session(engine) as session:
        entry = session.get(HLSMEpisodicEntry, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        metadata = dict(entry.extra_metadata) if entry.extra_metadata else {}
        metadata["pinned"] = data.get("is_pinned", True)
        entry.extra_metadata = metadata
        session.add(entry)
        session.commit()
    return {"status": "SUCCESS"}

@router.patch("/memory/{entry_id}/tags", dependencies=[Depends(verify_authenticated)])
async def tag_memory(entry_id: str, request: Request, data: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    from sqlmodel import Session
    from ..models import HLSMEpisodicEntry
    from ..database import engine
    
    with Session(engine) as session:
        entry = session.get(HLSMEpisodicEntry, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        metadata = dict(entry.extra_metadata) if entry.extra_metadata else {}
        metadata["tags"] = data.get("tags", [])
        entry.extra_metadata = metadata
        session.add(entry)
        session.commit()
    return {"status": "SUCCESS"}

@router.post("/memory/{entry_id}/promote", dependencies=[Depends(verify_authenticated)])
async def promote_memory(entry_id: str, request: Request, data: Optional[Dict[str, Any]] = None, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.hlsm_manager:
        raise HTTPException(status_code=503, detail="H-LSM manager not ready")
    
    from sqlmodel import Session
    from ..models import HLSMEpisodicEntry
    from ..database import engine
    
    data = data or {}
    target_tier = data.get("targetTier")
    
    with Session(engine) as session:
        base_uuid = entry_id
        if base_uuid.startswith("l2_") or base_uuid.startswith("l3_"):
            base_uuid = base_uuid[3:]
            
        entry = session.get(HLSMEpisodicEntry, base_uuid)
        if not entry:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        if target_tier == 3 or (entry.promoted_to_l2 and not getattr(entry, "promoted_to_l3", False)):
            try:
                await services.hlsm_manager.l3_store(entry)
                entry.promoted_to_l3 = True
                session.add(entry)
                session.commit()
            except Exception as e:
                logger.error(f"Promotion failed: {e}")
                raise HTTPException(status_code=500, detail="Promotion to L3 failed")
        elif not entry.promoted_to_l2:
            try:
                await services.hlsm_manager.l2_store(entry)
                entry.promoted_to_l2 = True
                session.add(entry)
                session.commit()
            except Exception as e:
                logger.error(f"Promotion failed: {e}")
                raise HTTPException(status_code=500, detail="Promotion to L2 failed")
                
    return {"status": "SUCCESS"}

@router.post("/memory/{entry_id}/demote", dependencies=[Depends(verify_authenticated)])
async def demote_memory(entry_id: str, request: Request, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.hlsm_manager:
        raise HTTPException(status_code=503, detail="H-LSM manager not ready")
    
    from sqlmodel import Session
    from ..models import HLSMEpisodicEntry
    from ..database import engine
    
    with Session(engine) as session:
        base_uuid = entry_id
        if base_uuid.startswith("l3_") or base_uuid.startswith("l2_"):
            base_uuid = base_uuid[3:]
            
        entry = session.get(HLSMEpisodicEntry, base_uuid)
        if not entry:
            raise HTTPException(status_code=404, detail="Memory not found")
            
        if getattr(entry, "promoted_to_l3", False):
            await services.hlsm_manager.l3_delete(f"l3_{base_uuid}")
            entry.promoted_to_l3 = False
        elif entry.promoted_to_l2:
            await services.hlsm_manager.l2_delete(f"l2_{base_uuid}")
            entry.promoted_to_l2 = False
        
        session.add(entry)
        session.commit()
    return {"status": "SUCCESS"}
