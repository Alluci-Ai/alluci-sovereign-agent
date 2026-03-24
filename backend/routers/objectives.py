# backend/routers/objectives.py — RE-APPLIED FIX

import base64
import json
import uuid
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from cryptography.hazmat.primitives.asymmetric import ed25519

from .. import services
from ..config import settings
from ..security.policyEngine import AutonomyPolicyEngine
from ..auth import get_current_user

router = APIRouter()
logger = logging.getLogger("ObjectiveManager")
policy_engine = AutonomyPolicyEngine()

class ObjectiveRequest(BaseModel):
    objective: str
    autonomy_level: str = "SEMI_AUTONOMOUS"

# ── Manifest Validation Helpers ───────────────────────────────────────────────

def _canonicalize(obj: Any) -> str:
    """Python mirror of ExecutionManifestFactory.canonicalize() in TypeScript."""
    if obj is None or not isinstance(obj, (dict, list)):
        return json.dumps(obj, separators=(',', ':'))
    if isinstance(obj, list):
        return f"[{','.join(_canonicalize(x) for x in obj)}]"
    sorted_keys = sorted(obj.keys())
    parts = [f'"{k}":{_canonicalize(obj[k])}' for k in sorted_keys]
    return "{" + ",".join(parts) + "}"

def verify_manifest(manifest_header: str) -> Dict[str, Any]:
    """Decodes and validates the Ed25519 signature of an execution manifest."""
    try:
        manifest_raw = base64.b64decode(manifest_header).decode("utf-8")
        signed_manifest = json.loads(manifest_raw)
        manifest = signed_manifest["manifest"]
        signature = bytes.fromhex(signed_manifest["signature"])
        root_pubkey = bytes.fromhex(manifest["rootPublicKey"])

        canonical_str = _canonicalize(manifest)
        verify_key = ed25519.Ed25519PublicKey.from_public_bytes(root_pubkey)
        verify_key.verify(signature, canonical_str.encode("utf-8"))
        
        return manifest
    except Exception as e:
        logger.error(f"[ SECURITY ]: Manifest verification failed: {e}")
        raise HTTPException(status_code=403, detail="Invalid Execution Manifest Signature.")

# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/execute")
async def execute_objective(
    request: ObjectiveRequest,
    manifest_header: Optional[str] = Header(None, alias="X-Execution-Manifest"),
    current_user: Any = Depends(get_current_user)
):
    """
    Executes a sovereign objective using the backend DAG planner.
    Enforces signed manifest validation and ACE-modulated policy.
    """
    if not services.orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialised.")

    # 1. Manifest Integrity & Authenticity Check
    if not manifest_header:
        raise HTTPException(status_code=403, detail="X-Execution-Manifest header required for production.")
    
    manifest = verify_manifest(manifest_header)

    # 2. Policy Enforcement (ACE/Autonomy Gate)
    ace_state = None
    if services.ace:
        # Map front-end biometrics to ACE state vector
        ace_state = {
            "physicalEnergy": getattr(services.ace, "physical_energy", 0.5),
            "emotionalValence": getattr(services.ace, "emotional_valence", 0.5),
            "cognitiveLoad": getattr(services.ace, "cognitive_load", 0.3)
        }

    # evaluate risk score (defaulting to 50 for legacy, should be dynamic)
    risk_score = 50 
    permitted = policy_engine.evaluate(manifest, risk_score, ace_state)

    if not permitted:
        logger.warning(f"[ POLICY ]: Objective rejected for {current_user.id} due to autonomy constraints.")
        raise HTTPException(status_code=403, detail="Objective rejected by autonomy policy gate.")

    # 3. Execution (Proxy to Orchestrator)
    try:
        logger.info(f"[ EXEC ]: Starting objective for {current_user.id}: {request.objective[:50]}...")
        run_id = await services.orchestrator.execute_objective(
            request.objective,
            autonomy_level=manifest["autonomyLevel"]
        )
        return {"status": "accepted", "run_id": run_id}
    except Exception as e:
        logger.exception("Objective execution failed.")
        raise HTTPException(status_code=500, detail=str(e))
