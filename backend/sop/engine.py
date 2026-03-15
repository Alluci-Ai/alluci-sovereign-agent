
import logging
from ..logging_config import get_logger
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlmodel import Session, select
from ..database import engine as db_engine
from ..models import SOPRecord

logger = get_logger("SOPEngine")

class SOPEngine:
    """
    Sovereign SOP (Standard Operating Procedure) Engine.
    Executes predefined sequences with database persistence and auditing.
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
        Each step is audited via the Run system.
        """
        sop = self.get_sop(sop_id)
        if not sop:
            raise ValueError(f"SOP {sop_id} not found.")

        from ..services import orchestrator
        if not orchestrator:
            raise RuntimeError("Orchestrator not initialized.")

        steps = sop.steps.get("steps", [])
        logger.info(f"🚀 [SOP_EXEC]: Starting sequence '{sop.name}' ({len(steps)} steps)")
        
        # 1. Create a Master Run for this SOP execution
        run_id = orchestrator._create_run_record(
            objective=f"SOP EXECUTION: {sop.name}",
            autonomy="autonomous"
        )
        
        results = []
        try:
            for i, step in enumerate(steps):
                action = step.get("action")
                description = step.get("description", f"Step {i+1}")
                
                logger.info(f"📍 [SOP_STEP]: {description} (Action: {action})")
                
                # Update Run Feedback with current step
                orchestrator._update_run_status(
                    run_id, 
                    "active", 
                    feedback=f"Executing Step {i+1}/{len(steps)}: {description}"
                )

                # Construct the objective for the orchestrator
                objective = f"SOP '{sop.name}' - Step {i+1}: {description}. Action: {action}"
                if context_overrides:
                    objective += f" | Context: {context_overrides}"

                # Execute via orchestrator
                res = await orchestrator.execute_objective(objective, autonomy="autonomous")
                
                step_result = {
                    "step": i+1, 
                    "description": description,
                    "status": res.get("status"), 
                    "result": res.get("result", res.get("reason", "No details"))
                }
                results.append(step_result)
                
                if res.get("status") != "success":
                    logger.error(f"❌ [SOP_FAILURE]: Step {i+1} failed. Sequence aborted.")
                    orchestrator._update_run_status(
                        run_id, 
                        "failed", 
                        feedback=f"Aborted at step {i+1}: {res.get('reason', 'Step failed')}"
                    )
                    return {"status": "failed", "step": i+1, "history": results, "run_id": run_id}

            logger.info(f"✅ [SOP_COMPLETE]: Successfully finished '{sop.name}'")
            orchestrator._update_run_status(
                run_id, 
                "completed", 
                feedback=f"SOP '{sop.name}' completed successfully."
            )
            return {"status": "success", "history": results, "run_id": run_id}

        except Exception as e:
            logger.error(f"🔥 [SOP_CRASH]: {e}")
            orchestrator._update_run_status(
                run_id, 
                "failed", 
                feedback=f"System error during SOP execution: {str(e)}"
            )
            raise

# Global Singleton
sop_engine = SOPEngine()
