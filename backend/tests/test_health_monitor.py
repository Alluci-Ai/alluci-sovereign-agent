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
