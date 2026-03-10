import time
import math
from typing import Dict, Any

class MemoryTopologyDecay:
    """
    Memory Topology Decay.
    Source: AAP §Memory — memory_manager.hpp::apply_decay()

    Simulates 'forgetting' as a topological contraction.
    Weights weaken according to a Sigmoid-Manifold function.
    """
    def __init__(self, half_life: float = 3600.0 * 24): # 24 hours
        self.half_life = half_life

    def calculate_retention(self, last_accessed: float, 
                             topological_importance: float = 1.0) -> float:
        """
        Calculates retention score ∈ [0, 1].
        Importance (Φ) slows down the decay rate.
        """
        delta_t = time.time() - last_accessed
        
        # λ = ln(2) / half_life
        decay_constant = 0.693147 / self.half_life
        
        # Topological Persistence Boost: more important nodes last longer
        lambda_adj = decay_constant / max(1.0, topological_importance)
        
        retention = math.exp(-lambda_adj * delta_t)
        return float(retention)

    def should_prune(self, retention: float, threshold: float = 0.1) -> bool:
        """Prune if manifold contribution is below threshold."""
        return retention < threshold
