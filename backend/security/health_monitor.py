import logging
from typing import Dict, Any
from .dpk import PolytopeState

logger = logging.getLogger("HealthMonitor")

class PVTManifoldHealthMonitor:
    """
    PVT Manifold Health Monitor.
    Source: AAP §PVT — health_check.cpp::eval_state()

    Evaluates the three-layer health of the agent:
      - Physical: Biometric tension context (psi)
      - Virtual: Execution stability (budgets)
      - Topological: Manifold integrity (coherence)
    """
    def evaluate(self, state: PolytopeState) -> Dict[str, Any]:
        """
        Returns a health report with a status: HEALTHY, WARN, or CRITICAL.
        """
        issues = []
        score = 1.0

        # Layer 1: Topological (Coherence)
        if state.coherence < 0.3:
            issues.append("Topological Rupture: Low Coherence")
            score *= 0.5
        elif state.coherence < 0.7:
            issues.append("Topological Drift: Medium Coherence")
            score *= 0.8

        # Layer 2: Virtual (Budget)
        if state.budget_used > 0.9:
            issues.append("Execution Stress: High Lipschitz Budget")
            score *= 0.7

        # Layer 3: Physical (Tension)
        if state.affective_tension_psi > 0.8:
            issues.append("Affective Overload: High Tension")
            score *= 0.9

        status = "HEALTHY"
        if score < 0.4:
            status = "CRITICAL"
        elif score < 0.8:
            status = "WARN"

        return {
            "status": status,
            "score": round(score, 3),
            "issues": issues,
            "phi_total": state.phi_total
        }
