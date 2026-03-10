import pytest
from backend.ace.btm_mapper import BTMMapper
from backend.models import TelemetryData

def test_btm_mapper_arousal():
    mapper = BTMMapper()
    
    # High HRV stability -> low arousal
    data_high = TelemetryData(hrv=100)
    state_high = mapper.map(data_high)
    
    # Low HRV stability -> high arousal
    # Need to feed it some history first
    mapper.map(TelemetryData(hrv=100))
    data_low = TelemetryData(hrv=10)
    state_low = mapper.map(data_low)
    
    assert state_low.arousal > state_high.arousal

def test_btm_mapper_tension():
    mapper = BTMMapper()
    
    # High stress -> high tension
    data = TelemetryData(stress_score=100.0)
    state = mapper.map(data)
    assert state.tension == 1024.0
    assert mapper.psi_from_state(state) == 1.0
    
    # Low stress -> low tension
    data_low = TelemetryData(stress_score=0.0)
    state_low = mapper.map(data_low)
    assert state_low.tension == 0.0
    assert mapper.psi_from_state(state_low) == 0.0

def test_btm_mapper_valence():
    mapper = BTMMapper()
    
    data = TelemetryData(valence=1.0)
    state = mapper.map(data)
    assert state.valence == 1024.0
    
    data_mid = TelemetryData(valence=0.5)
    state_mid = mapper.map(data_mid)
    assert state_mid.valence == 512.0
