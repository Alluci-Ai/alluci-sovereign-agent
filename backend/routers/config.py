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
    return services.config_editor.get_config()  # type: ignore


@router.put("/config", dependencies=[Depends(verify_authenticated)])
async def update_config(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    config: Dict[str, Any] = Body(...),
):
    await csrf_protect.validate_csrf(request)
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.update_config(config)  # type: ignore


@router.get("/config/schema", dependencies=[Depends(verify_authenticated)])
async def get_config_schema():
    if not services.config_editor:
        raise HTTPException(status_code=503, detail="Config editor not ready")
    return services.config_editor.get_schema()


@router.get("/config/dreaming/status", dependencies=[Depends(verify_authenticated)])
async def get_dreaming_status():
    from ..cron_engine import get_host_local_timezone_info
    tz_info = get_host_local_timezone_info()
    settings = getattr(services, "settings", None)
    cron_eng = getattr(services, "cron_engine", None)
    
    return {
        "enabled": getattr(settings, "DREAMING_CYCLE_ENABLED", True),
        "schedule_time": getattr(settings, "DREAMING_CYCLE_TIME", "02:00"),
        "timezone": getattr(settings, "DREAMING_CYCLE_TIMEZONE", "LOCAL"),
        "max_duration_minutes": getattr(settings, "DREAMING_CYCLE_MAX_DURATION_MINUTES", 45),
        "yield_on_user_activity": getattr(settings, "DREAMING_CYCLE_YIELD_ON_USER_ACTIVITY", True),
        "detected_host_timezone": tz_info,
        "is_active": getattr(cron_eng, "is_dreaming_active", False) if cron_eng else False
    }


@router.post("/config/dreaming/trigger", dependencies=[Depends(verify_authenticated)])
async def trigger_manual_dreaming(
    request: Request,
    csrf_protect: CsrfProtect = Depends()
):
    await csrf_protect.validate_csrf(request)
    cron_eng = getattr(services, "cron_engine", None)
    if not cron_eng:
        raise HTTPException(status_code=503, detail="Cron engine not initialized")
    res = await cron_eng.trigger_manual_dreaming_cycle()
    return res

