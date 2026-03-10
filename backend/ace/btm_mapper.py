from collections import deque
from ..models import TelemetryData
from .affect_kernel import AffectiveState


class BTMMapper:
    """
    Biometric Tension Mapper.
    Source: PPN §BTM — btm_interface.hpp::update_from_sensors()

    Maps raw telemetry to AffectiveState using three paper-defined transforms:
      A. Arousal  ← inverse HRV stability
      B. Tension  ← torsion (cognitive/stress load proxy)
      C. Valence  ← symmetry (emotional balance proxy)
    """

    def __init__(self, hrv_window: int = 10):
        self._hrv_history: deque = deque(maxlen=hrv_window)
        self._max_hrv_observed: float = 100.0  # ms baseline

    def map(self, data: TelemetryData) -> AffectiveState:

        # === A. AROUSAL: inverse HRV stability ===
        # arousal = clamp(1 / (hrv_stability + 0.1), 0, 1024)
        arousal = 512.0  # default: neutral
        if data.hrv and data.hrv > 0:
            self._hrv_history.append(float(data.hrv))
            self._max_hrv_observed = max(self._max_hrv_observed, float(data.hrv))
            hrv_stability = float(data.hrv) / self._max_hrv_observed
            raw_arousal = 1.0 / (hrv_stability + 0.1)
            arousal = max(0.0, min(1024.0, raw_arousal * 256.0))

        # === B. TENSION: torsion mapping ===
        # tension = clamp(torsion_score × 1024, 0, 1024)
        # Alluci proxy: stress_score / 100 = torsion [0..1]
        tension = 0.0
        if data.stress_score is not None:
            torsion = min(1.0, data.stress_score / 100.0)
            tension = min(1024.0, torsion * 1024.0)
        elif data.hr and data.hrv:
            rr = (data.respiratory_rate / 15.0) if data.respiratory_rate else 1.0
            torsion = min(1.0, (data.hr / max(data.hrv, 1)) * 10.0 * rr / 100.0)
            tension = min(1024.0, torsion * 1024.0)

        # === C. VALENCE: symmetry mapping ===
        # valence = clamp(symmetry × 512, 0, 1024)
        valence = 512.0  # default: neutral
        if data.valence is not None:
            valence = max(0.0, min(1024.0, data.valence * 1024.0))

        return AffectiveState(valence=valence, arousal=arousal, tension=tension)

    def psi_from_state(self, state: AffectiveState) -> float:
        """Convert AffectiveState to scalar ψ ∈ [0.0, 1.0] for ALCE."""
        return state.tension / 1024.0
