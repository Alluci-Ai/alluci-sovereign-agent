
from ..logging_config import get_logger
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body, Request
from ..security.auth import verify_authenticated
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
async def approve_request(request: Request, request_id: str, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.approve(request_id)

@router.post("/exec/deny/{request_id}", dependencies=[Depends(verify_authenticated)])
async def deny_request(request: Request, request_id: str, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.deny(request_id)

@router.get("/exec/policies", dependencies=[Depends(verify_authenticated)])
async def list_policies():
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.list_policies()

@router.post("/exec/policies", dependencies=[Depends(verify_authenticated)])
async def add_policy(request: Request, policy: Dict[str, Any] = Body(...), csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.add_policy(policy)

@router.delete("/exec/policies/{policy_id}", dependencies=[Depends(verify_authenticated)])
async def delete_policy(request: Request, policy_id: int, csrf_protect: CsrfProtect = Depends()):
    await csrf_protect.validate_csrf(request)
    if not services.exec_approval:
        raise HTTPException(status_code=503, detail="Approval system not ready")
    return await services.exec_approval.delete_policy(policy_id)
