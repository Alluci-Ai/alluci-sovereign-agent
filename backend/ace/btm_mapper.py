from collections import deque
from ..models import TelemetryData
from .affect_kernel import AffectiveState


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
        self._hrv_history: deque = deque(maxlen=hrv_window)
        self._gsr_history: deque = deque(maxlen=hrv_window)
        self._max_hrv_observed: float = 100.0  # ms baseline

    def map(self, data: TelemetryData) -> AffectiveState:

        # === A. AROUSAL: inverse HRV stability + GSR gradient ===
        # arousal = clamp(1 / (hrv_stability + 0.1), 0, 1024)
        arousal = 512.0  # default: neutral
        if data.hrv and data.hrv > 0:
            self._hrv_history.append(float(data.hrv))
            self._max_hrv_observed = max(self._max_hrv_observed, float(data.hrv))
            hrv_stability = float(data.hrv) / self._max_hrv_observed
            raw_arousal = 1.0 / (hrv_stability + 0.1)
            arousal = max(0.0, min(1024.0, raw_arousal * 256.0))

        # GSR gradient contribution (PPN §BTM — gsr_to_arousal)
        # Apple Watch often provides sparse or null GSR data. Gracefully decay or ignore if missing.
        if data.gsr is not None:
            self._gsr_history.append(float(data.gsr))
            if len(self._gsr_history) >= 2:
                gsr_gradient = self._gsr_history[-1] - self._gsr_history[-2]
                # Bit-shift scaling: gsr_raw << 2 = gsr_raw * 4
                gsr_arousal = max(0.0, min(1024.0, gsr_gradient * 4.0 * 256.0))
                # Blend HRV-arousal with GSR-arousal (weighted average)
                arousal = max(0.0, min(1024.0, (arousal + gsr_arousal) / 2.0))
        # If no GSR is present, we rely entirely on the HRV stability computed above.

        # === B. TENSION: torsion mapping ===
        # tension = clamp(torsion_score × 1024, 0, 1024)
        # Alluci calculation: stress_score / 100 = torsion [0..1]
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

    def compute_psi(self, hrv_raw: int = 0, gsr_raw: int = 0) -> int:
        """
        Integer-shift ψ computation (edge-compatible, no floats).
        Source: PPN §Affect — compute_psi()
        Handles optional GSR data by relying primarily on HRV when GSR is 0.

        Returns ψ ∈ [0, 1024] representing affective tension.
        """
        # Integer-based scaling (×1024)
        arousal = (gsr_raw << 2) if gsr_raw else 512  # neutral arousal if no GSR
        valence = hrv_raw >> 1   # hrv_raw / 2
        # ψ is the normalized affective tension [0, 1024]
        psi = (arousal - valence) + 512
        return max(0, min(1024, psi))

    def psi_from_state(self, state: AffectiveState) -> float:
        """Convert AffectiveState to scalar ψ ∈ [0.0, 1.0] for ALCE."""
        return state.tension / 1024.0
