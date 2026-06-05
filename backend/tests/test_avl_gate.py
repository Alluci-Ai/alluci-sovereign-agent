import pytest
from backend.security.avl_gate import AVLGate
from backend.security.dpk import PolytopeState

@pytest.fixture
def gate():
    return AVLGate()

@pytest.fixture
def valid_state():
    state = PolytopeState(
        vertices_V=8,
        edges_E=12,
        faces_F=6,
        phi_total=10,
        budget_used=0.5,
        signature_hash=12345,
        betti=[1, 0, 0, 1],
        affective_tension_psi=0.0
    )
    return state

def test_verify_unsigned(gate, valid_state):
    valid_state.signature_hash = 0
    safe, reason = gate.verify("test", valid_state)
    assert safe is False
    assert "Unsigned manifold" in reason

def test_verify_budget_exceeded(gate, valid_state):
    valid_state.budget_used = 1.1
    safe, reason = gate.verify("test", valid_state)
    assert safe is False
    assert "budget exceeded" in reason

def test_verify_topological_rupture(gate, valid_state):
    valid_state.betti = [10, 0, 0, 0]  # betti_chi = 10, chi = 2. Diff is 8
    safe, reason = gate.verify("test", valid_state)
    assert safe is False
    assert "Topological rupture" in reason

def test_verify_betti_short(gate, valid_state):
    valid_state.betti = [1]  # betti_chi will be 0. chi = 2. Diff = 2 <= 2
    safe, reason = gate.verify("test", valid_state)
    assert safe is True
    assert reason == "OK"

def test_verify_success(gate, valid_state):
    safe, reason = gate.verify("test", valid_state)
    assert safe is True
    assert reason == "OK"

def test_verify_with_refinement_unsigned(gate, valid_state):
    valid_state.signature_hash = 0
    safe, reason, refined = gate.verify_with_refinement("test", valid_state)
    assert safe is False
    assert "Unsigned" in reason
    assert refined is None

def test_verify_with_refinement_budget_catastrophic(gate, valid_state):
    valid_state.budget_used = 2.0  # > 1.5 * limit
    safe, reason, refined = gate.verify_with_refinement("test", valid_state)
    assert safe is False
    assert "beyond refinement threshold" in reason
    assert refined is None

def test_verify_with_refinement_budget_refined(gate, valid_state):
    valid_state.budget_used = 1.25  # <= 1.5
    completion = "1234567890"  # length 10
    safe, reason, refined = gate.verify_with_refinement(completion, valid_state)
    assert safe is True
    assert reason == "REFINED"
    # scale = 1.0 / 1.25 = 0.8
    # max_chars = int(10 * 0.8) = 8
    assert refined == "12345678"

def test_verify_with_refinement_topological_rupture(gate, valid_state):
    valid_state.betti = [10, 0, 0, 0]
    safe, reason, refined = gate.verify_with_refinement("test", valid_state)
    assert safe is False
    assert "Topological rupture" in reason
    assert refined is None

def test_verify_with_refinement_betti_short(gate, valid_state):
    valid_state.betti = [1]
    safe, reason, refined = gate.verify_with_refinement("test", valid_state)
    assert safe is True
    assert reason == "ADMISSIBLE"
    assert refined is None

def test_verify_with_refinement_success(gate, valid_state):
    safe, reason, refined = gate.verify_with_refinement("test", valid_state)
    assert safe is True
    assert reason == "ADMISSIBLE"
    assert refined is None

def test_project_to_boundary_zero_budget(gate, valid_state):
    valid_state.budget_used = 0
    res = gate.project_to_boundary("test", valid_state)
    assert res == "test"
