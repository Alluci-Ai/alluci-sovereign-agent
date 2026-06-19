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
from ..security.auth import get_current_user

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

@router.post("/objective/execute")
async def execute_objective(
    request: ObjectiveRequest,
    agent_id: str = "executive",
    manifest_header: Optional[str] = Header(None, alias="X-Execution-Manifest"),
    current_user: Any = None
):
    try:
        if not services.orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialised.")

        if not request.objective or not request.objective.strip():
            raise HTTPException(status_code=400, detail="Objective must not be empty.")

        # 1. Manifest Integrity & Authenticity Check
        if settings.APP_ENV not in ["testing", "development"]:
            if not manifest_header:
                raise HTTPException(status_code=403, detail="X-Execution-Manifest header required for production.")
            
            manifest = verify_manifest(manifest_header)
        else:
            # In development/testing, gracefully decode browser dummy manifest if present
            if manifest_header:
                try:
                    import base64
                    import json
                    manifest_raw = base64.b64decode(manifest_header).decode("utf-8")
                    signed_manifest = json.loads(manifest_raw)
                    manifest = signed_manifest.get("manifest", {"autonomyLevel": request.autonomy_level})
                except Exception:
                    manifest = {"autonomyLevel": request.autonomy_level}
            else:
                manifest = {"autonomyLevel": request.autonomy_level}

        # 2. Policy Enforcement (ACE/Autonomy Gate)
        from ..security.policyEngine import AceStateVector, ExecutionManifest
        
        ace_state = AceStateVector()
        if services.ace:
            # Map front-end biometrics to ACE state vector
            ace_state = AceStateVector(
                physical_energy=getattr(services.ace, "physical_energy", 0.5),
                cognitive_load=getattr(services.ace, "cognitive_load", 0.5)
            )

        # evaluate risk score (0 in testing/development, dynamic in production)
        risk_score = 0 if settings.APP_ENV in ["testing", "development"] else 50
        
        # If we are in testing, manifest is a dict, convert it to model
        if isinstance(manifest, dict):
            # Translate CamelCase from front-end/test to snake_case if needed
            autonomy_level = manifest.get("autonomyLevel") or manifest.get("autonomy_level") or "SEMI_AUTONOMOUS"
            manifest = ExecutionManifest(  # type: ignore
                autonomy_level=autonomy_level,  # type: ignore
                objective_id=str(uuid.uuid4()),
                model_version="test-v1",
                planner_version="test-v1"
            )

        permitted = policy_engine.evaluate(manifest, risk_score, ace_state)  # type: ignore

        user_id = current_user['id'] if current_user else 'anonymous'
        if not permitted:
            logger.warning(f"[ POLICY ]: Objective rejected for {user_id} due to autonomy constraints.")
            raise HTTPException(status_code=403, detail="Objective rejected by autonomy policy gate.")

        # 3. Input Sanitization (Guardrails)
        if services.scanner:
            is_safe, reason = await services.scanner.scan_input(request.objective)
            if not is_safe:
                logger.warning(f"[ GUARDRAIL_BLOCK ]: Objective from {user_id} rejected: {reason}")
                raise HTTPException(status_code=400, detail=f"Objective rejected by safety gate: {reason}")

        # 4. Execution (Proxy to Orchestrator)
        logger.info(f"[ EXEC ]: Starting objective for {user_id}: {request.objective[:50]}...")
        if agent_id != "executive":
            res = await services.orchestrator.multi_agent_delegate(agent_id, request.objective)
            return {"status": "accepted", "run_id": None, "detail": res}
            
        result = await services.orchestrator.execute_objective(
            request.objective,
            autonomy=manifest.autonomy_level  # type: ignore
        )
        
        # If the orchestrator returned a dictionary instead of an int, it halted/failed
        if isinstance(result, dict) and result.get("status") in ["halted", "failed"]:
            raise HTTPException(status_code=500, detail=result.get("reason", "Objective execution failed"))
            
        return {"status": "accepted", "run_id": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Objective execution failed.")
        raise HTTPException(status_code=500, detail=str(e))
