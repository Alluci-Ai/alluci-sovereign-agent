
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from ..security.auth import verify_authenticated
from .. import services
from fastapi_limiter.depends import RateLimiter

logger = logging.getLogger("WalletRouter")

router = APIRouter(tags=["Wallet & DeFi"])

@router.get("/api/wallet/status", dependencies=[Depends(verify_authenticated)])
async def get_wallet_status():
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter:
        raise HTTPException(status_code=503, detail="Wallet adapter not loaded")
    return await adapter.get_status()

@router.get("/api/wallet/balance", dependencies=[Depends(verify_authenticated)])
async def get_wallet_balance():
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: return {"balance": 0, "currency": "VRSC"}
    return await adapter.get_balance()

@router.post("/api/wallet/send", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=10, minutes=1))])
async def wallet_send(data: Dict[str, Any] = Body(...)):
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: raise HTTPException(503, "Wallet adapter not loaded")
    return await adapter.send_funds(data)

@router.get("/api/wallet/mining", dependencies=[Depends(verify_authenticated)])
async def get_mining_status():
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: return {"status": "offline"}
    return await adapter.get_mining_status()

@router.get("/api/wallet/node/status", dependencies=[Depends(verify_authenticated)])
async def get_node_status():
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: raise HTTPException(503, "Wallet adapter not loaded")
    return await adapter.get_node_status()

@router.post("/api/wallet/node/action", dependencies=[Depends(verify_authenticated)])
async def wallet_node_action(data: Dict[str, Any] = Body(...)):
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: raise HTTPException(503, "Wallet adapter not loaded")
    action = data.get("action")
    return await adapter.execute_node_action(action)
