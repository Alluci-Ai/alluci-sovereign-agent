import ctypes
import os
import platform
import logging
import numpy as np
from collections import deque
from ..logging_config import get_logger

logger = get_logger("EntropyMonitor")

_native_lib = None
try:
    _dir = os.path.dirname(os.path.abspath(__file__))
    _build_dir = os.path.join(_dir, "build")
    _system = platform.system()
    _candidates = {
        "Darwin": os.path.join(_build_dir, "libentropy_kernel.dylib"),
        "Linux":  os.path.join(_build_dir, "libentropy_kernel.so"),
        "Windows": os.path.join(_build_dir, "entropy_kernel.dll"),
    }
    _lib_path = _candidates.get(_system)
    
    if _lib_path and os.path.isfile(_lib_path):
        _native_lib = ctypes.CDLL(_lib_path)
        
        _native_lib.entropy_new.argtypes = [ctypes.c_int, ctypes.c_float]
        _native_lib.entropy_new.restype = ctypes.c_void_p
        
        _native_lib.entropy_free.argtypes = [ctypes.c_void_p]
        _native_lib.entropy_free.restype = None
        
        _native_lib.entropy_push.argtypes = [ctypes.c_void_p, ctypes.c_float]
        _native_lib.entropy_push.restype = ctypes.c_int
        
        _native_lib.entropy_get_state.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_float)
        ]
        _native_lib.entropy_get_state.restype = None
        
        logger.info("[EntropyMonitor] Native C++ Kernel Loaded.")
    else:
        logger.info("[EntropyMonitor] Native kernel not found. Using Python fallback.")
except Exception as e:
    logger.warning(f"[EntropyMonitor] Failed to initialize native instance: {e}. Falling back to Python.")
    _native_lib = None


class EntropySpikeDetector:
    """
    Entropy Spike Detector.
    Source: PPN §Monitoring — entropy_sensor.cpp::detect_spike()

    Monitors graph entropy (H_G) over time. Sudden spikes indicate 
    topological ruptures or "hallucination cascades".
    """
    def __init__(self, window_size: int = 15):
        self._window_size = window_size
        self.SPIKE_THRESHOLD = 2.0  # Z-score threshold for alert
        self._handle = None
        
        # Python fallback fields
        self._py_history = deque(maxlen=window_size)
        
        if _native_lib:
            try:
                self._handle = _native_lib.entropy_new(window_size, self.SPIKE_THRESHOLD)
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
                    _native_lib.entropy_free(self._handle)
                except Exception:
                    pass
            self._handle = None

    @property
    def history(self):
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            count = ctypes.c_int()
            threshold = ctypes.c_float()
            arr = (ctypes.c_float * self._window_size)()
            _native_lib.entropy_get_state(self._handle, arr, ctypes.byref(count), ctypes.byref(threshold))
            return deque(arr[:count.value], maxlen=self._window_size)
        return self._py_history

    @history.setter
    def history(self, value):
        if getattr(self, '_handle', None) is not None:
            self.cleanup()
        self._py_history = deque(value, maxlen=self._window_size)

    def push(self, h_norm: float) -> bool:
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            try:
                count = ctypes.c_int()
                threshold = ctypes.c_float()
                arr = (ctypes.c_float * self._window_size)()
                _native_lib.entropy_get_state(self._handle, arr, ctypes.byref(count), ctypes.byref(threshold))
                
                if count.value >= 5:
                    hist_slice = arr[:count.value]
                    mean = np.mean(hist_slice)
                    std = max(float(np.std(hist_slice)), 0.1)
                    z_score = abs(h_norm - mean) / std
                    if z_score > self.SPIKE_THRESHOLD:
                        logger.warning(f"[MONITOR] Entropy Spike Detected! Z={z_score:.2f}")

                res = _native_lib.entropy_push(self._handle, float(h_norm))
                return bool(res)
            except Exception as e:
                logger.warning(f"Error in native push call: {e}. Falling back to Python.")

        # Fallback to pure-Python implementation
        if len(self._py_history) < 5:
            self._py_history.append(h_norm)
            return False

        mean = np.mean(self._py_history)
        std = max(float(np.std(self._py_history)), 0.1)
        z_score = abs(h_norm - mean) / std

        self._py_history.append(h_norm)

        if z_score > self.SPIKE_THRESHOLD:
            logger.warning(f"[MONITOR] Entropy Spike Detected! Z={z_score:.2f}")
            return True
        return False
