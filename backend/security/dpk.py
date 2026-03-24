import logging
from ..logging_config import get_logger
import ctypes
import os
from dataclasses import dataclass
from typing import List, Optional

logger = get_logger("DPK")

# --- Native Struct Definitions ---
class NativePolytopeState(ctypes.Structure):
    _fields_ = [
        ("signature_hash", ctypes.c_uint64),
        ("vertices_V", ctypes.c_int32),
        ("edges_E", ctypes.c_int32),
        ("faces_F", ctypes.c_int32),
        ("betti", ctypes.c_float * 4),
        ("affective_tension_psi", ctypes.c_float),
    ]

# --- Python Model ---
@dataclass
class PolytopeState:
    signature_hash: int          # AAP-003: SHA256-derived sovereign hash
    vertices_V: int              # Simplex vertex count
    edges_E: int                 # Simplex edge count
    faces_F: int                 # Simplex face (triangle) count
    betti: List[float]           # [β₀, β₁, β₂, β₃] topological invariants
    affective_tension_psi: float # ψ ∈ [0.0, 1.0] from BTM (PPN-002)
    phi_total: int = 0           # Φ_total affective-invariant index (PPN-003)
    coherence: float = 0.0       # Coh(P_t) ∈ [0.0, 1.0] (AAP-001)
    budget_used: float = 0.0     # Lipschitz budget consumption (PPN-005)

class DiscreteProjectionKernel:
    """
    Gatekeeper for agent execution logic. Uses C++ Kernel via ctypes
    with a High-Fidelity Python fallback if the binary is unavailable.
    """
    def __init__(self):
        self.prev_state: Optional[PolytopeState] = None
        self.initialized = False
        self.MAX_EULER_DEVIATION = 2
        self.TEARING_THRESHOLD = 0.15
        
        # Load Native Kernel
        self.native_lib = self._load_native_lib()
        self.native_instance = None
        if self.native_lib:
            try:
                self.native_lib.dpk_new.restype = ctypes.c_void_p
                self.native_lib.dpk_free.argtypes = [ctypes.c_void_p]
                self.native_lib.dpk_authorize.argtypes = [ctypes.c_void_p, ctypes.POINTER(NativePolytopeState)]
                self.native_lib.dpk_authorize.restype = ctypes.c_bool
                self.native_instance = self.native_lib.dpk_new()
                logger.info("[DPK] Native C++ Kernel Loaded.")
            except Exception as e:
                logger.warning(f"[DPK] Failed to initialize native instance: {e}. Falling back to Python.")
                self.native_lib = None

    def _load_native_lib(self):
        # 1. Direct environment override (highest priority)
        env_path = os.getenv("DPK_LIB_PATH")
        if env_path:
            try:
                return ctypes.CDLL(env_path)
            except Exception as e:
                logger.warning(f"[DPK] Failed to load library from DPK_LIB_PATH={env_path}: {e}")

        # 2. Dynamic platform-specific discovery in build/ directory
        base_dir = os.path.dirname(os.path.abspath(__file__))
        build_dir = os.path.join(base_dir, "build")
        
        ext = ".so"
        import platform
        if platform.system() == "Darwin":
            ext = ".dylib"
        elif platform.system() == "Windows":
            ext = ".dll"
            
        lib_path = os.path.join(build_dir, f"libdpk{ext}")
        if os.path.exists(lib_path):
            try:
                return ctypes.CDLL(lib_path)
            except Exception as e:
                logger.warning(f"[DPK] Failed to load library at {lib_path}: {e}")
                
        # 3. Legacy path fallback (migration)
        legacy_path = os.path.join(base_dir, f"libdpk{ext}")
        if os.path.exists(legacy_path):
            try:
                return ctypes.CDLL(legacy_path)
            except Exception as e:
                logger.debug(f"[DPK] Legacy library load failed at {legacy_path}: {e}")

        return None

    def __del__(self):
        if self.native_lib and self.native_instance:
            self.native_lib.dpk_free(self.native_instance)

    def validate_manifold_integrity_py(self, current: PolytopeState) -> bool:
        """Pure Python fallback implementation."""
        if current.signature_hash == 0:
            logger.critical("[DPK] CRITICAL: Unsigned Manifold. Execution Blocked.")
            return False

        chi = current.vertices_V - current.edges_E + current.faces_F
        betti_chi = round(current.betti[0] - current.betti[1] + current.betti[2] - current.betti[3])

        if abs(chi - betti_chi) > self.MAX_EULER_DEVIATION:
            logger.error(f"[DPK] TOPOLOGY ERROR: Euler Mismatch. {chi} vs {betti_chi}")
            return False
        
        # Coherence Gate (T-12 Fallback)
        # If coherence drops below 0.3, the manifold is considered too fragmented to authorize.
        if current.coherence < 0.3:
            logger.error(f"[DPK] FRAGMENTATION ERROR: Low Coherence ({current.coherence:.3f}). Execution Blocked.")
            return False

        # Budget Gate
        # Lipschitz budget exceeding 0.9 implies dangerous representation drift.
        if current.budget_used > 0.9:
            logger.warning(f"[DPK] BUDGET EXCEEDED: Lipschitz Drift ({current.budget_used:.3f}).")
            return False

        if self.initialized and current.affective_tension_psi < 0.8:
            topology_shift = sum(abs(current.betti[i] - self.prev_state.betti[i]) for i in range(4))
            if topology_shift > self.TEARING_THRESHOLD * 10.0:
                logger.warning("[DPK] SAFETY: Manifold Tearing Detected.")
                return False

        self.prev_state = current
        self.initialized = True
        return True

    def authorize_execution(self, state: PolytopeState) -> bool:
        """Entry point for authorization, routes to native or python."""
        return self.validate_manifold_integrity(state)
        
    def validate_manifold_integrity(self, state: PolytopeState) -> bool:
        """Alias for authorize_execution, used directly by some benchmarks and internal gates."""
        if self.native_lib and self.native_instance:
            native_state = NativePolytopeState(
                signature_hash=state.signature_hash,
                vertices_V=state.vertices_V,
                edges_E=state.edges_E,
                faces_F=state.faces_F,
                betti=(ctypes.c_float * 4)(*state.betti),
                affective_tension_psi=state.affective_tension_psi
            )
            is_valid = self.native_lib.dpk_authorize(self.native_instance, ctypes.byref(native_state))
            if is_valid:
                logger.info(f"[DPK] STATE VALID (NATIVE). χ={state.vertices_V - state.edges_E + state.faces_F}")
                return True
            else:
                logger.error("[DPK] STATE INVALID (NATIVE). Blocking execution.")
                return False
        
        # Fallback to Python
        return self.validate_manifold_integrity_py(state)
