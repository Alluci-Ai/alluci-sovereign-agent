import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..security.resolution import resolution_manager
from ..security.network_policy import EgressFilterTransport
from ..security.circuit_breaker import circuit_breaker
from ..logging_config import get_logger

logger = get_logger("SecurityRouter")

router = APIRouter(prefix="/security", tags=["Security Resolution"])

class SecurityResolutionRequest(BaseModel):
    task_id: str
    resolution_type: str # ALLOW_DOMAIN_SESSION, ALLOW_DOMAIN_PERMANENT, IGNORE_BUDGET, CANCEL_TASK
    metadata: Optional[Dict[str, Any]] = None

@router.post("/resolve")
async def resolve_security_block(req: SecurityResolutionRequest):
    """
    Called by the frontend Interactive Security Modal to resolve a blocked task.
    """
    logger.info(f"Received security resolution: {req.resolution_type} for task {req.task_id}")
    
    if req.resolution_type == "CANCEL_TASK":
        success = resolution_manager.provide_resolution(req.task_id, "CANCEL_TASK")
        if not success:
            raise HTTPException(status_code=404, detail="Task ID not found in pending resolutions.")
        return {"status": "success", "action": "task_cancelled"}

    if req.resolution_type in ["ALLOW_DOMAIN_SESSION", "ALLOW_DOMAIN_PERMANENT"]:
        domain = req.metadata.get("domain") if req.metadata else None
        if not domain:
            raise HTTPException(status_code=400, detail="Domain must be provided in metadata.")
            
        # Add to memory
        EgressFilterTransport.TRUSTED_DOMAINS.add(domain)
        
        if req.resolution_type == "ALLOW_DOMAIN_PERMANENT":
            # Write to persistent config
            config_path = os.path.expanduser("~/.polytope/trusted_domains.json")
            try:
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                domains = list(EgressFilterTransport.TRUSTED_DOMAINS)
                with open(config_path, "w") as f:
                    json.dump(domains, f)
            except Exception as e:
                logger.error(f"Failed to save trusted domains to disk: {e}")
                
        resolution_manager.provide_resolution(req.task_id, req.resolution_type)
        return {"status": "success", "action": "domain_allowed"}
        
    if req.resolution_type == "IGNORE_BUDGET":
        # Temporarily increase limits
        budget_type = req.metadata.get("budget_type") if req.metadata else None
        amount = req.metadata.get("amount", 0.0) if req.metadata else 0.0
        
        if budget_type == "VERUS":
            circuit_breaker.MAX_VERUS_SPEND_PER_DAY += (amount + 10.0) # buffer
        elif budget_type == "LLM":
            circuit_breaker.MAX_LLM_API_COST_PER_DAY += (amount + 5.0)
            
        resolution_manager.provide_resolution(req.task_id, req.resolution_type)
        return {"status": "success", "action": "budget_increased"}
        
    raise HTTPException(status_code=400, detail=f"Unknown resolution_type: {req.resolution_type}")
