
import logging
from ..logging_config import get_logger
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, Body
from, Request
..security.auth import verify_authenticated
from fastapi_csrf_protect import CsrfProtect
from .. import services

logger = get_logger("ExecApprovalRouter")

router = APIRouter(tags=["Execution Approval"])

@router.get("/exec/pending", dependencies=[Depends(verify_authenticated)])
async def get_pending_approvals():
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.get_pending()

@router.post("/exec/approve/{request_id}", dependencies=[Depends(verify_authenticated)])
async def approve_request(request_id: str):
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.approve(request_id)

@router.post("/exec/deny/{request_id}", dependencies=[Depends(verify_authenticated)])
async def deny_request(request_id: str):
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.deny(request_id)

@router.get("/exec/policies", dependencies=[Depends(verify_authenticated)])
async def list_policies():
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.list_policies()

@router.post("/exec/policies", dependencies=[Depends(verify_authenticated)])
async def add_policy(policy: Dict[str, Any] = Body(...)):
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.add_policy(policy)

@router.delete("/exec/policies/{policy_id}", dependencies=[Depends(verify_authenticated)])
async def delete_policy(policy_id: int):
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.delete_policy(policy_id)
