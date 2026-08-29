import pytest
import numpy as np
from backend.security.trajectory import TrajectoryTracker
from backend.security.health_monitor import PVTManifoldHealthMonitor
from backend.security.dpk import PolytopeState

pytestmark = pytest.mark.unit


def test_linear_trajectory_zero_curvature():
    """
    Verifies that straight-line cognitive trajectory produces zero curvature (κ = 0).
    """
    tracker = TrajectoryTracker()
    
    # Linear steps along x-axis
    tracker.push_state(np.array([1.0, 0.0, 0.0]))
    tracker.push_state(np.array([2.0, 0.0, 0.0]))
    m3 = tracker.push_state(np.array([3.0, 0.0, 0.0]))

    assert m3["velocity_norm"] == 1.0
    assert m3["accel_norm"] == 0.0
    assert m3["curvature"] == 0.0
    assert tracker.is_ruptured() is False


def test_circular_trajectory_curvature():
    """
    Verifies that circular trajectory of radius R produces curvature κ ≈ 1/R.
    """
    tracker = TrajectoryTracker()
    R = 2.0
    # Small angle steps
    dt = 0.1
    for i in range(5):
        theta = i * dt
        x = R * np.cos(theta)
        y = R * np.sin(theta)
        z = 0.0
        m = tracker.push_state(np.array([x, y, z]))

    # Expected curvature for circle of radius 2 is 1/R = 0.5
    last_m = tracker.get_last_metrics()
    assert abs(last_m["curvature"] - (1.0 / R)) < 0.05
    assert tracker.is_ruptured() is False


def test_angular_snap_trajectory_rupture():
    """
    Verifies that a sudden orthogonal snap (high curvature > 5.0) triggers trajectory rupture.
    """
    tracker = TrajectoryTracker(critical_curvature=5.0)

    # Step 1 & 2: step along x with delta = 0.1
    tracker.push_state(np.array([0.0, 0.0, 0.0]))
    tracker.push_state(np.array([0.1, 0.0, 0.0]))
    
    # Step 3: sudden sharp 90-degree snap to y with delta = 0.1 (κ = 10.0 > 5.0)
    m3 = tracker.push_state(np.array([0.1, 0.1, 0.0]))

    assert m3["curvature"] >= 5.0
    assert tracker.is_ruptured() is True


def test_pvt_health_monitor_with_trajectory():
    """
    Verifies PVT health monitor seamlessly incorporates trajectory metrics.
    """
    monitor = PVTManifoldHealthMonitor()

    state1 = PolytopeState(
        signature_hash=12345,
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.1,
        phi_total=10,
        coherence=0.9,
        budget_used=0.1,
        stella_projection=[0.0, 0.0, 0.0]
    )
    r1 = monitor.evaluate(state1)
    assert r1["status"] == "HEALTHY"
    assert "trajectory" in r1

    state2 = PolytopeState(
        signature_hash=12345,
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.1,
        phi_total=10,
        coherence=0.9,
        budget_used=0.1,
        stella_projection=[0.1, 0.0, 0.0]
    )
    r2 = monitor.evaluate(state2)
    assert r2["status"] == "HEALTHY"

    # Step 3: Violent trajectory snap (0.1, 0.1, 0.0) -> curvature = 10.0
    state3 = PolytopeState(
        signature_hash=12345,
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.1,
        phi_total=10,
        coherence=0.9,
        budget_used=0.1,
        stella_projection=[0.1, 0.1, 0.0] # Sharp orthogonal snap
    )
    r3 = monitor.evaluate(state3)
    assert r3["is_ruptured"] is True
    assert monitor.is_ruptured() is True
    assert r3["status"] == "CRITICAL"
    assert any("Curvature" in issue for issue in r3["issues"])
