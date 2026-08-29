import pytest
import numpy as np
pytestmark = pytest.mark.unit

from backend.topology.j_space_simulator import (
    JSpaceSimulator,
    SimplicialChainOfThought,
    DualTetrahedronSocraticSynthesis,
)


def test_simplicial_chain_of_thought_strict_vs_elastic():
    cot_strict = SimplicialChainOfThought(strict_mode=True)
    cot_elastic = SimplicialChainOfThought(strict_mode=False)

    # Valid step
    passed, reason = cot_strict.verify_reasoning_step(
        premise_a="Session token is verified",
        premise_b="Caller is authenticated",
        conclusion="Access granted to sovereign memory",
        is_code_or_tool_dag=True
    )
    assert passed is True

    # Tautological circularity check
    passed_circ, reason_circ = cot_strict.verify_reasoning_step(
        premise_a="Data is valid",
        premise_b="",
        conclusion="Data is valid",
        is_code_or_tool_dag=True
    )
    assert passed_circ is False
    assert "circularity" in reason_circ.lower()


def test_socratic_dialectic_synthesis():
    socratic = DualTetrahedronSocraticSynthesis()
    p_vec = np.array([1.0, 0.5, 0.2])
    s_vec = np.array([-0.8, -0.3, 0.1])

    outcome = socratic.synthesize(p_vec, s_vec)
    assert outcome.synthesized_vector.shape == (3,)
    assert 0.0 <= outcome.coherence_score <= 1.0
    assert isinstance(outcome.is_admissible_to_action, bool)
    assert "Socratic dialectic" in outcome.synthesis_rationale


def test_j_space_simulator_rollout():
    sim = JSpaceSimulator(strict_cot=True)
    steps = [
        ("File exists on disk", "Permissions are read-only", "Open in read-mode"),
        ("Buffer decoded", "AST parsed cleanly", "Return symbol catalog")
    ]

    p_feat = np.array([0.5, 0.5, 0.5])
    s_feat = np.array([-0.5, -0.5, 0.5])

    trace = sim.simulate_rollout(
        experience_hash=12345678,
        reasoning_steps=steps,
        proposer_feature=p_feat,
        skeptic_feature=s_feat,
        is_code_or_tool_dag=True
    )

    assert trace.is_topologically_coherent is True
    assert trace.loop_detected is False
    assert len(trace.simulated_steps) == 2
    assert trace.execution_time_ms >= 0.0
    assert trace.betti_invariants[0] == 1.0
