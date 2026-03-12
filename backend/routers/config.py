
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body
from ..security.auth import verify_authenticated
from .. import services

logger = logging.getLogger("ConfigRouter")

router = APIRouter(tags=["System Configuration"])

@router.get("/api/config", dependencies=[Depends(verify_authenticated)])
async def get_config():
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.read_config()

@router.put("/api/config", dependencies=[Depends(verify_authenticated)])
async def update_config(config: Dict[str, Any] = Body(...)):
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.update_config(config)

@router.get("/api/config/schema", dependencies=[Depends(verify_authenticated)])
async def get_config_schema():
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.get_schema()
