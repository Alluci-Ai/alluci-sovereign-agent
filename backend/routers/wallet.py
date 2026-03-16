
import logging
from ..logging_config import get_logger
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from ..security.auth import verify_authenticated
from .. import services
from fastapi_limiter.depends import RateLimiter

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
async def wallet_send(data: Dict[str, Any] = Body(...)):
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
async def wallet_node_action(data: Dict[str, Any] = Body(...)):
    adapter = services.channel_registry.get("verus_wallet")
    if not adapter: raise HTTPException(503, "Wallet adapter not loaded")
    action = data.get("action")
    return await adapter.execute_node_action(action)
