from ..logging_config import get_logger
from typing import Dict, Any, Optional, List
from .dpk import PolytopeState

logger = get_logger("HealthMonitor")

class PVTManifoldHealthMonitor:
    """
    PVT Manifold Health Monitor.
    Source: AAP §PVT — health_check.cpp::eval_state()

    Evaluates the three-layer health of the agent using spec-compliant formulas:
      - Pressure (P): Constraint density / admissible volume
      - Volume (V): Hyper-volume of the admissible polytope (agency)
      - Temperature (T): Entropy spike / Betti stability metric
    """
    RUPTURE_THRESHOLD = 0.8  # T above this = manifold rupture

    def __init__(self):
        self._prev_betti: Optional[List[float]] = None
        self._prev_coherence: Optional[float] = None
        self._last_pvt: Dict[str, float] = {"P": 0.0, "V": 1.0, "T": 0.0}

    def evaluate(self, state: PolytopeState) -> Dict[str, Any]:
        """
        Returns a health report with PVT triple and status: HEALTHY, WARN, or CRITICAL.

        Formulas:
          P = Active_Constraints / Admissible_Volume
          V = (1 - budget_used) × coherence
          T = Δβ_norm + KL(P_t || P_{t-1})
        """
        # === Pressure: Constraint density ===
        # Active constraints = count of non-zero Betti numbers (topological features)
        active_constraints = sum(1 for b in state.betti if abs(b) > 0.5)
        # Admissible volume proxy = (1 - budget) * coherence
        V_agency = max((1.0 - state.budget_used) * max(state.coherence, 0.01), 1e-6)
        P = min(1.0, active_constraints / (V_agency * 4.0 + 1e-6))  # Normalize to [0, 1]

        # === Volume: Available agency ===
        V = max(0.0, min(1.0, V_agency))

        # === Temperature: Entropy spike detection ===
        T = 0.0
        if self._prev_betti is not None:
            # Δβ_norm: normalized Betti number shift
            delta_b = sum(abs(state.betti[i] - self._prev_betti[i]) 
                         for i in range(min(len(state.betti), len(self._prev_betti))))
            max_shift = len(state.betti) * 2.0
            delta_b_norm = min(1.0, delta_b / max(max_shift, 1.0))

            # KL divergence proxy between P_t and P_{t-1}
            kl_proxy = 0.0
            if self._prev_coherence is not None:
                kl_proxy = abs(state.coherence - self._prev_coherence)

            T = min(1.0, delta_b_norm + kl_proxy)

        # Store state for temporal delta
        self._prev_betti = list(state.betti)
        self._prev_coherence = state.coherence
        self._last_pvt = {"P": round(P, 4), "V": round(V, 4), "T": round(T, 4)}

        # === Status evaluation ===
        issues = []
        score = 1.0

        # Temperature check (most critical)
        is_ruptured = T > self.RUPTURE_THRESHOLD
        if is_ruptured:
            issues.append(f"Manifold Rupture: T={T:.3f} exceeds threshold {self.RUPTURE_THRESHOLD}")
            score *= 0.2
        elif T > 0.5:
            issues.append(f"Topological Instability: T={T:.3f}")
            score *= 0.6

        # Pressure check
        if P > 0.8:
            issues.append(f"High Manifold Pressure: P={P:.3f}")
            score *= 0.7
        elif P > 0.5:
            issues.append(f"Elevated Pressure: P={P:.3f}")
            score *= 0.9

        # Volume check (low volume = low agency)
        if V < 0.2:
            issues.append(f"Low Agency Volume: V={V:.3f}")
            score *= 0.5
        elif V < 0.5:
            issues.append(f"Constrained Agency: V={V:.3f}")
            score *= 0.8

        # Legacy checks for backward compatibility
        if state.coherence < 0.3:
            issues.append("Topological Rupture: Low Coherence")
            score *= 0.5
        elif state.coherence < 0.7:
            issues.append("Topological Drift: Medium Coherence")
            score *= 0.8

        if state.budget_used > 0.9:
            issues.append("Execution Stress: High Lipschitz Budget")
            score *= 0.7

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
            "phi_total": state.phi_total,
            "pvt": self._last_pvt,
            "is_ruptured": is_ruptured,
            "psi": state.affective_tension_psi,
            "coherence": state.coherence
        }

    def is_ruptured(self) -> bool:
        """Check if the last evaluation detected a manifold rupture."""
        return self._last_pvt.get("T", 0.0) > self.RUPTURE_THRESHOLD

    def get_last_pvt(self) -> Dict[str, float]:
        """Return the most recent PVT triple for WebSocket push."""
        return self._last_pvt
