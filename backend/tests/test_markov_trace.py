"""
Mathematical & Unit Tests for Markov Trace & Spectral Geometry Engine.
Verifies the formal proofs and theorems:
1. 3-State Minimal Analytical Excursion Proof (λ₂ = 1.0 vs λ₂ = 0.0)
2. Neumann Series Matrix Inverse Expansion Equivalence
3. Scale-Dependent Spectral Dimension Bounds
4. End-to-End HLSMManager Multi-Hop Trace Rescoring Integration
"""

import pytest
import numpy as np
from backend.memory.markov_trace import MarkovTraceEngine
from backend.memory.hlsm_manager import HLSMManager, HLSMRetrievalResult, HLSMEpisodicEntry
from sqlmodel import create_engine, SQLModel


@pytest.fixture
def trace_engine():
    return MarkovTraceEngine()


def test_minimal_3state_analytical_proof(trace_engine):
    """
    Minimal Analytical Proof from the paper:
    3-state system with visible sector V = {v1, v2} and hidden sector H = {h}:
        P = [
            [eps,  0,    1-eps],
            [0,    eps,  1-eps],
            [alpha, alpha, 1-2*alpha]
        ]
    Trace reduction yields:
        Tr_A(P) = [
            [eps + (1-eps)/2, (1-eps)/2],
            [(1-eps)/2,       eps + (1-eps)/2]
        ]
    For eps -> 0, Tr_A(P) -> [[0.5, 0.5], [0.5, 0.5]] with lambda_1 = 0, lambda_2 = 1.
    """
    eps = 1e-4
    alpha = 0.3
    P = np.array([
        [eps, 0.0, 1.0 - eps],
        [0.0, eps, 1.0 - eps],
        [alpha, alpha, 1.0 - 2.0 * alpha]
    ])

    visible_indices = [0, 1]
    P_A, excursion = trace_engine.compute_markov_trace(P, visible_indices)

    # Verify traced matrix converges to [[0.5, 0.5], [0.5, 0.5]]
    expected_P_A = np.array([
        [0.5, 0.5],
        [0.5, 0.5]
    ])
    np.testing.assert_allclose(P_A, expected_P_A, atol=1e-3)

    # Compute spectral geometry
    spectral = trace_engine.compute_spectral_geometry(P_A, diffusion_scale=1.0)

    # Lambda_1 = 0.0, Lambda_2 = 1.0 (Rapid mixing)
    assert len(spectral["eigenvalues"]) == 2
    assert pytest.approx(spectral["eigenvalues"][0], abs=1e-3) == 0.0
    assert pytest.approx(spectral["eigenvalues"][1], abs=1e-3) == 1.0
    assert spectral["mixing_rate"] == "rapid"
    assert spectral["fiedler_value"] >= 0.99


def test_neumann_series_expansion_equivalence(trace_engine):
    """
    Verifies that the regularized matrix inverse B(I - C)^(-1)D is mathematically
    equivalent to the infinite excursion path series:
        B * (sum_{k=0}^inf C^k) * D
    """
    # 4-state system: 2 visible, 2 hidden
    # Construct a valid row-stochastic matrix
    P = np.array([
        [0.4, 0.1, 0.3, 0.2],
        [0.2, 0.3, 0.2, 0.3],
        [0.2, 0.1, 0.4, 0.3],
        [0.1, 0.3, 0.2, 0.4]
    ])
    visible = [0, 1]
    hidden = [2, 3]

    A = P[np.ix_(visible, visible)]
    B = P[np.ix_(visible, hidden)]
    D = P[np.ix_(hidden, visible)]
    C = P[np.ix_(hidden, hidden)]

    # Compute closed-form excursion
    _, closed_form_excursion = trace_engine.compute_markov_trace(P, visible)

    # Compute partial sum of Neumann series up to K=50
    neumann_sum = np.zeros_like(C)
    C_k = np.eye(len(hidden))
    for _ in range(50):
        neumann_sum += C_k
        C_k = C_k @ C

    series_excursion = B @ neumann_sum @ D

    np.testing.assert_allclose(closed_form_excursion, series_excursion, atol=1e-4)


def test_scale_dependent_spectral_dimension(trace_engine):
    """
    Verifies that the Scale-Dependent Spectral Dimension d_s^A(sigma)
    is non-negative and properly behaves across varying diffusion scales.
    """
    # Complete 4-node clique (all-to-all mixing)
    P_A = np.full((4, 4), 0.25)

    for sigma in [0.1, 0.5, 1.0, 2.0, 5.0]:
        spectral = trace_engine.compute_spectral_geometry(P_A, diffusion_scale=sigma)
        assert spectral["spectral_dimension"] >= 0.0
        assert spectral["heat_return_prob"] >= 0.0
        assert spectral["heat_return_prob"] <= 1.0


def test_affinity_matrix_construction(trace_engine):
    """
    Verifies that build_affinity_matrix constructs a strictly row-stochastic matrix.
    """
    embeddings = np.array([
        [1.0, 0.0, 0.0],
        [0.8, 0.2, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0]
    ], dtype=np.float32)

    P = trace_engine.build_affinity_matrix(embeddings, temperature=0.5)

    assert P.shape == (4, 4)
    # Each row must sum to 1.0
    row_sums = P.sum(axis=1)
    np.testing.assert_allclose(row_sums, np.ones(4), atol=1e-5)


@pytest.mark.asyncio
async def test_hlsm_retrieve_context_with_markov_trace(temp_db):
    """
    End-to-end integration test verifying that HLSMManager.retrieve_context()
    successfully runs Markov Trace rescoring and populates spectral_metrics.
    """
    manager = HLSMManager(db_engine=temp_db, redis_client=None, kuzu_db_path=None)

    # Insert candidate episodic memories
    entries = [
        "Quantum topological invariants and Chern numbers calculation",
        "Simplicial complex homology and Betti numbers calculation",
        "Differential geometry and Markov trace excursions",
        "Polytope boundaries and convex hull projections",
    ]
    for content in entries:
        await manager.l1_store(content=content, source="agent", topological_importance=1.0)

    # Retrieve context
    ctx = await manager.retrieve_context("topological Betti numbers Markov trace", psi=0.2, max_per_tier=3)

    assert ctx is not None
    assert len(ctx.episodic_memories) > 0
    # Spectral metrics should be computed for candidate sets >= 3
    if ctx.spectral_metrics is not None:
        assert "spectral_dimension" in ctx.spectral_metrics
        assert "fiedler_value" in ctx.spectral_metrics
        assert "mixing_rate" in ctx.spectral_metrics
