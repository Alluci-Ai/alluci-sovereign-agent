import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from ..security.resolution import resolution_manager
from ..security.network_policy import EgressFilterTransport
from ..security.circuit_breaker import circuit_breaker
from ..security.calibration import CalibrationManager
from ..logging_config import get_logger

logger = get_logger("SecurityRouter")

router = APIRouter(prefix="/security", tags=["Security Resolution"])

class SecurityResolutionRequest(BaseModel):
    task_id: str
    resolution_type: str # ALLOW_DOMAIN_SESSION, ALLOW_DOMAIN_PERMANENT, IGNORE_BUDGET, CANCEL_TASK, OVERRIDE_TEARING
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

    if req.resolution_type == "OVERRIDE_TEARING":
        cm = CalibrationManager()
        
        topology_shift = float(req.metadata.get("topology_shift", 0.0)) if req.metadata else 0.0
        origin = req.metadata.get("origin", "local") if req.metadata else "local"
        is_tool = bool(req.metadata.get("is_tool", False)) if req.metadata else False
        
        # Log the approved trajectory divided by 10 (as handled inside DPK internally if valid)
        cm.log_approved_trajectory(topology_shift / 10.0, origin=origin, is_tool=is_tool)
        
        resolution_manager.provide_resolution(req.task_id, "OVERRIDE_TEARING")
        return {"status": "success", "action": "tearing_overridden"}

    if req.resolution_type in ["APPROVE_MEMORY_PURGE", "APPROVE_ACTION"]:
        import uuid
        from .. import services
        meta = req.metadata or {}
        pattern = str(meta.get("pattern") or meta.get("target") or "").strip()
        
        counts = {"deleted_l0": 0, "deleted_l1": 0, "deleted_l2": 0, "deleted_l3": 0, "total_deleted": 0}
        mgr = services.hlsm_manager or services.memory
        if pattern and mgr:
            try:
                counts = await mgr.delete_by_pattern(pattern)
            except Exception as e:
                logger.error(f"[SecurityRouter] Memory purge execution error: {e}")
        else:
            logger.warning(f"[SecurityRouter] Memory purge approval pattern empty or manager unavailable (pattern='{pattern}')")
        
        total = counts.get("total_deleted", 0)
        card_msg = (
            f"✅ **H-LSM Memory Purge Approved & Executed**\n\n"
            f"Successfully scanned all topological memory layers and permanently deleted **{total} matching memory entries** for `{pattern}`.\n\n"
            f"- **L0 Working Memory:** {counts.get('deleted_l0', 0)} entries purged\n"
            f"- **L1 Episodic Memory:** {counts.get('deleted_l1', 0)} entries purged\n"
            f"- **L2 Semantic Memory:** {counts.get('deleted_l2', 0)} entries purged\n"
            f"- **L3 Knowledge Graph:** {counts.get('deleted_l3', 0)} entries purged"
        )
        
        if services.orchestrator and hasattr(services.orchestrator, "ws_gateway") and services.orchestrator.ws_gateway:
            await services.orchestrator.ws_gateway.broadcast_event('chat.message.received', {
                "type": "chat.message.received",
                "id": f"msg_purge_{uuid.uuid4().hex[:8]}",
                "content": card_msg,
                "sender": "system"
            })
            await services.orchestrator.ws_gateway.broadcast_event('memory.deleted', {
                "type": "memory.deleted",
                "pattern": pattern,
                "total_deleted": total
            })
            
        resolution_manager.provide_resolution(req.task_id, req.resolution_type)
        return {"status": "success", "action": "memory_purge_executed", "total_deleted": total}
        
    raise HTTPException(status_code=400, detail=f"Unknown resolution_type: {req.resolution_type}")
