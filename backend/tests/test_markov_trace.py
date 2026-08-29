import pytest
import numpy as np
pytestmark = pytest.mark.unit

from backend.topology.markov_trace import MarkovTraceEngine, DPOTripletHarvester, DPOTriplet


def test_schur_complement_trace():
    engine = MarkovTraceEngine()
    # 4x4 matrix
    P = np.array([
        [0.8, 0.1, 0.05, 0.05],
        [0.1, 0.7, 0.1, 0.1],
        [0.2, 0.1, 0.5, 0.2],
        [0.1, 0.2, 0.1, 0.6]
    ])

    trace_score = engine.compute_schur_complement_trace(P)
    assert isinstance(trace_score, float)
    assert trace_score > 0.0


def test_frenet_serret_curvature_smooth():
    engine = MarkovTraceEngine()
    # Smooth line trajectory
    pts = np.array([
        [0.0, 0.0, 0.0],
        [1.0, 1.0, 1.0],
        [2.0, 2.0, 2.0],
        [3.0, 3.0, 3.0]
    ])

    kappa, is_smooth = engine.compute_frenet_serret_curvature(pts)
    assert is_smooth is True
    assert kappa <= 5.0


def test_dpo_triplet_harvester_record(tmp_path):
    harvester = DPOTripletHarvester(workspace_root=str(tmp_path))
    triplet = harvester.record_triplet(
        prompt_x="Generate safe memory search route",
        winning_yw="Use typed query params with bounds",
        losing_yl="Direct unvalidated string formatting",
        category="gjk_snapback"
    )

    assert triplet.triplet_id.startswith("dpo_")
    assert triplet.winning_response_yw == "Use typed query params with bounds"

    recent = harvester.list_recent_triplets(limit=10)
    assert len(recent) == 1
    assert recent[0]["triplet_id"] == triplet.triplet_id
