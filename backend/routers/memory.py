
import logging
from ..logging_config import get_logger
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from ..security.auth import verify_authenticated
from .. import services

logger = get_logger("MemoryRouter")

router = APIRouter(tags=["Sovereign Memory"])

@router.get("/api/memory", dependencies=[Depends(verify_authenticated)])
async def list_memory(limit: int = 50, offset: int = 0):
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    return await services.memory.list_entries(limit=limit, offset=offset)

@router.get("/api/memory/search", dependencies=[Depends(verify_authenticated)])
async def search_memory(q: str = Query(...), limit: int = 10):
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    return await services.memory.search(q, limit=limit)

@router.post("/api/memory/store", dependencies=[Depends(verify_authenticated)])
async def store_memory(data: Dict[str, Any] = Body(...)):
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    content = data.get("content")
    metadata = data.get("metadata", {})
    return await services.memory.store(content=content, metadata=metadata)

@router.get("/api/memory/stats", dependencies=[Depends(verify_authenticated)])
async def get_memory_stats():
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    return await services.memory.get_stats()

@router.delete("/api/memory/{entry_id}", dependencies=[Depends(verify_authenticated)])
async def delete_memory_entry(entry_id: str):
    if not services.memory:
        raise HTTPException(status_code=503, detail="Memory manager not ready")
    success = await services.memory.delete(entry_id)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {"status": "SUCCESS"}
