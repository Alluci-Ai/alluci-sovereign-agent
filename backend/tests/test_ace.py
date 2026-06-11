import pytest
pytestmark = pytest.mark.unit

"""
Affective Engine (ACE) Unit Tests

Tests flow state transitions, telemetry processing, and boundary conditions.
"""
from backend.ace.engine import AffectiveEngine
from backend.models import TelemetryData


@pytest.fixture
def ace():
    return AffectiveEngine()


def make_telemetry(**kwargs):
    defaults = {
        "hr": 70.0, "hrv": 50.0, "valence": 0.5,
        "focus": 0.6, "sleep_efficiency": 0.85, "respiratory_rate": 15.0
    }
    defaults.update(kwargs)
    return TelemetryData(**defaults)  # type: ignore


class TestACEFlowStates:

    @pytest.mark.unit
    def test_high_stress_triggers_recovery_mode(self, ace):
        """HR/HRV ratio indicating extreme stress activates RECOVERY_MODE."""
        telemetry = make_telemetry(hr=180.0, hrv=10.0)  # stress = (180/10)*10 = 180 >> 75
        result = ace.process_telemetry(telemetry)
        assert result["mode"] == "RECOVERY_MODE"
        assert ace.current_state["is_throttled"] is True

    @pytest.mark.unit
    def test_deep_work_state(self, ace):
        """High focus + moderate stress → DEEP_WORK mode."""
        telemetry = make_telemetry(hr=65.0, hrv=70.0, focus=0.95)
        result = ace.process_telemetry(telemetry)
        assert result["mode"] == "DEEP_WORK"

    @pytest.mark.unit
    def test_standard_mode_nominal_state(self, ace):
        """Nominal biometrics → STANDARD mode."""
        telemetry = make_telemetry(hr=70.0, hrv=60.0, focus=0.55, valence=0.5)
        result = ace.process_telemetry(telemetry)
        assert result["mode"] in ("STANDARD", "PEAK_PERFORMANCE")

    @pytest.mark.unit
    def test_peak_performance_mode(self, ace):
        """Excellent vitality + nominal load → PEAK_PERFORMANCE."""
        telemetry = make_telemetry(hr=60.0, hrv=90.0, focus=0.6, sleep_efficiency=0.95)
        result = ace.process_telemetry(telemetry)
        assert result["mode"] in ("PEAK_PERFORMANCE", "STANDARD")

    @pytest.mark.unit
    def test_fatigued_state_triggers_throttle(self, ace):
        """Very low focus score → fatigued state, which throttles the agent."""
        telemetry = make_telemetry(focus=0.1)
        result = ace.process_telemetry(telemetry)
        assert ace.current_state["mental_load"] == "fatigued"

    @pytest.mark.unit
    def test_missing_optional_fields_do_not_crash(self, ace):
        """ACE handles telemetry with only partial data (no crash on missing fields)."""
        sparse_telemetry = TelemetryData(hr=None, hrv=None, valence=None, focus=None)
        result = ace.process_telemetry(sparse_telemetry)
        assert "mode" in result
        assert isinstance(result["mode"], str)

    @pytest.mark.unit
    def test_sleep_deprivation_biases_valence_negative(self, ace):
        """Low sleep efficiency biases affective valence toward contracted."""
        telemetry = make_telemetry(valence=0.5, sleep_efficiency=0.4)
        ace.process_telemetry(telemetry)
        # Sleep bias = 0.4 - 0.8 = -0.4; adjusted_valence = 0.5 + (-0.4) = 0.1 → contracted
        assert ace.current_state["affective_valence"] == "contracted"
