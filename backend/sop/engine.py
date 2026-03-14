
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlmodel import Session, select
from ..database import engine as db_engine
from ..models import SOPRecord

logger = logging.getLogger("SOPEngine")

class SOPEngine:
    """
    Sovereign SOP (Standard Operating Procedure) Engine.
    Executes predefined sequences with database persistence.
    """
    def __init__(self, engine=None):
        self.engine = engine or db_engine

    async def register_sop(self, name: str, description: str, steps: List[Dict[str, Any]]) -> int:
        with Session(self.engine) as session:
            sop = SOPRecord(
                name=name,
                description=description,
                steps={"steps": steps}
            )
            session.add(sop)
            session.commit()
            session.refresh(sop)
            return sop.id

    def get_sop(self, sop_id: int) -> Optional[SOPRecord]:
        with Session(self.engine) as session:
            return session.get(SOPRecord, sop_id)

    def list_sops(self) -> List[SOPRecord]:
        with Session(self.engine) as session:
            stmt = select(SOPRecord).where(SOPRecord.is_active == True)
            return session.exec(stmt).all()

    async def execute_sop(self, sop_id: int, context_overrides: Dict[str, Any] = None):
        """
        Executes an SOP by iterating through its defined steps.
        Each step is dispatched to the ExecutiveOrchestrator.
        """
        sop = self.get_sop(sop_id)
        if not sop:
            raise ValueError(f"SOP {sop_id} not found.")

        from ..services import orchestrator
        if not orchestrator:
            raise RuntimeError("Orchestrator not initialized.")

        steps = sop.steps.get("steps", [])
        logger.info(f"🚀 [SOP_EXEC]: Starting sequence '{sop.name}' ({len(steps)} steps)")
        
        results = []
        for i, step in enumerate(steps):
            action = step.get("action")
            description = step.get("description", f"Step {i+1}")
            
            logger.info(f"📍 [SOP_STEP]: {description} (Action: {action})")
            
            # Construct the objective for the orchestrator
            objective = f"SOP Step: {description}. Action: {action}"
            if context_overrides:
                objective += f" | Context: {context_overrides}"

            # Execute via orchestrator
            res = await orchestrator.execute_objective(objective, autonomy="autonomous")
            results.append({"step": i+1, "status": res.get("status"), "result": res.get("result")})
            
            if res.get("status") == "failed":
                logger.error(f"❌ [SOP_FAILURE]: Step {i+1} failed. Habilitating emergency stop.")
                return {"status": "failed", "step": i+1, "history": results}

        logger.info(f"✅ [SOP_COMPLETE]: Successfully finished '{sop.name}'")
        return {"status": "success", "history": results}

# Global Singleton
sop_engine = SOPEngine()
