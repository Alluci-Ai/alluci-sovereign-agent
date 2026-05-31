
from ..models import TelemetryData
from typing import Dict, Any, Optional
from .affect_kernel import AffectKernel, AffectiveState
from .btm_mapper import BTMMapper

class AffectiveEngine:
    """
    Monitors user's biological state and adjusts agent autonomy levels
    via the Flow Assistance Framework.
    """
    def __init__(self):
        self.kernel = AffectKernel()
        self.btm = BTMMapper()
        self._affective_state = AffectiveState()
        self._deadline_override_turns = 0
        self._deadline_override_tension = 1024.0
        
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
        # Update AffectiveState using BTMMapper (PPN-002)
        self._affective_state = self.btm.map(data)
        
        # Backward compatibility for current_state
        stress = (self._affective_state.tension / 1024.0) * 100.0
        self.current_state["stress_score"] = stress
        self.current_state["physical_vitality"] = max(0.0, 1.0 - (stress / 100.0))
        
        # Map valence/arousal for legacy modes
        v = self._affective_state.valence / 1024.0
        
        # Apply cognitive biases (e.g. sleep deprivation)
        if data.sleep_efficiency and data.sleep_efficiency < 0.8:
            # Low sleep biases valence negatively
            sleep_bias = data.sleep_efficiency - 0.8 # e.g. 0.4 - 0.8 = -0.4
            v = max(0.0, min(1.0, v + sleep_bias))

        if v > 0.7:
            self.current_state["affective_valence"] = "expansive"
        elif v < 0.3:
            self.current_state["affective_valence"] = "contracted"
        else:
            self.current_state["affective_valence"] = "neutral"

        # 3. Cognitive State (Mental Load)
        if data.focus is not None:
            recovery_boost = 0.1 if (data.sleep_efficiency and data.sleep_efficiency > 0.9) else 0.0
            adjusted_focus = data.focus + recovery_boost
            
            if adjusted_focus > 0.8:
                self.current_state["mental_load"] = "deep_work"
            elif adjusted_focus < 0.3:
                self.current_state["mental_load"] = "fatigued"
            else:
                self.current_state["mental_load"] = "nominal"

        return self._evaluate_flow_state()

    def get_affective_state(self) -> AffectiveState:
        """
        Returns the current affective state, applying any active overrides.
        Source: PPN §DDS — get_affective_state()
        """
        state = self._affective_state
        if self._deadline_override_turns > 0:
            # Inject deadline contraction (PPN-011)
            state = AffectiveState(
                valence=state.valence,
                arousal=state.arousal,
                tension=max(state.tension, self._deadline_override_tension)
            )
            self._deadline_override_turns -= 1
        return state

    def inject_deadline_contraction(self, turns: int = 3):
        """Trigger κ contraction on turn deadline breach."""
        self._deadline_override_turns = turns
        self._deadline_override_tension = 1024.0

    def _evaluate_flow_state(self) -> Dict[str, Any]:
        """Evaluates combined markers to determine the overarching Flow mode."""
        stress = self.current_state["stress_score"]
        load = self.current_state["mental_load"]

        # Determine ACE_STATE_X (Biometric Profile)
        if stress > 75 or load == "fatigued":
            self.current_state["ace_state"] = "<ACE_STATE_5>" if stress > 85 else "<ACE_STATE_4>"
            self.current_state["is_throttled"] = True
            self.current_state["flow_mode"] = "RECOVERY_MODE"
            return {"mode": "RECOVERY_MODE", "action": "SILENCE_NON_URGENT", "reason": "High Strain Detected", "ace_state": self.current_state["ace_state"]}
        
        if load == "deep_work" and stress < 60:
            self.current_state["ace_state"] = "<ACE_STATE_3>" if stress > 40 else "<ACE_STATE_2>"
            self.current_state["is_throttled"] = True
            self.current_state["flow_mode"] = "DEEP_WORK"
            return {"mode": "DEEP_WORK", "action": "SILENCE_ALL_BUT_EMERGENCY", "reason": "Deep Cognitive Focus", "ace_state": self.current_state["ace_state"]}
        
        if self.current_state["physical_vitality"] > 0.8 and load == "nominal":
            self.current_state["ace_state"] = "<ACE_STATE_1>"
            self.current_state["is_throttled"] = False
            self.current_state["flow_mode"] = "PEAK_PERFORMANCE"
            return {"mode": "PEAK_PERFORMANCE", "action": "SUGGEST_HIGH_LOGIC_EPICS", "reason": "High Vitality", "ace_state": self.current_state["ace_state"]}

        self.current_state["ace_state"] = "<ACE_STATE_0>"
        self.current_state["is_throttled"] = False
        self.current_state["flow_mode"] = "STANDARD"
        return {"mode": "STANDARD", "action": "NORMAL_ROUTING", "reason": "Nominal State", "ace_state": self.current_state["ace_state"]}

    def should_throttle(self) -> bool:
        """Determines if the system should suppress standard bridge notifications."""
        return self.current_state["is_throttled"]
