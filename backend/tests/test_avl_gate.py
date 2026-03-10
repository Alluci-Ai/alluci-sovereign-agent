from backend.security.avl_gate import AVLGate
from backend.security.dpk import PolytopeState

def test_avl_gate_rejection():
    avl = AVLGate()
    
    # 1. Reject unsigned
    state_unsigned = PolytopeState(
        signature_hash=0, vertices_V=10, edges_E=20, faces_F=11,
        betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.5,
        budget_used=0.1, coherence=0.9
    )
    safe, reason = avl.verify("test", state_unsigned)
    assert not safe
    assert "Unsigned" in reason

    # 2. Reject budget overflow
    state_budget = PolytopeState(
        signature_hash=123, vertices_V=10, edges_E=20, faces_F=11,
        betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.5,
        budget_used=1.5, coherence=0.9
    )
    safe, reason = avl.verify("test", state_budget)
    assert not safe
    assert "budget" in reason

    # 3. Reject topological rupture
    state_rupture = PolytopeState(
        signature_hash=123, vertices_V=10, edges_E=50, faces_F=11, # χ = 10 - 50 + 11 = -29
        betti=[1.0, 0.0, 0.0, 0.0], # β_chi = 1
        affective_tension_psi=0.5,
        budget_used=0.1, coherence=0.9
    )
    safe, reason = avl.verify("test", state_rupture)
    assert not safe
    assert "Topological" in reason

def test_avl_gate_success():
    avl = AVLGate()
    state = PolytopeState(
        signature_hash=123, vertices_V=10, edges_E=9, faces_F=0, # χ = 1
        betti=[1.0, 0.0, 0.0, 0.0], # β_chi = 1
        affective_tension_psi=0.5,
        budget_used=0.1, coherence=0.9
    )
    safe, reason = avl.verify("test", state)
    assert safe
    assert reason == "OK"
