
import logging
from ..logging_config import get_logger
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body, Request
from ..security.auth import verify_authenticated
from fastapi_csrf_protect import CsrfProtect
from .. import services

logger = get_logger("MemoryRouter")

router = APIRouter(tags=["Sovereign Memory"])

@router.get("/memory", dependencies=[Depends(verify_authenticated)])
async def list_memory(limit: int = 50, offset: int = 0):
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    return await services.memory.list_entries(limit=limit, offset=offset)

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
    return await services.memory.store(content=content, metadata=metadata)

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
