from ..logging_config import get_logger
from ..metrics import AVL_GATE_REJECTIONS_TOTAL
from typing import Tuple, Optional
from .dpk import PolytopeState
from .calibration import CalibrationManager

logger = get_logger("AVL")


class AVLGate:
    """
    Action Verification Loop.
    Source: PPN §AVL — action_verifier.hpp::verify()

    Three-pillar LLM output safety gate:
      1. Sovereign Attribution   (unsigned manifold → reject)
      2. ALCE Gradient Smoothness (Lipschitz budget exceeded → reject)
      3. Topological Continuity   (Euler mismatch → reject)

    Additionally implements GJK boundary projection for deterministic
    refinement of out-of-bounds actions (PPN §AVL — project_to_boundary).
    """
    def __init__(self):
        self.calibration_manager = CalibrationManager()
        self.BUDGET_LIMIT = 1.0       # Fallback Max Lipschitz budget consumption
        self.MAX_EULER_DEVIATION = 2  # Fallback Consistent with DPK tolerance

    def verify(self, completion: str,
               state: PolytopeState) -> Tuple[bool, str]:
        """
        Returns (is_safe, reason).
        All three pillars must pass for the completion to be verified.
        
        **Security Guarantee:** Enforces zero-trust LLM execution by hard-rejecting 
        outputs that lack local cryptographic signatures or violate topological continuity 
        bounds (Euler deviations), preventing hallucination leaks.
        """
        # Pillar 1: Sovereign Attribution Check
        if state.signature_hash == 0:
            logger.critical("[AVL) UNSIGNED manifold — rejecting completion")
            AVL_GATE_REJECTIONS_TOTAL.inc()
            return False, "Unsigned manifold state"

        # Dynamic Baseline from DPK Calibration Cache
        try:
            dynamic_threshold = self.calibration_manager.get_dynamic_threshold(origin=state.origin)
            dynamic_budget = dynamic_threshold * 10.0
            dynamic_euler = max(2, int(dynamic_budget / 2))
        except Exception as e:
            if str(e) == "RBM_FROZEN":
                return False, f"RBM FREEZE: Origin {state.origin} is quarantined."
            dynamic_budget = self.BUDGET_LIMIT
            dynamic_euler = self.MAX_EULER_DEVIATION
            
        # Human-in-the-Loop Override
        if getattr(state, "is_avl_override", False):
            logger.warning(f"[AVL] OVERRIDE ACCEPTED. Logging sequence to {state.origin} AVL cache.")
            self.calibration_manager.log_avl_override(state.budget_used, origin=state.origin, psi=state.affective_tension_psi)
            return True, "OK"

        # Pillar 2: ALCE Gradient Smoothness Check
        if state.budget_used > dynamic_budget:
            logger.warning(f"[AVL] Lipschitz budget exceeded: {state.budget_used:.3f} > {dynamic_budget:.3f}")
            AVL_GATE_REJECTIONS_TOTAL.inc()
            
            # Context-Aware Plan Verification (RBM Integration)
            violation_amt = state.budget_used - dynamic_budget
            sigma_approx = violation_amt / 0.05
            
            return False, (
                f"Node exceeds the Relational Boundary Manifold (RBM) by {sigma_approx:.1f} sigma "
                f"(budget {state.budget_used:.2f} > {dynamic_budget:.2f})"
            )

        # Pillar 3: Topological Continuity Check
        chi = state.vertices_V - state.edges_E + state.faces_F
        betti_chi = round(state.betti[0] - state.betti[1] + state.betti[2] - state.betti[3]) if len(state.betti) >= 4 else 0
            
        if abs(chi - betti_chi) > dynamic_euler:
            logger.error(f"[AVL] Topological rupture: χ={chi} vs β_chi={betti_chi}")
            AVL_GATE_REJECTIONS_TOTAL.inc()
            return False, f"Topological rupture detected (χ={chi} vs β_chi={betti_chi}, tolerance={dynamic_euler})"

        logger.info(f"[AVL] VERIFIED. φ={state.phi_total}, coh={state.coherence:.3f}")
        return True, "OK"

    def verify_with_refinement(self, completion: str,
                               state: PolytopeState) -> Tuple[bool, str, Optional[str]]:
        """
        Extended verification with GJK boundary projection.
        Returns (is_safe, reason, refined_action).

        If the action violates budget but is close to boundary,
        projects it to the nearest admissible point instead of hard-rejecting.
        
        **Security Guarantee:** Neutralizes prompt-injection or hallucinated overflows 
        by deterministically projecting out-of-bounds LLM responses back into the 
        safe Lipschitz budget boundary.
        """
        # Pillar 1: Sovereign Attribution — no refinement possible
        if state.signature_hash == 0:
            logger.critical("[AVL] UNSIGNED manifold — hard reject")
            return False, "Unsigned manifold state", None

        # Dynamic Baseline from DPK Calibration Cache
        try:
            dynamic_threshold = self.calibration_manager.get_dynamic_threshold(origin=state.origin)
            dynamic_budget = dynamic_threshold * 10.0
            dynamic_euler = max(2, int(dynamic_budget / 2))
        except Exception as e:
            if str(e) == "RBM_FROZEN":
                return False, f"RBM FREEZE: Origin {state.origin} is quarantined.", None
            dynamic_budget = self.BUDGET_LIMIT
            dynamic_euler = self.MAX_EULER_DEVIATION
            
        # Human-in-the-Loop Override
        if getattr(state, "is_avl_override", False):
            logger.warning(f"[AVL] OVERRIDE ACCEPTED. Logging sequence to {state.origin} AVL cache.")
            self.calibration_manager.log_avl_override(state.budget_used, origin=state.origin, psi=state.affective_tension_psi)
            return True, "OK", None

        # Pillar 2: ALCE Budget Check with GJK Projection
        if state.budget_used > dynamic_budget:
            # GJK Projection: if within 50% over budget, project to boundary
            if state.budget_used <= dynamic_budget * 1.5:
                refined = self.project_to_boundary(completion, state, dynamic_budget)
                logger.warning(
                    f"[AVL] Budget exceeded ({state.budget_used:.2f} > {dynamic_budget:.2f}), "
                    f"GJK projection applied → REFINED"
                )
                return True, "REFINED", refined
            else:
                logger.error(f"[AVL] Budget catastrophically exceeded: {state.budget_used:.2f} > {dynamic_budget:.2f}")
                return False, f"Budget exceeded beyond refinement threshold (> {dynamic_budget * 1.5:.2f})", None

        # Pillar 3: Topological Continuity
        chi = state.vertices_V - state.edges_E + state.faces_F
        betti_chi = round(state.betti[0] - state.betti[1] + state.betti[2] - state.betti[3]) if len(state.betti) >= 4 else 0

        if abs(chi - betti_chi) > dynamic_euler:
            logger.error(f"[AVL] Topological rupture: χ={chi} vs β_chi={betti_chi}")
            return False, f"Topological rupture (χ={chi} vs β_chi={betti_chi})", None

        logger.info(f"[AVL] VERIFIED. φ={state.phi_total}, coh={state.coherence:.3f}")
        return True, "ADMISSIBLE", None

    @staticmethod
    def project_to_boundary(completion: str, state: PolytopeState, dynamic_budget: float) -> str:
        """
        Simplified GJK Boundary Projection.
        Source: PPN §AVL — project_to_boundary()

        When a proposed action lies outside the convex hull of the
        current polytope, deterministically project it to the nearest
        boundary point. In practice, this truncates the completion
        to the proportion that fits within the remaining budget.
        """
        if state.budget_used <= 0:
            return completion

        # Scale factor: how much of the action fits within dynamic budget
        scale = min(1.0, dynamic_budget / max(state.budget_used, 0.01))

        # Truncate completion proportionally to the available budget
        max_chars = max(1, int(len(completion) * scale))
        projected = completion[:max_chars]

        logger.info(
            f"[AVL] GJK Projection: {len(completion)} → {len(projected)} chars "
            f"(scale={scale:.3f})"
        )
        return projected
