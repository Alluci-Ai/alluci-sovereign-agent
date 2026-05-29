import time
import math
import ctypes
import os
import platform
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("MemoryDecay")

# Load native library
_native_lib = None
try:
    _dir = os.path.dirname(os.path.abspath(__file__))
    _build_dir = os.path.join(_dir, "build")
    _system = platform.system()
    _candidates = {
        "Darwin": os.path.join(_build_dir, "libaffect_kernel.dylib"),
        "Linux":  os.path.join(_build_dir, "libaffect_kernel.so"),
        "Windows": os.path.join(_build_dir, "affect_kernel.dll"),
    }
    _lib_path = _candidates.get(_system)
    
    if _lib_path and os.path.isfile(_lib_path):
        _native_lib = ctypes.CDLL(_lib_path)
        _native_lib.decay_retention_batch.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.c_float
        ]
        _native_lib.decay_retention_batch.restype = None
        logger.info("[MemoryDecay] Native C++ Kernel Loaded.")
    else:
        logger.info("[MemoryDecay] Native kernel not found. Using Python fallback.")
except Exception as e:
    logger.warning(f"[MemoryDecay] Failed to initialize native instance: {e}. Falling back to Python.")
    _native_lib = None


class MemoryTopologyDecay:
    """
    Memory Topology Decay.
    Source: AAP §Memory — memory_manager.hpp::apply_decay()
    """
    def __init__(self, half_life: float = 3600.0 * 24): # 24 hours
        self.half_life = half_life

    def calculate_retention(self, last_accessed: float, 
                             topological_importance: float = 1.0,
                             betti_1_support: float = 0.0) -> float:
        """
        Calculates retention score ∈ [0, 1].
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
        n = len(memories)
        
        if n == 0:
            return []
            
        current_time = time.time()
        
        if _native_lib:
            # Batch process in C++
            delta_t_arr = (ctypes.c_float * n)()
            topo_imp_arr = (ctypes.c_float * n)()
            betti_1_arr = (ctypes.c_float * n)()
            out_arr = (ctypes.c_float * n)()
            
            for i, mem in enumerate(memories):
                last_accessed = mem.get("last_accessed", current_time)
                delta_t_arr[i] = current_time - last_accessed
                
                topo_imp_arr[i] = mem.get("topological_importance", 1.0)
                
                betti_support = mem.get("betti_1_support", 0.0)
                if has_loops and betti_support > 0:
                    betti_support *= 2.0
                betti_1_arr[i] = betti_support
                
            _native_lib.decay_retention_batch(out_arr, delta_t_arr, topo_imp_arr, betti_1_arr, n, ctypes.c_float(self.half_life))
            
            result = []
            for i, mem in enumerate(memories):
                retention = out_arr[i]
                if not self.should_prune(retention):
                    mem["retention_score"] = float(retention)
                    result.append(mem)
            return result

        # Fallback
        result = []
        for mem in memories:
            last_accessed = mem.get("last_accessed", current_time)
            importance = mem.get("topological_importance", 1.0)
            betti_support = mem.get("betti_1_support", 0.0)

            if has_loops and betti_support > 0:
                betti_support *= 2.0

            retention = self.calculate_retention(
                last_accessed, importance, betti_support
            )

            if not self.should_prune(retention):
                mem["retention_score"] = retention
                result.append(mem)

        return result
