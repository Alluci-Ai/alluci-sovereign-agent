
from ..logging_config import get_logger
from typing import Dict, Any
from ..security.auth import verify_authenticated
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from .. import services
from ..security.rate_limit import RateLimiter
try:
    try:
        from fastapi_csrf_protect import CsrfProtect
    except ImportError:
        class CsrfProtect:
            async def validate_csrf(self, request):
                return None
except ImportError:
    class CsrfProtect:
        async def validate_csrf(self, request):
            return None

logger = get_logger("WalletRouter")

router = APIRouter(tags=["Wallet & DeFi"])

@router.get("/wallet/status", dependencies=[Depends(verify_authenticated)])
async def get_wallet_status():
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter:
        raise HTTPException(status_code=503, detail="Wallet adapter not loaded")
    return await adapter.get_status()

@router.get("/wallet/balance", dependencies=[Depends(verify_authenticated)])
async def get_wallet_balance():
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: return {"balance": 0, "currency": "VRSC"}
    return await adapter.get_balance()

@router.post("/wallet/send", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=10, minutes=1))])
async def wallet_send(request: Request, data: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: raise HTTPException(503, "Wallet adapter not loaded")
    return await adapter.send_funds(data)

@router.get("/wallet/mining", dependencies=[Depends(verify_authenticated)])
async def get_mining_status():
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: return {"status": "offline"}
    return await adapter.get_mining_status()

@router.get("/wallet/node/status", dependencies=[Depends(verify_authenticated)])
async def get_node_status():
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: raise HTTPException(503, "Wallet adapter not loaded")
    return await adapter.get_node_status()

@router.post("/wallet/node/action", dependencies=[Depends(verify_authenticated)])
async def wallet_node_action(request: Request, data: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: raise HTTPException(503, "Wallet adapter not loaded")
    action = data.get("action")
    return await adapter.execute_node_action(action)
