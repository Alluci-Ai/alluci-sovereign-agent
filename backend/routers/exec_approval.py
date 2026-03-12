
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from ..security.auth import verify_authenticated
from .. import services

logger = logging.getLogger("ExecApprovalRouter")

router = APIRouter(tags=["Execution Approval"])

@router.get("/api/exec/pending", dependencies=[Depends(verify_authenticated)])
async def get_pending_approvals():
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.get_pending()

@router.post("/api/exec/approve/{request_id}", dependencies=[Depends(verify_authenticated)])
async def approve_request(request_id: str):
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.approve(request_id)

@router.post("/api/exec/deny/{request_id}", dependencies=[Depends(verify_authenticated)])
async def deny_request(request_id: str):
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.deny(request_id)

@router.get("/api/exec/policies", dependencies=[Depends(verify_authenticated)])
async def list_policies():
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.list_policies()

@router.post("/api/exec/policies", dependencies=[Depends(verify_authenticated)])
async def add_policy(policy: Dict[str, Any] = Body(...)):
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.add_policy(policy)

@router.delete("/api/exec/policies/{policy_id}", dependencies=[Depends(verify_authenticated)])
async def delete_policy(policy_id: int):
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.delete_policy(policy_id)
