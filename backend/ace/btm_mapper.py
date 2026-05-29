import ctypes
import os
import platform
import logging
from collections import deque
from ..models import TelemetryData
from .affect_kernel import AffectiveState

logger = logging.getLogger("BTMMapper")

_native_lib = None
try:
    _dir = os.path.dirname(os.path.abspath(__file__))
    _build_dir = os.path.join(_dir, "build")
    _system = platform.system()
    _candidates = {
        "Darwin": os.path.join(_build_dir, "libbtm_kernel.dylib"),
        "Linux":  os.path.join(_build_dir, "libbtm_kernel.so"),
        "Windows": os.path.join(_build_dir, "btm_kernel.dll"),
    }
    _lib_path = _candidates.get(_system)
    
    if _lib_path and os.path.isfile(_lib_path):
        _native_lib = ctypes.CDLL(_lib_path)
        
        _native_lib.btm_new.argtypes = [ctypes.c_int]
        _native_lib.btm_new.restype = ctypes.c_void_p
        
        _native_lib.btm_free.argtypes = [ctypes.c_void_p]
        _native_lib.btm_free.restype = None
        
        _native_lib.btm_map.argtypes = [
            ctypes.c_void_p,
            ctypes.c_float, ctypes.c_int,
            ctypes.c_float, ctypes.c_int,
            ctypes.c_float, ctypes.c_int,
            ctypes.c_float, ctypes.c_int,
            ctypes.c_float, ctypes.c_int,
            ctypes.c_float, ctypes.c_int,
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float)
        ]
        _native_lib.btm_map.restype = None
        
        _native_lib.btm_compute_psi.argtypes = [ctypes.c_int32, ctypes.c_int32]
        _native_lib.btm_compute_psi.restype = ctypes.c_int32
        
        _native_lib.btm_get_state.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_float)
        ]
        _native_lib.btm_get_state.restype = None
        
        logger.info("[BTMMapper] Native C++ Kernel Loaded.")
    else:
        logger.info("[BTMMapper] Native kernel not found. Using Python fallback.")
except Exception as e:
    logger.warning(f"[BTMMapper] Failed to initialize native instance: {e}. Falling back to Python.")
    _native_lib = None


class BTMMapper:
    """
    Biometric Tension Mapper.
    Source: PPN §BTM — btm_interface.hpp::update_from_sensors()

    Maps raw telemetry to AffectiveState using three paper-defined transforms:
      A. Arousal  ← inverse HRV stability + GSR gradient
      B. Tension  ← torsion (cognitive/stress load proxy)
      C. Valence  ← symmetry (emotional balance proxy)
    """

    def __init__(self, hrv_window: int = 10):
        self._hrv_window = hrv_window
        self._handle = None
        
        # Python fallback fields
        self._py_hrv_history = deque(maxlen=hrv_window)
        self._py_gsr_history = deque(maxlen=hrv_window)
        self._py_max_hrv_observed = 100.0
        
        if _native_lib:
            try:
                self._handle = _native_lib.btm_new(hrv_window)
            except Exception as e:
                logger.warning(f"Failed to instantiate native instance: {e}")
                self._handle = None

    def __del__(self):
        self.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        if getattr(self, '_handle', None) is not None:
            if _native_lib is not None:
                try:
                    _native_lib.btm_free(self._handle)
                except Exception:
                    pass
            self._handle = None

    @property
    def _hrv_history(self):
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            count = ctypes.c_int()
            gsr_count = ctypes.c_int()
            max_hrv = ctypes.c_float()
            hrv_arr = (ctypes.c_float * self._hrv_window)()
            gsr_arr = (ctypes.c_float * self._hrv_window)()
            _native_lib.btm_get_state(self._handle, hrv_arr, gsr_arr, ctypes.byref(count), ctypes.byref(gsr_count), ctypes.byref(max_hrv))
            return deque(hrv_arr[:count.value], maxlen=self._hrv_window)
        return self._py_hrv_history

    @property
    def _gsr_history(self):
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            count = ctypes.c_int()
            gsr_count = ctypes.c_int()
            max_hrv = ctypes.c_float()
            hrv_arr = (ctypes.c_float * self._hrv_window)()
            gsr_arr = (ctypes.c_float * self._hrv_window)()
            _native_lib.btm_get_state(self._handle, hrv_arr, gsr_arr, ctypes.byref(count), ctypes.byref(gsr_count), ctypes.byref(max_hrv))
            return deque(gsr_arr[:gsr_count.value], maxlen=self._hrv_window)
        return self._py_gsr_history

    @property
    def _max_hrv_observed(self):
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            count = ctypes.c_int()
            gsr_count = ctypes.c_int()
            max_hrv = ctypes.c_float()
            hrv_arr = (ctypes.c_float * self._hrv_window)()
            gsr_arr = (ctypes.c_float * self._hrv_window)()
            _native_lib.btm_get_state(self._handle, hrv_arr, gsr_arr, ctypes.byref(count), ctypes.byref(gsr_count), ctypes.byref(max_hrv))
            return max_hrv.value
        return self._py_max_hrv_observed

    def map(self, data: TelemetryData) -> AffectiveState:
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            hrv_val = float(data.hrv) if (data.hrv is not None and data.hrv > 0) else 0.0
            has_hrv = 1 if (data.hrv is not None and data.hrv > 0) else 0
            
            gsr_val = float(data.gsr) if data.gsr is not None else 0.0
            has_gsr = 1 if data.gsr is not None else 0
            
            stress_val = float(data.stress_score) if data.stress_score is not None else 0.0
            has_stress = 1 if data.stress_score is not None else 0
            
            hr_val = float(data.hr) if data.hr is not None else 0.0
            has_hr = 1 if data.hr is not None else 0
            
            rr_val = float(data.respiratory_rate) if data.respiratory_rate is not None else 0.0
            has_rr = 1 if data.respiratory_rate is not None else 0
            
            valence_val = float(data.valence) if data.valence is not None else 0.0
            has_val = 1 if data.valence is not None else 0
            
            out_val = ctypes.c_float()
            out_ar = ctypes.c_float()
            out_ten = ctypes.c_float()
            
            try:
                _native_lib.btm_map(
                    self._handle,
                    hrv_val, has_hrv,
                    gsr_val, has_gsr,
                    stress_val, has_stress,
                    hr_val, has_hr,
                    rr_val, has_rr,
                    valence_val, has_val,
                    ctypes.byref(out_val), ctypes.byref(out_ar), ctypes.byref(out_ten)
                )
                return AffectiveState(valence=out_val.value, arousal=out_ar.value, tension=out_ten.value)
            except Exception as e:
                logger.warning(f"Error in native map call: {e}. Falling back to Python.")

        # Fallback to pure-Python implementation
        # === A. AROUSAL: inverse HRV stability + GSR gradient ===
        arousal = 512.0
        if data.hrv and data.hrv > 0:
            self._py_hrv_history.append(float(data.hrv))
            self._py_max_hrv_observed = max(self._py_max_hrv_observed, float(data.hrv))
            hrv_stability = float(data.hrv) / self._py_max_hrv_observed
            raw_arousal = 1.0 / (hrv_stability + 0.1)
            arousal = max(0.0, min(1024.0, raw_arousal * 256.0))

        if data.gsr is not None:
            self._py_gsr_history.append(float(data.gsr))
            if len(self._py_gsr_history) >= 2:
                gsr_gradient = self._py_gsr_history[-1] - self._py_gsr_history[-2]
                gsr_arousal = max(0.0, min(1024.0, gsr_gradient * 4.0 * 256.0))
                arousal = max(0.0, min(1024.0, (arousal + gsr_arousal) / 2.0))

        # === B. TENSION: torsion mapping ===
        tension = 0.0
        if data.stress_score is not None:
            torsion = min(1.0, data.stress_score / 100.0)
            tension = min(1024.0, torsion * 1024.0)
        elif data.hr and data.hrv:
            rr = (data.respiratory_rate / 15.0) if data.respiratory_rate else 1.0
            torsion = min(1.0, (data.hr / max(data.hrv, 1)) * 10.0 * rr / 100.0)
            tension = min(1024.0, torsion * 1024.0)

        # === C. VALENCE: symmetry mapping ===
        valence = 512.0
        if data.valence is not None:
            valence = max(0.0, min(1024.0, data.valence * 1024.0))

        return AffectiveState(valence=valence, arousal=arousal, tension=tension)

    def compute_psi(self, hrv_raw: int = 0, gsr_raw: int = 0) -> int:
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            try:
                return _native_lib.btm_compute_psi(int(hrv_raw), int(gsr_raw))
            except Exception as e:
                logger.warning(f"Error in native compute_psi: {e}. Falling back to Python.")
        
        arousal = (gsr_raw << 2) if gsr_raw else 512
        valence = hrv_raw >> 1
        psi = (arousal - valence) + 512
        return max(0, min(1024, psi))

    def psi_from_state(self, state: AffectiveState) -> float:
        """Convert AffectiveState to scalar ψ ∈ [0.0, 1.0] for ALCE."""
        return state.tension / 1024.0
