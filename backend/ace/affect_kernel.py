import ctypes
import os
import platform
import logging
from dataclasses import dataclass

logger = logging.getLogger("AffectKernel")

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

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
        _native_lib.affect_apply_batch.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.c_int32,
            ctypes.c_int32,
            ctypes.c_int32
        ]
        _native_lib.affect_apply_batch.restype = None
        logger.info("[AffectKernel] Native C++ Kernel Loaded.")
    else:
        logger.info("[AffectKernel] Native kernel not found. Using Python fallback.")
except Exception as e:
    logger.warning(f"[AffectKernel] Failed to initialize native instance: {e}. Falling back to Python.")
    _native_lib = None


@dataclass
class AffectiveState:
    # Core Affective Dimensions
    valence: float = 512.0   # 0=pessimistic, 512=neutral, 1024=optimistic
    arousal: float = 0.0     # 0=calm, 1024=maximum arousal
    tension: float = 0.0     # 0=relaxed, 1024=maximum contraction
    
    # [ PPN-010 ] Physical Biometrics (Multimodal Polytope Fusion)
    heart_rate: float = 70.0       # bpm
    hrv: float = 50.0              # ms
    respiratory_rate: float = 16.0 # breaths/min
    
    def fuse_biometrics(self):
        """
        Sub-microsecond projection of raw biometrics into affective dimensions.
        Avoids slow string-to-vector conversion.
        """
        # Baseline heuristics mapping biometrics to affective dimensions
        # High HR + Low HRV + High RR = High Arousal, High Tension, Low Valence (Stress)
        self.arousal = max(0.0, min(1024.0, (self.heart_rate - 60.0) * 10.0 + (self.respiratory_rate - 12.0) * 20.0))
        self.tension = max(0.0, min(1024.0, (100.0 - self.hrv) * 10.0))
        self.valence = max(0.0, min(1024.0, 512.0 + (self.hrv - 50.0) * 5.0 - (self.heart_rate - 70.0) * 2.0))


class AffectKernel:
    """
    Integer-based affective deformation kernel.
    Source: PPN §affect_op.cpp — apply_deformation()

    Applies three sequential fixed-point transforms:
      1. Tension-driven contraction (denominator scaling)
      2. Arousal-driven dilation (bit-shifted multiply)
      3. Valence-driven shear (register bias)
    """
    SCALE = 2048            # Fixed-point scale factor
    NEUTRAL_TENSION = 1024  # Neutral tension coefficient
    MAX_VAL = 32767         # int16 max for manifold safety

    def apply(self, raw_val: float, state: AffectiveState) -> float:
        """
        Apply affective deformation to a single scalar value.
        """
        if _native_lib:
            in_arr = (ctypes.c_float * 1)(raw_val)
            out_arr = (ctypes.c_float * 1)()
            _native_lib.affect_apply_batch(out_arr, in_arr, 1, int(state.tension), int(state.arousal), int(state.valence))
            return out_arr[0]

        # 1. Tension coefficient — contraction denominator
        tension_coeff = self.NEUTRAL_TENSION + int(state.tension * 8)

        # 2. Arousal dilation — fixed-point multiply + bit-shift
        raw_int = int(raw_val * self.SCALE)
        dilated = (raw_int * (self.NEUTRAL_TENSION + int(state.arousal))) >> 10

        # 3. Valence shear — biases semantic register
        dilated += int(state.valence * 512) >> 2

        # 4. ALCE Lipschitz normalization — prevent manifold tearing
        final = (dilated * self.NEUTRAL_TENSION) // max(tension_coeff, 1)
        final = max(-self.MAX_VAL, min(self.MAX_VAL, final))

        return final / float(self.SCALE)

    def apply_tensor(self, t: 'torch.Tensor', state: AffectiveState) -> 'torch.Tensor':
        """Batch-apply deformation to an entire embedding tensor."""
        if not HAS_TORCH:
            raise ImportError("PyTorch required for apply_tensor. Install 'torch' to enable tensor deformation.")
            
        if _native_lib:
            t_contig = t.contiguous().to(torch.float32)
            out = torch.empty_like(t_contig)
            
            n = t_contig.numel()
            out_ptr = ctypes.cast(out.data_ptr(), ctypes.POINTER(ctypes.c_float))
            in_ptr = ctypes.cast(t_contig.data_ptr(), ctypes.POINTER(ctypes.c_float))
            
            _native_lib.affect_apply_batch(
                out_ptr, in_ptr, n, 
                int(state.tension), int(state.arousal), int(state.valence)
            )
            return out.reshape_as(t)

        # Fallback to Python / PyTorch ops
        # 1. Tension coefficient
        tension_coeff = self.NEUTRAL_TENSION + int(state.tension * 8)
        
        # 2. Arousal dilation
        raw_int = (t * self.SCALE).to(torch.long)
        dilated = (raw_int * (self.NEUTRAL_TENSION + int(state.arousal))) >> 10
        
        # 3. Valence shear
        dilated += int(state.valence * 512) >> 2
        
        # 4. ALCE Lipschitz normalization
        final = (dilated * self.NEUTRAL_TENSION) // max(tension_coeff, 1)
        final = torch.clamp(final, -self.MAX_VAL, self.MAX_VAL)
        
        return final.to(torch.float32) / float(self.SCALE)
