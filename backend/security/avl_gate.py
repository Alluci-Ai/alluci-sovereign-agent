import logging
from typing import Tuple
from .dpk import PolytopeState

logger = logging.getLogger("AVL")


class AVLGate:
    """
    Action Verification Loop.
    Source: PPN §AVL — action_verifier.hpp::verify()

    Three-pillar LLM output safety gate:
      1. Sovereign Attribution   (unsigned manifold → reject)
      2. ALCE Gradient Smoothness (Lipschitz budget exceeded → reject)
      3. Topological Continuity   (Euler mismatch → reject)
    """
    BUDGET_LIMIT = 1.0       # Max Lipschitz budget consumption
    MAX_EULER_DEVIATION = 2  # Consistent with DPK tolerance

    def verify(self, completion: str,
               state: PolytopeState) -> Tuple[bool, str]:
        """
        Returns (is_safe, reason).
        All three pillars must pass for the completion to be verified.
        """
        # Pillar 1: Sovereign Attribution Check
        if state.signature_hash == 0:
            logger.critical("[AVL) UNSIGNED manifold — rejecting completion")
            return False, "Unsigned manifold state"

        # Pillar 2: ALCE Gradient Smoothness Check
        if state.budget_used > self.BUDGET_LIMIT:
            logger.warning(
                f"[AVL] Lipschitz budget exceeded: {state.budget_used:.3f}"
            )
            return False, (
                f"Manifold deformation budget exceeded "
                f"({state.budget_used:.2f} > 1.0)"
            )

        # Pillar 3: Topological Continuity Check
        chi = state.vertices_V - state.edges_E + state.faces_F
        if len(state.betti) >= 4:
            betti_chi = round(
                state.betti[0] - state.betti[1] +
                state.betti[2] - state.betti[3]
            )
        else:
            betti_chi = 0
            
        if abs(chi - betti_chi) > self.MAX_EULER_DEVIATION:
            logger.error(
                f"[AVL] Topological rupture: χ={chi} vs β_chi={betti_chi}"
            )
            return False, (
                f"Topological rupture detected (χ={chi} vs β_chi={betti_chi})"
            )

        logger.info(
            f"[AVL] VERIFIED. φ={state.phi_total}, coh={state.coherence:.3f}"
        )
        return True, "OK"
