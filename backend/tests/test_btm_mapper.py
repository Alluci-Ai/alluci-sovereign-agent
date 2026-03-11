from backend.ace.btm_mapper import BTMMapper
from backend.ace.affect_kernel import AffectiveState
from backend.models import TelemetryData

def test_btm_mapper_basic():
    mapper = BTMMapper()
    data = TelemetryData(hr=72, hrv=55, stress_score=30.0, valence=0.6)
    state = mapper.map(data)
    assert isinstance(state, AffectiveState)
    assert 0 <= state.valence <= 1024
    assert 0 <= state.arousal <= 1024
    assert 0 <= state.tension <= 1024

def test_btm_mapper_high_stress():
    mapper = BTMMapper()
    data = TelemetryData(hr=120, hrv=20, stress_score=85.0, valence=0.2)
    state = mapper.map(data)
    assert state.tension > 500  # High stress = high tension
    assert state.valence < 300  # Low valence

def test_btm_mapper_gsr_sensor():
    """GSR gradient contributes to arousal via the BTM pipeline."""
    mapper = BTMMapper()
    # First reading: baseline
    data1 = TelemetryData(hr=72, hrv=55, gsr=2.0, valence=0.5)
    mapper.map(data1)
    # Second reading: GSR spike
    data2 = TelemetryData(hr=72, hrv=55, gsr=5.0, valence=0.5)
    state = mapper.map(data2)
    # GSR gradient should influence arousal
    assert state.arousal > 0

def test_btm_mapper_gsr_no_gradient_no_change():
    """No GSR history = default arousal from HRV only."""
    mapper = BTMMapper()
    data = TelemetryData(hr=72, hrv=55, gsr=3.0, valence=0.5)
    state = mapper.map(data)
    # With only one reading, no gradient to compute
    assert 0 <= state.arousal <= 1024

def test_btm_compute_psi_integer():
    """Integer-shift ψ computation (no floats)."""
    mapper = BTMMapper()
    # Low GSR, moderate HRV → moderate psi
    psi = mapper.compute_psi(hrv_raw=60, gsr_raw=10)
    assert 0 <= psi <= 1024
    
    # High GSR, low HRV → high psi
    psi_high = mapper.compute_psi(hrv_raw=20, gsr_raw=200)
    assert psi_high > psi

def test_btm_psi_from_state():
    mapper = BTMMapper()
    state = AffectiveState(valence=512, arousal=300, tension=768)
    psi = mapper.psi_from_state(state)
    assert 0.0 <= psi <= 1.0
    assert abs(psi - 0.75) < 0.01
