
import uuid
import traceback
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from sqlmodel import Session, select, desc
from ..config import settings
from ..database import engine as db_engine
from ..models import ObjectiveRequest, Run, TaskRecord as TaskRecordModel, TaskUpdate
from ..security.auth import verify_authenticated
from ..security.utils import sanitize_input
from .. import services
from fastapi_limiter.depends import RateLimiter

router = APIRouter(tags=["Objectives & Tasks"])

@router.post("/objective/execute", dependencies=[Depends(verify_authenticated), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))])
async def execute_objective(req: ObjectiveRequest):
    if not services.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not ready")
        
    try:
        # 1. Sanitize user-provided objective
        sanitized_objective = await sanitize_input(req.objective, scanner=services.scanner)
        
        # 2. Execute via orchestrator
        result = await services.orchestrator.execute_objective(sanitized_objective, req.autonomy_level, mode=req.mode)
        
        # 3. Scan Output (for PII/Secret leakage)
        vault_keys = await services.vault.retrieve_secret("alluci_api_keys") or {}
        active_secrets = []
        for cat, providers in vault_keys.items():
            if isinstance(providers, dict):
                for k, v in providers.items():
                    if v and isinstance(v, str) and len(v) > 8 and v != "MASK":
                        active_secrets.append(v)
        
        is_safe, error = await services.scanner.scan_output(str(result), active_secrets=active_secrets)
        if not is_safe:
            raise HTTPException(status_code=403, detail=error)
            
        return {"result": result}
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())
        raise HTTPException(
            status_code=500,
            detail=f"Objective execution failed. Error reference: {error_id}"
        )
