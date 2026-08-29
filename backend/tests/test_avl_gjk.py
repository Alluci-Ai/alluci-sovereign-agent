import pytest
import numpy as np
from backend.security.stella_octangula import StellaOctangulaGeometry
from backend.security.avl_gate import AVLGate
from backend.security.dpk import PolytopeState

pytestmark = pytest.mark.unit


def test_stella_gjk_support_point():
    """
    Verifies that the GJK support function S_{S8}(d) returns the extreme
    vertex maximizing the dot product along arbitrary directions.
    """
    geom = StellaOctangulaGeometry()

    # Direction (1, 1, 1) should return vertex (1, 1, 1)
    supp_pos = geom.get_support_point(np.array([1.0, 1.0, 1.0]))
    np.testing.assert_allclose(supp_pos, np.array([1.0, 1.0, 1.0]))

    # Direction (-1, -1, -1) should return vertex (-1, -1, -1)
    supp_neg = geom.get_support_point(np.array([-1.0, -1.0, -1.0]))
    np.testing.assert_allclose(supp_neg, np.array([-1.0, -1.0, -1.0]))

    # Direction (1, 0, 0) should return a vertex with x = 1
    supp_x = geom.get_support_point(np.array([1.0, 0.0, 0.0]))
    assert supp_x[0] == 1.0


def test_stella_gjk_distance_and_projection():
    """
    Verifies Euclidean distance computation and boundary projection onto Conv(S8).
    """
    geom = StellaOctangulaGeometry()

    # Point inside convex hull
    p_inside = np.array([0.2, -0.4, 0.8])
    dist_inside, proj_inside = geom.compute_gjk_distance(p_inside)
    assert dist_inside == 0.0
    np.testing.assert_allclose(proj_inside, p_inside)

    # Point outside convex hull: (2.0, -3.0, 1.5)
    p_outside = np.array([2.0, -3.0, 1.5])
    dist_outside, proj_outside = geom.compute_gjk_distance(p_outside)
    expected_proj = np.array([1.0, -1.0, 1.0])
    expected_dist = float(np.linalg.norm(p_outside - expected_proj))
    assert dist_outside > 0.0
    np.testing.assert_allclose(proj_outside, expected_proj)
    assert pytest.approx(dist_outside) == expected_dist


def test_avl_verify_action_payload_clean():
    """
    Verifies that a valid structured tool action payload passes without alteration.
    """
    gate = AVLGate()
    state = PolytopeState(
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.0,
        signature_hash=99999,
        budget_used=0.2,
        origin="test_tool_origin",
        is_tool_action=True
    )
    payload = {"query": "SELECT * FROM memory", "limit": 10, "timeout": 30}
    is_safe, reason, refined = gate.verify_action_payload("search_db", payload, state)
    assert is_safe is True
    assert reason == "OK"
    assert refined == payload


def test_avl_verify_action_payload_refinement():
    """
    Verifies that structured tool parameters exceeding boundary bounds are clamped via GJK refinement.
    """
    gate = AVLGate()
    state = PolytopeState(
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.0,
        signature_hash=99999,
        budget_used=1.2, # Slightly above 1.0 budget, but <= 1.5
        origin="local",
        is_tool_action=True
    )
    payload = {"query": "SELECT * FROM memory", "limit": 500, "timeout": 300, "depth": 10}
    is_safe, reason, refined = gate.verify_action_payload("search_db", payload, state)
    assert is_safe is True
    assert reason == "REFINED"
    assert refined is not None
    # Check that parameters were clamped
    assert refined["limit"] <= 100
    assert refined["timeout"] <= 120
    assert refined["depth"] <= 5


def test_avl_verify_stream_chunk():
    """
    Verifies real-time streaming token chunk verification.
    """
    gate = AVLGate()
    state_valid = PolytopeState(
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.0,
        signature_hash=12345,
        budget_used=0.5
    )
    ok, reason = gate.verify_stream_chunk("This is a verified token chunk.", state_valid)
    assert ok is True
    assert reason == "OK"

    state_unsigned = PolytopeState(
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.0,
        signature_hash=0,
        budget_used=0.5
    )
    ok_unsign, reason_unsign = gate.verify_stream_chunk("Test", state_unsigned)
    assert ok_unsign is False
    assert "Unsigned" in reason_unsign


def test_avl_protocol3_lipschitz_saturation():
    """
    Verifies Protocol 3: 3 successive Lipschitz budget breaches trigger saturation.
    """
    gate = AVLGate()
    origin = "sat_origin"

    state_breach = PolytopeState(
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.0,
        signature_hash=55555,
        budget_used=2.5, # Catastrophic breach > 1.5
        origin=origin
    )

    # Strike 1
    safe1, reason1 = gate.verify("test action", state_breach)
    assert safe1 is False
    assert gate.get_saturation_strikes(origin) == 1
    assert gate.is_lipschitz_saturated(origin) is False

    # Strike 2
    safe2, reason2 = gate.verify("test action 2", state_breach)
    assert safe2 is False
    assert gate.get_saturation_strikes(origin) == 2
    assert gate.is_lipschitz_saturated(origin) is False

    # Strike 3 -> Saturated!
    safe3, reason3 = gate.verify("test action 3", state_breach)
    assert safe3 is False
    assert gate.get_saturation_strikes(origin) == 3
    assert gate.is_lipschitz_saturated(origin) is True

    # Reset on valid state
    state_valid = PolytopeState(
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        betti=[1.0, 0.0, 0.0, 0.0],
        affective_tension_psi=0.0,
        signature_hash=55555,
        budget_used=0.1,
        origin=origin
    )
    safe_ok, _ = gate.verify("valid action", state_valid)
    assert safe_ok is True
    assert gate.get_saturation_strikes(origin) == 0
    assert gate.is_lipschitz_saturated(origin) is False
