import pytest
pytestmark = pytest.mark.unit

from backend.security.health_monitor import PVTManifoldHealthMonitor
from backend.security.dpk import PolytopeState

def test_health_monitor_evaluation():
    monitor = PVTManifoldHealthMonitor()
    
    # Healthy state
    state_ok = PolytopeState(
        signature_hash=1, vertices_V=10, edges_E=9, faces_F=0,
        betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.1,
        phi_total=123, coherence=0.9, budget_used=0.1
    )
    report = monitor.evaluate(state_ok)
    assert report["status"] == "HEALTHY"
    assert report["score"] > 0.9

    # Critical state
    state_bad = PolytopeState(
        signature_hash=1, vertices_V=10, edges_E=9, faces_F=0,
        betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.9,
        phi_total=123, coherence=0.2, budget_used=0.95
    )
    report_bad = monitor.evaluate(state_bad)
    assert report_bad["status"] == "CRITICAL"
    assert len(report_bad["issues"]) >= 3

def test_pvt_formulas():
    """PVT triple uses spec-compliant formulas."""
    monitor = PVTManifoldHealthMonitor()

    state = PolytopeState(
        signature_hash=1, vertices_V=5, edges_E=4, faces_F=1,
        betti=[1.0, 1.0, 0.0, 0.0], affective_tension_psi=0.5,
        phi_total=42, coherence=0.8, budget_used=0.3
    )
    report = monitor.evaluate(state)
    
    assert "pvt" in report
    pvt = report["pvt"]
    assert "P" in pvt and "V" in pvt and "T" in pvt
    
    # Volume = (1 - budget_used) * coherence = 0.7 * 0.8 = 0.56
    assert abs(pvt["V"] - 0.56) < 0.01

def test_pvt_rupture_detection():
    """T > 0.8 triggers manifold rupture."""
    monitor = PVTManifoldHealthMonitor()

    # First call sets baseline Betti
    state1 = PolytopeState(
        signature_hash=1, vertices_V=5, edges_E=4, faces_F=1,
        betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.2,
        phi_total=42, coherence=0.9, budget_used=0.1
    )
    monitor.evaluate(state1)

    # Second call with massive Betti shift + coherence drop
    state2 = PolytopeState(
        signature_hash=1, vertices_V=5, edges_E=4, faces_F=1,
        betti=[5.0, 3.0, 2.0, 1.0], affective_tension_psi=0.9,
        phi_total=42, coherence=0.1, budget_used=0.95
    )
    report = monitor.evaluate(state2)
    assert report.get("is_ruptured") is True
    assert monitor.is_ruptured()

def test_pvt_get_last_pvt():
    monitor = PVTManifoldHealthMonitor()
    state = PolytopeState(
        signature_hash=1, vertices_V=5, edges_E=4, faces_F=1,
        betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.3,
        phi_total=42, coherence=0.85, budget_used=0.2
    )
    monitor.evaluate(state)
    
    pvt = monitor.get_last_pvt()
    assert isinstance(pvt, dict)
    assert "P" in pvt and "V" in pvt and "T" in pvt
