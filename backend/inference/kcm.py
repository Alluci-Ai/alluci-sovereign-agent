try:
    import torch
except ImportError:
    class TorchPlaceholder:
        def __getattr__(self, name):
            # Special case for nn.Module to avoid base class crashes
            if name == 'nn': return TorchPlaceholder()
            if name == 'Module': return object 
            def placeholder(*args, **kwargs):
                raise ImportError("torch is required for this operation, but is not installed on this system.")
            return placeholder
    torch = TorchPlaceholder()

import numpy as np
import math

class KCMGeodesicCost:
    PSI_HIGH_TENSION = 700

    def compute(self, betti_current, betti_goal, psi: float) -> float:
        if not hasattr(torch, "sum"):
             return 0.0
        dist = torch.sum(torch.abs(betti_current.float() - betti_goal.float())).item()
        cost = dist * (1.0 + psi)
        return float(cost)

    def hyperbolic_penalty(self, psi: float, latency_ms: float) -> float:
        psi_scaled = psi * 1024.0
        return math.cosh(psi_scaled / 1024.0) * latency_ms

    def select_model(self, psi: float, strong_latency_ms: float = 3000.0,
                     light_latency_ms: float = 200.0) -> str:
        psi_int = int(psi * 1024)
        if psi_int < self.PSI_HIGH_TENSION:
            return "strong"
        return "light"

    def select_best_path(self, candidates_betti: list, 
                         goal_betti, 
                         psi: float) -> int:
        costs = [self.compute(b, goal_betti, psi) for b in candidates_betti]
        return int(np.argmin(costs))
