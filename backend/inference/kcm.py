import ctypes
import os
import platform
import logging
import math
import numpy as np

logger = logging.getLogger("KCM")

try:
    import torch
except ImportError:
    class TorchPlaceholder:
        def __getattr__(self, name):
            if name == 'nn': return TorchPlaceholder()
            if name == 'Module': return object 
            def placeholder(*args, **kwargs):
                raise ImportError("torch is required for this operation, but is not installed on this system.")
            return placeholder
    torch = TorchPlaceholder()

_native_lib = None
try:
    _dir = os.path.dirname(os.path.abspath(__file__))
    _build_dir = os.path.join(_dir, "build")
    _system = platform.system()
    _candidates = {
        "Darwin": os.path.join(_build_dir, "libtopology_kernel.dylib"),
        "Linux":  os.path.join(_build_dir, "libtopology_kernel.so"),
        "Windows": os.path.join(_build_dir, "topology_kernel.dll"),
    }
    _lib_path = _candidates.get(_system)
    
    if _lib_path and os.path.isfile(_lib_path):
        _native_lib = ctypes.CDLL(_lib_path)
        _native_lib.kcm_geodesic_cost.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_float,
            ctypes.c_int
        ]
        _native_lib.kcm_geodesic_cost.restype = ctypes.c_float
        logger.info("[KCM] Native C++ Geodesic Cost Kernel Loaded.")
    else:
        logger.info("[KCM] Native kernel not found. Using Python fallback.")
except Exception as e:
    logger.warning(f"[KCM] Failed to initialize native instance: {e}. Falling back to Python.")
    _native_lib = None


class KCMGeodesicCost:
    PSI_HIGH_TENSION = 700

    def compute(self, betti_current, betti_goal, psi: float) -> float:
        if hasattr(betti_current, 'detach'):
            betti_current = betti_current.detach().cpu().numpy()
        if hasattr(betti_goal, 'detach'):
            betti_goal = betti_goal.detach().cpu().numpy()
            
        b_curr = np.array(betti_current, dtype=np.float32)
        b_goal = np.array(betti_goal, dtype=np.float32)
        
        if _native_lib:
            try:
                curr_ptr = b_curr.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
                goal_ptr = b_goal.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
                res = _native_lib.kcm_geodesic_cost(curr_ptr, goal_ptr, psi, len(b_curr))
                return float(res)
            except Exception as e:
                logger.warning(f"Error in native cost call: {e}. Falling back to Python.")

        # Fallback to pure-Python/NumPy implementation
        dist = np.sum(np.abs(b_curr - b_goal))
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
