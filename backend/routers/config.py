# backend/routers/config.py
from ..logging_config import get_logger
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from fastapi_csrf_protect import CsrfProtect
from ..security.auth import verify_authenticated
from .. import services

logger = get_logger("ConfigRouter")
router = APIRouter(tags=["System Configuration"])


@router.get("/config", dependencies=[Depends(verify_authenticated)])
async def get_config():
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.read_config()


@router.put("/config", dependencies=[Depends(verify_authenticated)])
async def update_config(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    config: Dict[str, Any] = Body(...),
):
    await csrf_protect.validate_csrf(request)
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.update_config(config)


@router.get("/config/schema", dependencies=[Depends(verify_authenticated)])
async def get_config_schema():
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.get_schema()
