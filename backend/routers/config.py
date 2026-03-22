
import logging
from ..logging_config import get_logger
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body
from ..security.auth import verify_authenticated
from .. import services

from fastapi_csrf_protect import CsrfProtect

logger = get_logger("ConfigRouter")

router = APIRouter(tags=["System Configuration"])

@router.get("/config", dependencies=[Depends(verify_authenticated)])
async def get_config():
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.read_config()

@router.put("/config", dependencies=[Depends(verify_authenticated), Depends(CsrfProtect().validate_csrf)])
async def update_config(config: Dict[str, Any] = Body(...)):
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.update_config(config)

@router.get("/config/schema", dependencies=[Depends(verify_authenticated)])
async def get_config_schema():
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.get_schema()
