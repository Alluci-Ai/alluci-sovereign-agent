import numpy as np
from typing import List, Optional, Dict, Any
from ..logging_config import get_logger

logger = get_logger("TrajectoryTracker")


class TrajectoryTracker:
    """
    [ Polytope Trajectory Continuity & Curvature Engine ]
    Source: AAP §PVT — Frenet-Serret State Manifold Geometry

    Tracks continuous thought trajectory γ(t) ∈ R^d across agent iterations,
    computing geodesic velocity v(t), acceleration a(t), and trajectory
    curvature κ(t) to catch abrupt prompt injection shocks or erratic cognitive snaps.
    """
    def __init__(self, max_history: int = 10, critical_curvature: float = 5.0):
        self.max_history = max_history
        self.critical_curvature = critical_curvature
        self.history: List[np.ndarray] = []
        self._last_metrics: Dict[str, float] = {
            "velocity_norm": 0.0,
            "accel_norm": 0.0,
            "curvature": 0.0,
            "is_ruptured": 0.0
        }

    def reset(self) -> None:
        """Clears the trajectory history."""
        self.history.clear()
        self._last_metrics = {
            "velocity_norm": 0.0,
            "accel_norm": 0.0,
            "curvature": 0.0,
            "is_ruptured": 0.0
        }

    def push_state(self, state_vector: np.ndarray) -> Dict[str, float]:
        """
        Appends a new continuous state vector γ(t) and updates velocity,
        acceleration, and Frenet-Serret curvature.
        """
        vec = np.asarray(state_vector, dtype=np.float64).flatten()
        self.history.append(vec)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        metrics = self._compute_kinematics()
        self._last_metrics = metrics
        return metrics

    def _compute_kinematics(self) -> Dict[str, float]:
        """Computes velocity, acceleration, and curvature from state history."""
        n = len(self.history)
        if n < 2:
            return {
                "velocity_norm": 0.0,
                "accel_norm": 0.0,
                "curvature": 0.0,
                "is_ruptured": 0.0
            }

        # Current and previous states
        p_t = self.history[-1]
        p_t1 = self.history[-2]

        # Velocity: v(t) = γ(t) - γ(t-1)
        v = p_t - p_t1
        v_norm = float(np.linalg.norm(v))

        if n < 3:
            return {
                "velocity_norm": round(v_norm, 4),
                "accel_norm": 0.0,
                "curvature": 0.0,
                "is_ruptured": 0.0
            }

        p_t2 = self.history[-3]

        # Acceleration: a(t) = γ(t) - 2γ(t-1) + γ(t-2)
        a = p_t - (2.0 * p_t1) + p_t2
        a_norm = float(np.linalg.norm(a))

        # Frenet-Serret Curvature in R^d:
        # κ = sqrt( ||v||^2 ||a||^2 - (v · a)^2 ) / (||v||^3 + ε)
        if v_norm < 1e-7:
            kappa = 0.0
        else:
            v_dot_a = float(np.dot(v, a))
            cross_term_sq = (v_norm ** 2) * (a_norm ** 2) - (v_dot_a ** 2)
            cross_term = np.sqrt(max(0.0, cross_term_sq))
            kappa = float(cross_term / (v_norm ** 3 + 1e-9))

        is_ruptured = 1.0 if kappa > self.critical_curvature else 0.0
        if is_ruptured > 0:
            logger.warning(
                f"[TRAJECTORY] Curvature breach detected: κ={kappa:.3f} > {self.critical_curvature:.1f} "
                f"(||v||={v_norm:.3f}, ||a||={a_norm:.3f})"
            )

        return {
            "velocity_norm": round(v_norm, 4),
            "accel_norm": round(a_norm, 4),
            "curvature": round(kappa, 4),
            "is_ruptured": is_ruptured
        }

    def get_last_metrics(self) -> Dict[str, float]:
        """Returns the most recent kinematic and curvature metrics."""
        return self._last_metrics

    def is_ruptured(self) -> bool:
        """Returns True if the current trajectory curvature exceeds the critical threshold."""
        return self._last_metrics.get("is_ruptured", 0.0) > 0.5
