
import numpy as np
import logging
from .logging_config import get_logger
from datetime import datetime, timezone
from typing import List, Any, Tuple
from pydantic import BaseModel, Field

logger = get_logger("HarmonicEnhancer")

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

        # Normalize
        arr = np.array(series)
        arr = (arr - np.mean(arr)) / (np.std(arr) + 1e-6)
        
        # Autocorrelation
        result = np.correlate(arr, arr, mode='full')
        result = result[result.size // 2:] # Keep positive lags
        
        # Find peaks (skipping lag 0)
        peaks = []
        for i in range(1, len(result) - 1):
            if result[i-1] < result[i] > result[i+1]:
                peaks.append((i, result[i]))
        
        if not peaks:
            return LatticeDescriptor(periodicity_strength=0.0, cycle_length=0, is_looping=False)
            
        # Sort by correlation strength
        peaks.sort(key=lambda x: x[1], reverse=True)
        best_lag, strength = peaks[0]
        
        # Normalize strength (0-1 approx)
        norm_strength = min(1.0, strength / len(series))
        
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
        # Hash task to integer
        h = sum(ord(c) for c in task_identifier)
        is_qp = self.is_quasi_prime(h)
        return 1.0 if is_qp else 0.5

class TopologyMapper:
    """
    Maps Consciousness-Field Topology.
    Clusters signals into attractor basins.
    """
    def __init__(self):
        self.history: List[Tuple[float, float]] = [] # (valence, arousal)
        self.MAX_HISTORY = 50

    def update(self, signal: AttentionSignal) -> Tuple[Tuple[float, float], bool]:
        self.history.append((signal.valence, signal.arousal))
        if len(self.history) > self.MAX_HISTORY:
            self.history.pop(0)
            
        # Compute Centroid
        if not self.history:
            return (0.5, 0.5), False
            
        arr = np.array(self.history)
        centroid = np.mean(arr, axis=0)
        c_val, c_ar = centroid[0], centroid[1]
        
        # Detect Stress Basin (High Arousal, Low Valence)
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

        # 1. Update Lattice (using Focus series)
        focus_series = [s.focus for s in self.signal_buffer]
        lattice_desc = self.lattice.analyze(focus_series)
        
        # 2. Update Topology
        centroid, stress = self.topology.update(signal)
        
        # 3. Check Ikigai Alignment (Drop in Valence)
        ikigai_deficit = signal.valence < 0.3
        
        self.current_state = HarmonicState(
            current_lattice=lattice_desc,
            centroid=centroid,
            in_stress_basin=stress,
            ikigai_deficit=ikigai_deficit
        )
        
        # Trigger Protocols
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
        
        # Get current state factors
        V_norm = self.signal_buffer[-1].valence if self.signal_buffer else 0.5
        L = self.current_state.current_lattice.periodicity_strength
        focus_penalty = self.signal_buffer[-1].focus if self.signal_buffer else 1.0
        
        for task in tasks:
            # Handle both object and dict access
            t_id = getattr(task, 'id', str(task))
            t_desc = getattr(task, 'args', {}).get('description', '')
            
            # W: Prime Weight
            W = self.primes.compute_weight(t_id + t_desc)
            
            # Combined Score Formula
            # CombinedScore = 0.4(V_norm) + 0.3(1 - L) + 0.3(W)
            combined_score = (0.4 * V_norm) + (0.3 * (1.0 - L)) + (0.3 * W)
            
            # Novelty (Simulated by Prime check again for now, or random)
            novelty = 1.0 if W > 0.8 else 0.2
            
            # Base Impact (T-10): Dynamic weighting based on relevance and tension
            # Semantic relevance proxy: description length and keyword matching
            desc_len = len(t_desc)
            semantic_relevance = min(1.0, desc_len / 300.0) 
            base_impact = (semantic_relevance * 0.7) + (psi * 0.3)
            
            # P = clamp(...) * FocusPenalty
            raw_p = (base_impact * 0.5) + (combined_score * 0.3) + (novelty * 0.2)
            p = max(0.0, min(1.0, raw_p)) * (0.5 + (0.5 * focus_penalty)) # Soften penalty
            
            # Ikigai Boost
            if self.current_state.ikigai_deficit and W > 0.8:
                p += 0.2 # Boost prime tasks (Love/Connection mapping)
            
            # Assign score (dynamically add attribute if possible)
            try:
                setattr(task, 'priority_score', p)
            except Exception:
                pass # If dict or immutable
                
            ranked.append((p, task))
            
        # Sort descending
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in ranked]
