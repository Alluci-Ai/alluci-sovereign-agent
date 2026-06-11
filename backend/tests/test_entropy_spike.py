import pytest
pytestmark = pytest.mark.unit

numpy = pytest.importorskip("numpy")
from backend.ace.entropy_monitor import EntropySpikeDetector

def test_entropy_spike_detection():
    detector = EntropySpikeDetector(window_size=10)
    
    # Baseline
    for _ in range(8):
        detector.push(0.5)
    
    # Normal variation
    assert not detector.push(0.55)
    
    # Sudden spike
    assert detector.push(1.5)
