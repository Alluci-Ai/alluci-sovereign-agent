# backend/security/policyEngine.py
import logging
from enum import Enum
from pydantic import BaseModel

logger = logging.getLogger("PolicyEngine")

class AutonomyLevel(str, Enum):
    RESTRICTED = "RESTRICTED"
    SEMI_AUTONOMOUS = "SEMI_AUTONOMOUS"
    SOVEREIGN = "SOVEREIGN"

class AceStateVector(BaseModel):
    physical_energy: float = 0.5  # 0.0 - 1.0
    cognitive_load: float = 0.5   # 0.0 - 1.0

class ExecutionManifest(BaseModel):
    autonomy_level: AutonomyLevel = AutonomyLevel.RESTRICTED
    objective_id: str
    model_version: str
    planner_version: str

class AutonomyPolicyEngine:
    """
    [ AUTONOMY_POLICY_ENGINE ]
    Decides whether an action is permitted based on:
    1. The declared AutonomyLevel in the manifest.
    2. The Risk Score calculated by the Critic.
    3. The current biological/affective state of the user (ACE).
    """
    
    def evaluate(
        self,
        manifest: ExecutionManifest,
        risk_score: float, # 0.0 - 100.0
        ace_state: AceStateVector
    ) -> bool:
        logger.info(f"DEBUG POLICY: manifest={type(manifest)}, ace={type(ace_state)}")
        if not hasattr(manifest, "autonomy_level"):
             logger.error(f"DEBUG POLICY: manifest missing autonomy_level! {manifest}")
             return False
        if not hasattr(ace_state, "physical_energy"):
             logger.error(f"DEBUG POLICY: ace_state missing physical_energy! {ace_state}")
             return False
        if manifest.autonomy_level == AutonomyLevel.RESTRICTED:
            # Restricted execution is extremely conservative.
            if risk_score > 10:
                logger.warning(f"[ POLICY ]: REJECTED. RESTRICTED mode limit (10) exceeded by risk {risk_score}.")
                return False

        # 2. ACE Signal Modulation
        # If the user has low physical energy, the system becomes more conservative (lower threshold).
        # If the user has high cognitive load, the system becomes more conservative to avoid overwhelming them.
        
        energy_modulator = max(0.2, ace_state.physical_energy) # Floor at 0.2
        load_modulator = max(0.2, 1.0 - ace_state.cognitive_load) # Invert load
        
        # Determine Base Threshold
        base_threshold = 10.0
        if manifest.autonomy_level == AutonomyLevel.SEMI_AUTONOMOUS:
            base_threshold = 50.0
        elif manifest.autonomy_level == AutonomyLevel.SOVEREIGN:
            base_threshold = 90.0

        # Calculate Dynamic Threshold
        # dynamic = base * energy * (1 - load)
        dynamic_threshold = base_threshold * energy_modulator * load_modulator

        if risk_score > dynamic_threshold:
            logger.warning(
                f"[ POLICY ]: REJECTED. Risk {risk_score} exceeds dynamic threshold {dynamic_threshold:.2f}. "
                f"Details: Base={base_threshold}, Energy={energy_modulator:.2f}, LoadInv={load_modulator:.2f}"
            )
            return False

        logger.info(f"[ POLICY ]: APPROVED. Risk {risk_score} within threshold {dynamic_threshold:.2f}.")
        return True
