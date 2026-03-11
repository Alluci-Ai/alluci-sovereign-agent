import torch
import numpy as np
import math


class KCMGeodesicCost:
    """
    KCM Geodesic Cost Function.
    Source: PPN §KCM — cost_evaluator.hpp::compute_geodesic()

    Calculates the 'Topological distance' to goal state.
    Used by the planner to penalize actions that drift from the manifold.
    """
    # ψ threshold (integer scale 0-1024) above which hyperbolic penalty activates
    PSI_HIGH_TENSION = 700

    def compute(self, betti_current: torch.Tensor, 
                betti_goal: torch.Tensor, 
                psi: float) -> float:
        """
        Cost = Σ |β_curr - β_goal| * (1 + psi)
        """
        # 1. Hamming/Manhattan distance in topological space
        dist = torch.sum(torch.abs(betti_current.float() - betti_goal.float())).item()
        
        # 2. Affective Weighting: high tension (psi) makes drift more 'expensive'
        cost = dist * (1.0 + psi)
        
        return float(cost)

    def hyperbolic_penalty(self, psi: float, latency_ms: float) -> float:
        """
        KCM Hyperbolic Penalty.
        Source: PPN §KCM — hyperbolic_cost()

        Penalty = cosh(ψ / 1024) × latency_ms

        High ψ (>700) exponentially increases the cost of slow (Strong) models,
        forcing routing to fast/deterministic (Light) models.
        """
        # ψ is in [0.0, 1.0] float scale; convert to 1024-scale internally
        psi_scaled = psi * 1024.0
        return math.cosh(psi_scaled / 1024.0) * latency_ms

    def select_model(self, psi: float, strong_latency_ms: float = 3000.0,
                     light_latency_ms: float = 200.0) -> str:
        """
        ψ-Modulated Model Selection.
        Returns "strong" or "light" based on ψ threshold and penalty.

        Below PSI_HIGH_TENSION (700/1024 ≈ 0.684): always use strong model.
        Above threshold: the hyperbolic penalty forces routing to light.
        """
        psi_int = int(psi * 1024)

        # Gate: below high-tension threshold, always prefer strong
        if psi_int < self.PSI_HIGH_TENSION:
            return "strong"

        # Above threshold: strong model's cost grows prohibitively
        return "light"

    def select_best_path(self, candidates_betti: list, 
                         goal_betti: torch.Tensor, 
                         psi: float) -> int:
        """Helper to find the candidate with minimum geodesic cost."""
        costs = [self.compute(torch.tensor(b), goal_betti, psi) for b in candidates_betti]
        return int(np.argmin(costs))
