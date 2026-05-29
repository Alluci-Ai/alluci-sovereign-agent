import ctypes
import os
import platform
import logging
import numpy as np
from datetime import datetime, timezone
from typing import List, Any, Tuple
from pydantic import BaseModel, Field
from .logging_config import get_logger

logger = get_logger("HarmonicEnhancer")

_native_lib = None
try:
    _dir = os.path.dirname(os.path.abspath(__file__))
    _build_dir = os.path.join(_dir, "ace", "build")
    _system = platform.system()
    _candidates = {
        "Darwin": os.path.join(_build_dir, "libharmonic_kernel.dylib"),
        "Linux":  os.path.join(_build_dir, "libharmonic_kernel.so"),
        "Windows": os.path.join(_build_dir, "harmonic_kernel.dll"),
    }
    _lib_path = _candidates.get(_system)
    
    if _lib_path and os.path.isfile(_lib_path):
        _native_lib = ctypes.CDLL(_lib_path)
        
        _native_lib.lattice_analyze.argtypes = [
            ctypes.POINTER(ctypes.c_float),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_int)
        ]
        _native_lib.lattice_analyze.restype = ctypes.c_int
        
        _native_lib.topology_mapper_new.argtypes = [ctypes.c_int]
        _native_lib.topology_mapper_new.restype = ctypes.c_void_p
        
        _native_lib.topology_mapper_free.argtypes = [ctypes.c_void_p]
        _native_lib.topology_mapper_free.restype = None
        
        _native_lib.topology_mapper_update.argtypes = [
            ctypes.c_void_p,
            ctypes.c_float,
            ctypes.c_float,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_int)
        ]
        _native_lib.topology_mapper_update.restype = None
        
        _native_lib.topology_mapper_get_state.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_float),
            ctypes.POINTER(ctypes.c_int)
        ]
        _native_lib.topology_mapper_get_state.restype = None
        
        logger.info("[HarmonicEnhancer] Native C++ Kernel Loaded.")
    else:
        logger.info("[HarmonicEnhancer] Native kernel not found. Using Python fallback.")
except Exception as e:
    logger.warning(f"[HarmonicEnhancer] Failed to initialize native instance: {e}. Falling back to Python.")
    _native_lib = None


# --- Data Models ---

class AttentionSignal(BaseModel):
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    valence: float = Field(..., ge=0.0, le=1.0)
    arousal: float = Field(..., ge=0.0, le=1.0)
    focus: float = Field(..., ge=0.0, le=1.0)

class LatticeDescriptor(BaseModel):
    periodicity_strength: float
    cycle_length: int
    is_looping: bool

class HarmonicState(BaseModel):
    current_lattice: LatticeDescriptor
    centroid: Tuple[float, float]
    in_stress_basin: bool
    ikigai_deficit: bool


# --- Core Components ---

class LatticeAnalyzer:
    """
    Analyzes Reciprocal Lattice Dynamics using Naive Autocorrelation.
    Identifies repeating cycles in affective signals.
    """
    def analyze(self, series: List[float]) -> LatticeDescriptor:
        if len(series) < 5:
            return LatticeDescriptor(periodicity_strength=0.0, cycle_length=0, is_looping=False)

        if _native_lib:
            try:
                c_arr = (ctypes.c_float * len(series))(*series)
                strength = ctypes.c_float()
                cycle_len = ctypes.c_int()
                res = _native_lib.lattice_analyze(c_arr, int(len(series)), ctypes.byref(strength), ctypes.byref(cycle_len))
                if res:
                    return LatticeDescriptor(
                        periodicity_strength=strength.value,
                        cycle_length=cycle_len.value,
                        is_looping=strength.value > 0.7 and cycle_len.value < 3
                    )
                else:
                    return LatticeDescriptor(periodicity_strength=0.0, cycle_length=0, is_looping=False)
            except Exception as e:
                logger.warning(f"Error in native lattice analyze: {e}. Falling back to Python.")

        # Fallback to pure-Python implementation
        arr = np.array(series)
        arr = (arr - np.mean(arr)) / (np.std(arr) + 1e-6)
        result = np.correlate(arr, arr, mode='full')
        result = result[result.size // 2:]
        
        peaks = []
        for i in range(1, len(result) - 1):
            if result[i-1] < result[i] > result[i+1]:
                peaks.append((i, result[i]))
        
        if not peaks:
            return LatticeDescriptor(periodicity_strength=0.0, cycle_length=0, is_looping=False)
            
        peaks.sort(key=lambda x: x[1], reverse=True)
        best_lag, strength_val = peaks[0]
        norm_strength = min(1.0, strength_val / len(series))
        
        return LatticeDescriptor(
            periodicity_strength=norm_strength,
            cycle_length=best_lag,
            is_looping=norm_strength > 0.7 and best_lag < 3
        )


class PrimeMapper:
    """
    Determines Structural Stability using Quasi-Prime filtering.
    """
    SMALL_PRIMES = {2, 3, 5, 7, 11}

    def is_quasi_prime(self, n: int) -> bool:
        if n < 2:
            return False
        for p in self.SMALL_PRIMES:
            if n % p == 0:
                return False
        return True

    def compute_weight(self, task_identifier: str) -> float:
        h = sum(ord(c) for c in task_identifier)
        is_qp = self.is_quasi_prime(h)
        return 1.0 if is_qp else 0.5


class TopologyMapper:
    """
    Maps Consciousness-Field Topology.
    Clusters signals into attractor basins.
    """
    def __init__(self):
        self.MAX_HISTORY = 50
        self._handle = None
        
        # Python fallback fields
        self._py_history: List[Tuple[float, float]] = []
        
        if _native_lib:
            try:
                self._handle = _native_lib.topology_mapper_new(self.MAX_HISTORY)
            except Exception as e:
                logger.warning(f"Failed to instantiate native topology mapper: {e}")
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
                    _native_lib.topology_mapper_free(self._handle)
                except Exception:
                    pass
            self._handle = None

    @property
    def history(self):
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            count = ctypes.c_int()
            val_arr = (ctypes.c_float * self.MAX_HISTORY)()
            ar_arr = (ctypes.c_float * self.MAX_HISTORY)()
            try:
                _native_lib.topology_mapper_get_state(self._handle, val_arr, ar_arr, ctypes.byref(count))
                return [(val_arr[i], ar_arr[i]) for i in range(count.value)]
            except Exception:
                pass
        return self._py_history


    @history.setter
    def history(self, value):
        if getattr(self, '_handle', None) is not None:
            self.cleanup()
        self._py_history = list(value)

    def update(self, signal: AttentionSignal) -> Tuple[Tuple[float, float], bool]:
        if getattr(self, '_handle', None) is not None and _native_lib is not None:
            try:
                c_val = ctypes.c_float()
                c_ar = ctypes.c_float()
                stress = ctypes.c_int()
                _native_lib.topology_mapper_update(
                    self._handle,
                    signal.valence,
                    signal.arousal,
                    ctypes.byref(c_val),
                    ctypes.byref(c_ar),
                    ctypes.byref(stress)
                )
                return (c_val.value, c_ar.value), bool(stress.value)
            except Exception as e:
                logger.warning(f"Error in native topology update: {e}. Falling back to Python.")

        # Fallback to pure-Python implementation
        self._py_history.append((signal.valence, signal.arousal))
        if len(self._py_history) > self.MAX_HISTORY:
            self._py_history.pop(0)
            
        if not self._py_history:
            return (0.5, 0.5), False
            
        arr = np.array(self._py_history)
        centroid = np.mean(arr, axis=0)
        c_val, c_ar = centroid[0], centroid[1]
        in_stress_basin = (c_ar > 0.7) and (c_val < 0.3)
        return (c_val, c_ar), in_stress_basin


# --- Main Module ---

class HarmonicAssistant:
    def __init__(self):
        self.lattice = LatticeAnalyzer()
        self.primes = PrimeMapper()
        self.topology = TopologyMapper()
        
        self.signal_buffer: List[AttentionSignal] = []
        self.BUFFER_SIZE = 20
        self.current_state = HarmonicState(
            current_lattice=LatticeDescriptor(periodicity_strength=0, cycle_length=0, is_looping=False),
            centroid=(0.5, 0.5),
            in_stress_basin=False,
            ikigai_deficit=False
        )

    async def tick(self, signal: AttentionSignal):
        """
        Ingest signal loop. Updates internal models.
        """
        self.signal_buffer.append(signal)
        if len(self.signal_buffer) > self.BUFFER_SIZE:
            self.signal_buffer.pop(0)

        focus_series = [s.focus for s in self.signal_buffer]
        lattice_desc = self.lattice.analyze(focus_series)
        
        centroid, stress = self.topology.update(signal)
        
        ikigai_deficit = signal.valence < 0.3
        
        self.current_state = HarmonicState(
            current_lattice=lattice_desc,
            centroid=centroid,
            in_stress_basin=stress,
            ikigai_deficit=ikigai_deficit
        )
        
        if lattice_desc.is_looping:
            logger.warning("PROTOCOL: Interrupt-Loop Triggered (Cycle < 3, Strength > 0.7)")
        
        if stress:
            logger.warning("PROTOCOL: Topological Shift Triggered (Stuck in Stress Basin)")
            
        if ikigai_deficit:
            logger.info("PROTOCOL: Ikigai Alignment Triggered (Mapping Joy -> Love)")

    def rank_actions(self, tasks: List[Any], psi: float = 0.5) -> List[Any]:
        """
        Enriches and sorts tasks based on Harmonic Priority Score.
        Tasks are expected to be DAGTask objects or dicts.
        """
        ranked = []
        
        V_norm = self.signal_buffer[-1].valence if self.signal_buffer else 0.5
        L = self.current_state.current_lattice.periodicity_strength
        focus_penalty = self.signal_buffer[-1].focus if self.signal_buffer else 1.0
        
        for task in tasks:
            t_id = getattr(task, 'id', str(task))
            t_desc = getattr(task, 'args', {}).get('description', '')
            
            W = self.primes.compute_weight(t_id + t_desc)
            
            combined_score = (0.4 * V_norm) + (0.3 * (1.0 - L)) + (0.3 * W)
            
            import hashlib
            h_obj = hashlib.md5((t_id + str(len(t_desc))).encode('utf-8'))
            structural_novelty = int(h_obj.hexdigest()[:4], 16) / 65535.0
            
            desc_len = len(t_desc)
            semantic_relevance = min(1.0, desc_len / 300.0) 
            base_impact = (semantic_relevance * 0.7) + (psi * 0.3)
            
            raw_p = (base_impact * 0.5) + (combined_score * 0.3) + (structural_novelty * 0.2)
            p = max(0.0, min(1.0, raw_p)) * (0.5 + (0.5 * focus_penalty))
            
            if self.current_state.ikigai_deficit and W > 0.8:
                p += 0.2
            
            try:
                setattr(task, 'priority_score', p)
            except Exception:
                pass
                
            ranked.append((p, task))
            
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in ranked]
