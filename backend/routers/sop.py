
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from ..security.auth import verify_authenticated
from ..models import SOPRecord
from fastapi_csrf_protect import CsrfProtect
from .. import services

router = APIRouter(prefix="/sops", tags=["SOP Engine"])

@router.get("/", response_model=List[SOPRecord], dependencies=[Depends(verify_authenticated)])
async def list_sops():
    """List all active Standard Operating Procedures."""
    if not services.sop_engine:
        raise HTTPException(status_code=503, detail="SOP engine not ready")
    return services.sop_engine.list_sops()

@router.post("/", dependencies=[Depends(verify_authenticated)])
async def register_sop(
    request: Request,
    name: str = Body(...), 
    description: str = Body(...), 
    steps: List[Dict[str, Any]] = Body(...),
    csrf_protect: CsrfProtect = Depends(),
):
    await csrf_protect.validate_csrf(request)
    """Register a new SOP sequence."""
    if not services.sop_engine:
        raise HTTPException(status_code=503, detail="SOP engine not ready")
    sop_id = await services.sop_engine.register_sop(name, description, steps)
    return {"id": sop_id, "status": "REGISTERED"}

@router.get("/{sop_id}", response_model=SOPRecord, dependencies=[Depends(verify_authenticated)])
async def get_sop(sop_id: int):
    """Get details of a specific SOP."""
    if not services.sop_engine:
        raise HTTPException(status_code=503, detail="SOP engine not ready")
    sop = services.sop_engine.get_sop(sop_id)
    if not sop:
        raise HTTPException(status_code=404, detail="SOP not found")
    return sop

@router.post("/{sop_id}/execute", dependencies=[Depends(verify_authenticated)])
async def execute_sop(request: Request, sop_id: int, context_overrides: Optional[Dict[str, Any]] = Body(None), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    """Trigger the execution of an SOP."""
    if not services.sop_engine:
        raise HTTPException(status_code=503, detail="SOP engine not ready")
    try:
        result = await services.sop_engine.execute_sop(sop_id, context_overrides=context_overrides)  # type: ignore
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SOP execution failed: {str(e)}")
