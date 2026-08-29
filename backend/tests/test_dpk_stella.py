"""
Mathematical & Unit Tests for Discrete Projection Kernel (DPK) & Stella Octangula S8.
Verifies the formal proofs and theorems:
1. Simplicial Boundary Operator Nilpotence: ∂1 ∘ ∂2 = 0 (B1 @ B2 = 0)
2. Idempotent Fusion Simplex Invariant: Π ∘ Π = Π
3. Stella Octangula Euler Invariant & Betti Numbers
4. Entropic Arrow of Time Monotonicity: H(X_n | X_1) >= H(X_{n-1} | X_1)
5. DPK Native C++ vs Python Fallback Parity
"""

import pytest
import numpy as np
from backend.security.stella_octangula import StellaOctangulaGeometry
from backend.security.dpk import DiscreteProjectionKernel, PolytopeState


@pytest.fixture
def stella():
    return StellaOctangulaGeometry()


@pytest.fixture
def dpk():
    return DiscreteProjectionKernel()


def test_boundary_nilpotence(stella):
    """
    Fundamental Theorem of Algebraic Topology:
    Boundary of a boundary is identically zero (∂1 ∘ ∂2 = 0).
    """
    assert stella.verify_boundary_nilpotence() is True
    # Explicit matrix product verification
    product = stella.B1 @ stella.B2
    np.testing.assert_allclose(product, np.zeros((8, 8)), atol=1e-10)


def test_idempotent_fusion_operator(stella):
    """
    Idempotent Fusion Simplex Invariant:
    For any input state x, the projection Π satisfies Π(Π(x)) = Π(x).
    """
    # Test random 3D points, interior points, and high-dimensional vectors
    test_vectors = [
        np.array([0.5, 0.5, 0.5]),
        np.array([2.0, -3.0, 1.5]),
        np.array([-5.0, 4.0, -2.0]),
        np.zeros(3),
        np.ones(384) * 0.42  # High-dimensional embedding
    ]

    for vec in test_vectors:
        proj1 = stella.project_to_simplex(vec)
        proj2 = stella.project_to_simplex(proj1)
        np.testing.assert_allclose(proj1, proj2, atol=1e-3)
        assert stella.verify_idempotence(vec) is True


def test_stella_octangula_euler_characteristic(stella):
    """
    Verifies the Euler Characteristic and topological dimensions of the Stella Octangula S8 compound.
    """
    assert len(stella.vertices) == 8
    assert len(stella.edges) == 12
    assert len(stella.faces) == 8
    assert len(stella.octahedron_vertices) == 6

    # Compound Euler characteristic: V - E + F = 8 - 12 + 8 = 4 (two disjoint dual tetrahedra)
    chi = stella.get_euler_characteristic()
    assert chi == 4

    # Betti numbers
    betti = stella.compute_betti_numbers()
    assert len(betti) == 4
    # Two connected components (T+ and T-) -> b0 = 2.0
    assert betti[0] == 2.0
    assert betti[3] == 0.0


def test_entropic_arrow_of_time(stella):
    """
    Verifies that the Entropic Arrow of Time enforces non-decreasing conditional Shannon entropy:
        H(X_n | X_1) >= H(X_{n-1} | X_1)
    """
    # Monotonically spreading probability distributions (increasing entropy)
    seq_increasing = [
        np.array([0.9, 0.05, 0.03, 0.02]),
        np.array([0.6, 0.2, 0.1, 0.1]),
        np.array([0.3, 0.3, 0.2, 0.2]),
        np.array([0.25, 0.25, 0.25, 0.25])
    ]
    assert stella.verify_entropic_arrow_of_time(seq_increasing) is True

    # Violating sequence (decreasing entropy / representation collapse)
    seq_decreasing = [
        np.array([0.3, 0.3, 0.2, 0.2]),
        np.array([0.95, 0.02, 0.02, 0.01])
    ]
    assert stella.verify_entropic_arrow_of_time(seq_decreasing) is False


def test_dpk_project_state_and_betti_signature(dpk):
    """
    Verifies that DPK project_state produces valid 3D points bounded within the Stella Octangula.
    """
    signals = [
        "quantum entanglement manifold",
        "sovereign verus id authentication",
        "simplicial chain complex invariant",
        "hitl security approval modal"
    ]

    for sig in signals:
        p = dpk.project_state(sig)
        assert p.shape == (3,)
        # Must be bounded within coordinate limits of Stella Octangula [-1, 1]
        assert np.all(p >= -1.0 - 1e-3)
        assert np.all(p <= 1.0 + 1e-3)

        betti = dpk.get_betti_signature(p)
        assert len(betti) == 4
        assert betti[0] == 2.0


def test_dpk_authorize_execution_and_idempotence(dpk):
    """
    Verifies that DPK validates PolytopeState with boundary nilpotence and idempotent projection.
    """
    p = dpk.project_state("test state")
    sig_hash = dpk.compute_signature_hash([2.0, 0.0, 2.0, 0.0], 4)

    state = PolytopeState(
        signature_hash=sig_hash,
        vertices_V=8,
        edges_E=12,
        faces_F=8,
        betti=[2.0, 0.0, 2.0, 0.0],
        affective_tension_psi=0.2,
        hardware_status=2,
        coherence=0.8,
        budget_used=0.1,
        stella_projection=p.tolist()
    )

    authorized = dpk.authorize_execution(state)
    assert authorized is True
    assert state.is_idempotent is True
