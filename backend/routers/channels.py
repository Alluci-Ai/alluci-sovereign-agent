
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from ..security.auth import verify_authenticated
from .. import services

logger = logging.getLogger("ChannelsRouter")

router = APIRouter(tags=["Bridge Channels"])

@router.get("/api/channels", dependencies=[Depends(verify_authenticated)])
async def list_channels():
    # Summarize all available communication manifolds
    return [
        {"id": cid, "status": getattr(adapter, "status", "idle"), "type": getattr(adapter, "channel_type", "unknown")}
        for cid, adapter in services.channel_registry.items()
    ]

@router.get("/api/channels/{channel_id}/config", dependencies=[Depends(verify_authenticated)])
async def get_channel_config(channel_id: str):
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    return getattr(adapter, "config", {})

@router.put("/api/channels/{channel_id}/config", dependencies=[Depends(verify_authenticated)])
async def update_channel_config(channel_id: str, config: Dict[str, Any] = Body(...)):
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    if hasattr(adapter, "update_config"):
        return await adapter.update_config(config)
    raise HTTPException(status_code=501, detail="Config update not supported for this channel")

@router.post("/api/channels/{channel_id}/connect", dependencies=[Depends(verify_authenticated)])
async def connect_channel(channel_id: str):
    adapter = services.channel_registry.get(channel_id)
    if not adapter:
        raise HTTPException(status_code=404, detail="Channel not found")
    if hasattr(adapter, "connect"):
        return await adapter.connect()
    raise HTTPException(status_code=501, detail="Direct connect not supported")

# --- Specialized Channel Routes ---

@router.get("/api/channels/iwatch/status", dependencies=[Depends(verify_authenticated)])
async def iwatch_status():
    adapter = services.channel_registry.get("iwatch")
    if not adapter:
        return {"status": "unloaded"}
    return {"status": "connected" if getattr(adapter, "is_connected", False) else "paired"}

@router.post("/api/channels/iwatch/pair")
async def iwatch_pair():
    """Step 1: Generate TOTP secret for pairing."""
    adapter = services.channel_registry.get("iwatch")
    if not adapter: raise HTTPException(404, "Adapter not found")
    import pyotp
    secret = pyotp.random_base32()
    adapter.pending_totp_secret = secret
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name="Sovereign Agent", issuer_name="Alluci")
    return {"status": "SUCCESS", "secret": secret, "provisioning_uri": uri}

@router.post("/api/channels/iwatch/pair/verify")
async def iwatch_pair_verify(data: Dict[str, str] = Body(...)):
    """Step 2: Verify TOTP code."""
    code = data.get("code")
    if not code: raise HTTPException(400, "Missing 'code' parameter")
    adapter = services.channel_registry.get("iwatch")
    if not adapter: raise HTTPException(404, "Adapter not found")
    
    result = await adapter.submit_pairing_code(code)
    if result.get("paired"):
        credentials = result.get("credentials", {})
        if services.vault:
            from ..security.utils import log_system_event
            await services.vault.store_secret("channel_iwatch", credentials)
            await log_system_event("DEVICE_PAIR", "Apple Watch successfully paired.", "SUCCESS")
        return {"status": "SUCCESS", "message": "Apple Watch Paired."}
    raise HTTPException(status_code=401, detail=result.get("error", "Pairing failed"))

@router.get("/api/channels/wechat/qr-init")
async def wechat_qr_init():
    adapter = services.channel_registry.get("wechat")
    if hasattr(adapter, "init_qr"):
        return await adapter.init_qr()
    raise HTTPException(status_code=501, detail="WeChat QR flow not implemented")

@router.post("/api/channels/webchat/session/{id}/capture")
async def webchat_session_capture(id: str, data: Dict[str, Any] = Body(...)):
    adapter = services.channel_registry.get("webchat")
    if hasattr(adapter, "capture_session"):
        return await adapter.capture_session(id, data)
    raise HTTPException(status_code=501, detail="WebChat capture not implemented")

@router.post("/api/channels/icloud/2fa")
async def icloud_2fa(data: Dict[str, str] = Body(...)):
    adapter = services.channel_registry.get("icloud")
    if hasattr(adapter, "submit_2fa"):
        return await adapter.submit_2fa(data.get("code"))
    raise HTTPException(status_code=501, detail="iCloud 2FA not implemented")
