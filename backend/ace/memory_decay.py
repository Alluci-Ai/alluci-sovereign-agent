import time
import math
from typing import Dict, Any, List, Optional

class MemoryTopologyDecay:
    """
    Memory Topology Decay.
    Source: AAP §Memory — memory_manager.hpp::apply_decay()

    Simulates 'forgetting' as a topological contraction.
    Weights weaken according to a Sigmoid-Manifold function.

    Betti Persistence: Memories that support Betti-1 holes (loops/tunnels)
    in the current strategic manifold are preserved longer;
    topologically 'flat' memories are pruned to save compute.
    """
    def __init__(self, half_life: float = 3600.0 * 24): # 24 hours
        self.half_life = half_life

    def calculate_retention(self, last_accessed: float, 
                             topological_importance: float = 1.0,
                             betti_1_support: float = 0.0) -> float:
        """
        Calculates retention score ∈ [0, 1].

        Parameters:
          - topological_importance (Φ): slows down the decay rate
          - betti_1_support: if > 0, the memory supports a loop/tunnel
            in the strategic manifold, granting a persistence boost
        """
        delta_t = time.time() - last_accessed
        
        # λ = ln(2) / half_life
        decay_constant = 0.693147 / self.half_life
        
        # Topological Persistence Boost: more important nodes last longer
        lambda_adj = decay_constant / max(1.0, topological_importance)

        # Betti-1 Persistence: memories supporting holes (loops) in the
        # manifold get their half-life multiplied by (1 + betti_1_support)
        if betti_1_support > 0.0:
            betti_boost = 1.0 + min(betti_1_support, 5.0)  # Cap at 6× slower decay
            lambda_adj /= betti_boost
        
        retention = math.exp(-lambda_adj * delta_t)
        return float(retention)

    def should_prune(self, retention: float, threshold: float = 0.1) -> bool:
        """Prune if manifold contribution is below threshold."""
        return retention < threshold

    def filter_by_persistence(self, memories: List[Dict[str, Any]],
                               current_betti: Optional[List[float]] = None) -> List[Dict[str, Any]]:
        """
        Filter a list of memories using Betti persistence.
        Memories supporting Betti-1 features (loops) are retained;
        topologically flat memories are candidate for pruning.
        """
        if not current_betti or len(current_betti) < 2:
            return memories

        # Betti-1 > 0 means loops exist in the manifold; preserve supporting memories
        has_loops = current_betti[1] > 0.5

        result = []
        for mem in memories:
            last_accessed = mem.get("last_accessed", time.time())
            importance = mem.get("topological_importance", 1.0)
            betti_support = mem.get("betti_1_support", 0.0)

            # If manifold has active loops, boost memories that support them
            if has_loops and betti_support > 0:
                betti_support *= 2.0  # Double the persistence

            retention = self.calculate_retention(
                last_accessed, importance, betti_support
            )

            if not self.should_prune(retention):
                mem["retention_score"] = retention
                result.append(mem)

        return result
