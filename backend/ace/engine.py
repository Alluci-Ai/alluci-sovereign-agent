
from ..models import TelemetryData
from typing import Dict, Any

class AffectiveEngine:
    """
    Monitors user's biological state and adjusts agent autonomy levels
    via the Flow Assistance Framework.
    """
    def __init__(self):
        self.current_state = {
            "physical_vitality": 1.0,         # Based on HR/HRV
            "affective_valence": "neutral",   # Emotional state
            "mental_load": "nominal",         # Cognitive state
            "stress_score": 0.0,
            "flow_mode": "STANDARD",          # Flow Assistance state
            "is_throttled": False
        }

    def process_telemetry(self, data: TelemetryData) -> Dict[str, Any]:
        """Ingests raw telemetry and outputs an abstracted Flow state."""
        
        # 1. Physical Vitality (Stress)
        if data.hr and data.hrv:
            # Simple heuristic: high HR and low HRV indicates stress
            stress = (data.hr / data.hrv) * 10 
            self.current_state["stress_score"] = stress
            self.current_state["physical_vitality"] = max(0.0, 1.0 - (stress / 100))
        
        # 2. Affective Valence (Emotion - if provided via skin conductance/voice)
        if data.valence is not None:
            if data.valence > 0.7:
                self.current_state["affective_valence"] = "expansive"
            elif data.valence < 0.3:
                self.current_state["affective_valence"] = "contracted"
            else:
                self.current_state["affective_valence"] = "neutral"

        # 3. Cognitive State (Mental Load)
        if data.focus is not None:
            if data.focus > 0.8:
                self.current_state["mental_load"] = "deep_work"
            elif data.focus < 0.3:
                self.current_state["mental_load"] = "fatigued"
            else:
                self.current_state["mental_load"] = "nominal"

        # 4. Flow Assistance Framework (Determine active state)
        return self._evaluate_flow_state()

    def _evaluate_flow_state(self) -> Dict[str, Any]:
        """Evaluates combined markers to determine the overarching Flow mode."""
        stress = self.current_state["stress_score"]
        load = self.current_state["mental_load"]

        # Burnout Prevention
        if stress > 75 or load == "fatigued":
            self.current_state["is_throttled"] = True
            self.current_state["flow_mode"] = "RECOVERY_MODE"
            return {"mode": "RECOVERY_MODE", "action": "SILENCE_NON_URGENT", "reason": "High Strain Detected"}
        
        # Deep Work Isolation
        if load == "deep_work" and stress < 60:
            self.current_state["is_throttled"] = True
            self.current_state["flow_mode"] = "DEEP_WORK"
            return {"mode": "DEEP_WORK", "action": "SILENCE_ALL_BUT_EMERGENCY", "reason": "Deep Cognitive Focus"}
        
        # Peak Performance
        if self.current_state["physical_vitality"] > 0.8 and load == "nominal":
            self.current_state["is_throttled"] = False
            self.current_state["flow_mode"] = "PEAK_PERFORMANCE"
            return {"mode": "PEAK_PERFORMANCE", "action": "SUGGEST_HIGH_LOGIC_EPICS", "reason": "High Vitality"}

        # Standard Operation
        self.current_state["is_throttled"] = False
        self.current_state["flow_mode"] = "STANDARD"
        return {"mode": "STANDARD", "action": "NORMAL_ROUTING", "reason": "Nominal State"}

    def should_throttle(self) -> bool:
        """Determines if the system should suppress standard bridge notifications."""
        return self.current_state["is_throttled"]
