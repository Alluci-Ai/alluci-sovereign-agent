import pytest
pytestmark = pytest.mark.unit

from backend.ace.engine import AffectiveEngine
from backend.models import TelemetryData
from backend.ace.affect_kernel import AffectiveState

def test_initial_state():
    engine = AffectiveEngine()
    assert engine.current_state["flow_mode"] == "STANDARD"
    assert engine.current_state["is_throttled"] is False
    assert engine.current_state["physical_vitality"] == 1.0

def test_high_stress_triggers_recovery_mode():
    engine = AffectiveEngine()
    
    # Simulate high HR, low HRV (Stress)
    data = TelemetryData(
        hr=110,
        hrv=20,
        respiratory_rate=22
    )
    
    result = engine.process_telemetry(data)
    
    # Tension should be high
    state = engine.get_affective_state()
    assert state.tension > 500
    
    # Should trigger recovery mode due to stress score > 75
    assert engine.current_state["flow_mode"] == "RECOVERY_MODE"
    assert engine.current_state["is_throttled"] is True
    assert engine.current_state["ace_state"] in ["<ACE_STATE_4>", "<ACE_STATE_5>"]

def test_deep_work_mode():
    engine = AffectiveEngine()
    
    # Simulate normal HR, moderate focus
    data = TelemetryData(
        hr=65,
        hrv=60,
        respiratory_rate=14,
        focus=0.9
    )
    
    result = engine.process_telemetry(data)
    
    # Should trigger deep work mode
    assert engine.current_state["flow_mode"] == "DEEP_WORK"
    assert engine.current_state["is_throttled"] is True
    assert engine.current_state["ace_state"] in ["<ACE_STATE_2>", "<ACE_STATE_3>"]

def test_peak_performance_mode():
    engine = AffectiveEngine()
    
    # Simulate excellent HR/HRV, nominal focus
    data = TelemetryData(
        hr=60,
        hrv=80,
        respiratory_rate=12,
        focus=0.5
    )
    
    result = engine.process_telemetry(data)
    
    assert engine.current_state["flow_mode"] == "PEAK_PERFORMANCE"
    assert engine.current_state["is_throttled"] is False
    assert engine.current_state["ace_state"] == "<ACE_STATE_1>"
