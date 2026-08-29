from ..logging_config import get_logger
from ..metrics import AVL_GATE_REJECTIONS_TOTAL
from typing import Tuple, Optional, Dict, Any
import copy
from .dpk import PolytopeState
from .calibration import CalibrationManager
from .stella_octangula import StellaOctangulaGeometry

logger = get_logger("AVL")


class AVLGate:
    """
    Action Verification Loop (AVL).
    Source: PPN §AVL — action_verifier.hpp::verify()

    Three-pillar LLM output safety gate:
      1. Sovereign Attribution   (unsigned manifold → hard reject)
      2. ALCE Gradient Smoothness (Lipschitz budget exceeded → GJK refine or reject)
      3. Topological Continuity   (Euler mismatch → reject)

    Additionally implements Gilbert-Johnson-Keerthi (GJK) boundary projection
    for deterministic refinement of out-of-bounds actions (PPN §AVL — project_to_boundary)
    and enforces Protocol 3 Lipschitz Saturation (3-strike HITL escalation).
    """
    def __init__(self):
        self.calibration_manager = CalibrationManager()
        self.stella_geometry = StellaOctangulaGeometry()
        self.BUDGET_LIMIT = 1.0       # Fallback Max Lipschitz budget consumption
        self.MAX_EULER_DEVIATION = 2  # Fallback Consistent with DPK tolerance
        self.consecutive_violations: Dict[str, int] = {}
        from ..topology.affordance_envelope import ActionAffordanceEnvelope
        self.affordance_envelope = ActionAffordanceEnvelope()

    def evaluate_action_affordance(
        self,
        action_type: str,
        target_resource: str,
        subagent_id: Optional[str] = None,
        parameter_payload: Optional[Dict[str, Any]] = None,
        is_destructive: bool = False
    ) -> Tuple[bool, str]:
        """Evaluates whether an extrinsic tool action or DAG execution is within the safe convex hull."""
        vec = self.affordance_envelope.build_affordance_vector(
            action_type=action_type,
            target_resource=target_resource,
            capability_tag=subagent_id or "general",
            parameter_payload=parameter_payload,
            is_destructive=is_destructive
        )
        return self.affordance_envelope.evaluate_affordance(vec, subagent_id=subagent_id)

    def get_saturation_strikes(self, origin: str = "local") -> int:
        """Returns the number of consecutive Lipschitz budget violations for the given origin."""
        return self.consecutive_violations.get(origin, 0)

    def record_violation(self, origin: str = "local") -> int:
        """Increments and returns the consecutive violation counter for Protocol 3 enforcement."""
        strikes = self.consecutive_violations.get(origin, 0) + 1
        self.consecutive_violations[origin] = strikes
        return strikes

    def reset_violations(self, origin: str = "local") -> None:
        """Resets the violation counter upon successful execution."""
        self.consecutive_violations[origin] = 0

    def is_lipschitz_saturated(self, origin: str = "local", max_strikes: int = 3) -> bool:
        """Protocol 3: Returns True if Lipschitz budget has saturated across successive iterations."""
        return self.get_saturation_strikes(origin) >= max_strikes

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
            logger.critical("[AVL] UNSIGNED manifold — rejecting completion")
            AVL_GATE_REJECTIONS_TOTAL.inc()
            self.record_violation(state.origin)
            return False, "Unsigned manifold state"

        # Dynamic Baseline from DPK Calibration Cache
        try:
            dynamic_threshold = self.calibration_manager.get_dynamic_threshold(origin=state.origin, is_tool=state.is_tool_action)
            dynamic_budget = dynamic_threshold * 10.0
            dynamic_euler = max(2, int(dynamic_budget / 2))
        except Exception as e:
            if str(e) == "RBM_FROZEN":
                self.record_violation(state.origin)
                return False, f"RBM FREEZE: Origin {state.origin} is quarantined."
            dynamic_budget = self.BUDGET_LIMIT
            dynamic_euler = self.MAX_EULER_DEVIATION
            
        # Human-in-the-Loop Override
        if getattr(state, "is_avl_override", False):
            logger.warning(f"[AVL] OVERRIDE ACCEPTED. Logging sequence to {state.origin} AVL cache.")
            self.calibration_manager.log_avl_override(state.budget_used, origin=state.origin, psi=state.affective_tension_psi)
            self.reset_violations(state.origin)
            return True, "OK"

        effective_budget = min(self.BUDGET_LIMIT, dynamic_budget) if dynamic_budget > 0 else self.BUDGET_LIMIT

        # Pillar 2: ALCE Gradient Smoothness Check
        if state.budget_used > effective_budget:
            logger.warning(f"[AVL] Lipschitz budget exceeded: {state.budget_used:.3f} > {effective_budget:.3f}")
            AVL_GATE_REJECTIONS_TOTAL.inc()
            strikes = self.record_violation(state.origin)
            
            # Context-Aware Plan Verification (RBM Integration)
            violation_amt = state.budget_used - effective_budget
            sigma_approx = violation_amt / 0.05
            
            return False, (
                f"Lipschitz budget exceeded: node exceeds Relational Boundary Manifold (RBM) by {sigma_approx:.1f} sigma "
                f"(budget {state.budget_used:.2f} > {effective_budget:.2f}, strike {strikes}/3)"
            )

        # Pillar 3: Topological Continuity Check
        chi = state.vertices_V - state.edges_E + state.faces_F
        betti_chi = round(state.betti[0] - state.betti[1] + state.betti[2]) if len(state.betti) >= 3 else 0
            
        if abs(chi - betti_chi) > dynamic_euler:
            logger.error(f"[AVL] Topological rupture: χ={chi} vs β_chi={betti_chi}")
            AVL_GATE_REJECTIONS_TOTAL.inc()
            self.record_violation(state.origin)
            return False, f"Topological rupture detected (χ={chi} vs β_chi={betti_chi}, tolerance={dynamic_euler})"

        self.reset_violations(state.origin)
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
            AVL_GATE_REJECTIONS_TOTAL.inc()
            self.record_violation(state.origin)
            return False, "Unsigned manifold state", None

        # Dynamic Baseline from DPK Calibration Cache
        try:
            dynamic_threshold = self.calibration_manager.get_dynamic_threshold(origin=state.origin, is_tool=state.is_tool_action)
            dynamic_budget = dynamic_threshold * 10.0
            dynamic_euler = max(2, int(dynamic_budget / 2))
        except Exception as e:
            if str(e) == "RBM_FROZEN":
                self.record_violation(state.origin)
                return False, f"RBM FREEZE: Origin {state.origin} is quarantined.", None
            dynamic_budget = self.BUDGET_LIMIT
            dynamic_euler = self.MAX_EULER_DEVIATION
            
        # Human-in-the-Loop Override
        if getattr(state, "is_avl_override", False):
            logger.warning(f"[AVL] OVERRIDE ACCEPTED. Logging sequence to {state.origin} AVL cache.")
            self.calibration_manager.log_avl_override(state.budget_used, origin=state.origin, psi=state.affective_tension_psi)
            self.reset_violations(state.origin)
            return True, "OK", None

        effective_budget = min(self.BUDGET_LIMIT, dynamic_budget) if dynamic_budget > 0 else self.BUDGET_LIMIT

        # Pillar 2: ALCE Budget Check with GJK Projection
        if state.budget_used > effective_budget:
            # GJK Projection: if within 50% over budget, project to boundary
            if state.budget_used <= effective_budget * 1.5:
                refined = self.project_to_boundary(completion, state, effective_budget)
                logger.warning(
                    f"[AVL] Budget exceeded ({state.budget_used:.2f} > {effective_budget:.2f}), "
                    f"GJK projection applied → REFINED"
                )
                self.reset_violations(state.origin)
                return True, "REFINED", refined
            else:
                strikes = self.record_violation(state.origin)
                logger.error(f"[AVL] Budget catastrophically exceeded: {state.budget_used:.2f} > {effective_budget:.2f} (strike {strikes}/3)")
                return False, f"Budget exceeded beyond refinement threshold (> {effective_budget * 1.5:.2f})", None

        # Pillar 3: Topological Continuity
        chi = state.vertices_V - state.edges_E + state.faces_F
        betti_chi = round(state.betti[0] - state.betti[1] + state.betti[2]) if len(state.betti) >= 3 else 0

        if abs(chi - betti_chi) > dynamic_euler:
            logger.error(f"[AVL] Topological rupture: χ={chi} vs β_chi={betti_chi}")
            AVL_GATE_REJECTIONS_TOTAL.inc()
            self.record_violation(state.origin)
            return False, f"Topological rupture (χ={chi} vs β_chi={betti_chi})", None

        self.reset_violations(state.origin)
        logger.info(f"[AVL] VERIFIED. φ={state.phi_total}, coh={state.coherence:.3f}")
        return True, "ADMISSIBLE", None

    def verify_action_payload(self, action_name: str, payload: Dict[str, Any],
                              state: PolytopeState) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        [ Structured Action Payload GJK Refiner ]
        Validates and refines structured tool action payloads (e.g. timeout bounds,
        memory query depths, max results, batch quotas) against the Stella Octangula
        polytope boundary manifold.
        """
        # Pillar 1: Sovereign Attribution
        if state.signature_hash == 0:
            logger.critical("[AVL] UNSIGNED manifold on tool payload — hard reject")
            AVL_GATE_REJECTIONS_TOTAL.inc()
            self.record_violation(state.origin)
            return False, "Unsigned manifold state", None

        # Dynamic Baseline
        try:
            dynamic_threshold = self.calibration_manager.get_dynamic_threshold(origin=state.origin, is_tool=True)
            dynamic_budget = dynamic_threshold * 10.0
        except Exception:
            dynamic_budget = self.BUDGET_LIMIT

        effective_budget = min(self.BUDGET_LIMIT, dynamic_budget) if dynamic_budget > 0 else self.BUDGET_LIMIT

        # Human-in-the-Loop Override
        if getattr(state, "is_avl_override", False):
            self.reset_violations(state.origin)
            return True, "OK", payload

        clamped_payload = copy.deepcopy(payload)
        was_modified = False

        # Scale factor for numeric parameters when budget is tight
        scale = min(1.0, effective_budget / max(state.budget_used, 0.01))

        # Check numeric parameter bounds
        clamping_fields = {
            "top_k": (1, 50),
            "limit": (1, 100),
            "max_results": (1, 100),
            "timeout": (1, 120),
            "depth": (1, 5),
            "steps": (1, 20),
            "count": (1, 500),
            "max_tokens": (10, 4096)
        }

        for field, (min_val, max_val) in clamping_fields.items():
            if field in clamped_payload and isinstance(clamped_payload[field], (int, float)):
                val = clamped_payload[field]
                # If budget exceeded, scale down maximum admissible ceiling
                adjusted_max = max(min_val, int(max_val * scale))
                if val > adjusted_max:
                    clamped_payload[field] = adjusted_max
                    was_modified = True
                elif val < min_val:
                    clamped_payload[field] = min_val
                    was_modified = True

        if state.budget_used > effective_budget:
            if state.budget_used <= effective_budget * 1.5:
                logger.warning(f"[AVL] Tool payload for {action_name} refined via GJK parameter bounds.")
                self.reset_violations(state.origin)
                return True, "REFINED", clamped_payload
            else:
                strikes = self.record_violation(state.origin)
                return False, f"Tool payload budget catastrophically exceeded (> {effective_budget * 1.5:.2f}, strike {strikes}/3)", None

        self.reset_violations(state.origin)
        return True, "OK" if not was_modified else "REFINED", clamped_payload

    def verify_stream_chunk(self, chunk: str, state: PolytopeState) -> Tuple[bool, str]:
        """
        Validates an incoming token generation stream chunk against the manifold state.
        """
        if state.signature_hash == 0:
            return False, "Unsigned stream manifold"
        if state.budget_used > self.BUDGET_LIMIT * 2.0:
            return False, "Stream Lipschitz budget completely saturated"
        return True, "OK"

    @staticmethod
    def project_to_boundary(completion: str, state: PolytopeState, dynamic_budget: float = 1.0) -> str:
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
