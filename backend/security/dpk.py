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
        ("hardware_status", ctypes.c_int32),
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
    hardware_status: int = 0     # 0=Unconfigured, 1=Unavailable, 2=Active
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
        """
        Loads the native C++ DPK kernel.
        Resolution order:
          1. DPK_LIB_PATH environment variable (CI / Docker)
          2. build/ directory relative to this file (local dev)
          3. Returns None if not found — Python fallback activates
        """
        import ctypes
        import platform

        # 1. Env override (used in CI and Docker)
        env_path = os.environ.get("DPK_LIB_PATH")
        if env_path and os.path.isfile(env_path):
            logger.info(f"[DPK] Loading kernel from DPK_LIB_PATH: {env_path}")
            try:
                return ctypes.CDLL(env_path)
            except OSError as e:
                logger.warning(f"[DPK] Failed to load from DPK_LIB_PATH: {e}")

        # 2. Convention path relative to this file
        security_dir = os.path.dirname(os.path.abspath(__file__))
        build_dir = os.path.join(security_dir, "build")
        system = platform.system()

        candidates = {
            "Darwin": os.path.join(build_dir, "libdpk.dylib"),
            "Linux":  os.path.join(build_dir, "libdpk.so"),
            "Windows": os.path.join(build_dir, "dpk.dll"),
        }
        lib_path = candidates.get(system)

        if lib_path and os.path.isfile(lib_path):
            try:
                lib = ctypes.CDLL(lib_path)
                logger.info(f"[DPK] Native kernel loaded: {lib_path}")
                return lib
            except OSError as e:
                logger.warning(f"[DPK] Failed to load native kernel: {e}")

        logger.info("[DPK] Native kernel not found. Using Python fallback (full fidelity).")
        return None

    def compute_signature_hash(self, betti: list, chi: int) -> int:
        """
        Compute a deterministic signature hash from Betti numbers and Euler characteristic.
        AAP-003: SHA256-derived sovereign hash for manifold identity.
        """
        import hashlib
        payload = f"betti={betti}|chi={chi}"
        digest = hashlib.sha256(payload.encode()).digest()
        # Take first 8 bytes as uint64
        return int.from_bytes(digest[:8], byteorder="big")

    def __del__(self):
        if self.native_lib and self.native_instance:
            self.native_lib.dpk_free(self.native_instance)

    def validate_manifold_integrity_py(self, current: PolytopeState) -> bool:
        """Pure Python fallback implementation."""
        if current.signature_hash == 0:
            logger.critical("[DPK] CRITICAL: Unsigned Manifold. Execution Blocked.")
            return False
        if current.hardware_status == 1:
            logger.info("[DPK] BYPASS: Hardware status indicates Lite. Bypassing synthetic tearing checks.")
            return True

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
            topology_shift = sum(abs(current.betti[i] - self.prev_state.betti[i]) for i in range(4))  # type: ignore
            if topology_shift > self.TEARING_THRESHOLD * 10.0:
                logger.warning("[DPK] SAFETY: Manifold Tearing Detected.")
                return False

        self.prev_state = current
        self.initialized = True
        return True

    def authorize_execution(self, state: PolytopeState) -> bool:
        """Entry point for authorization, routes to native or python."""
        
        # 1. Unsigned Manifold Check
        if state.signature_hash == 0:
            logger.critical("[DPK] CRITICAL: Unsigned Manifold detected. Blocking execution.")
            return False
            
        # 2. Euler Characteristic Check
        chi = state.vertices_V - state.edges_E + state.faces_F
        betti_chi = round(state.betti[0] - state.betti[1] + state.betti[2] - state.betti[3])
        if abs(chi - betti_chi) > self.MAX_EULER_DEVIATION:
            logger.error(f"[DPK] TOPOLOGY ERROR: Euler Mismatch ({chi} vs {betti_chi}). Blocking execution.")
            return False
            
        # 3. Native or Fallback
        if self.native_lib and self.native_instance:
            native_state = NativePolytopeState(
                signature_hash=state.signature_hash,
                vertices_V=state.vertices_V,
                edges_E=state.edges_E,
                faces_F=state.faces_F,
                betti=(ctypes.c_float * 4)(*state.betti),
                affective_tension_psi=state.affective_tension_psi,
                hardware_status=state.hardware_status
            )
            is_valid = self.native_lib.dpk_authorize(self.native_instance, ctypes.byref(native_state))
            if is_valid:
                logger.info(f"[DPK] STATE VALID (NATIVE). χ={chi}")
                return True
            else:
                logger.error("[DPK] STATE INVALID (NATIVE). Blocking execution.")
                return False
        
        return self.validate_manifold_integrity_py(state)
        
    def validate_manifold_integrity(self, state: PolytopeState) -> bool:
        """Alias for authorize_execution, used directly by some benchmarks and internal gates."""
        return self.authorize_execution(state)
