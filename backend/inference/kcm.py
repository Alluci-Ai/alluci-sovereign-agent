import torch
import numpy as np


class KCMGeodesicCost:
    """
    KCM Geodesic Cost Function.
    Source: PPN §KCM — cost_evaluator.hpp::compute_geodesic()

    Calculates the 'Topological distance' to goal state.
    Used by the planner to penalize actions that drift from the manifold.
    """
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

    def select_best_path(self, candidates_betti: list, 
                         goal_betti: torch.Tensor, 
                         psi: float) -> int:
        """Helper to find the candidate with minimum geodesic cost."""
        costs = [self.compute(torch.tensor(b), goal_betti, psi) for b in candidates_betti]
        return int(np.argmin(costs))
