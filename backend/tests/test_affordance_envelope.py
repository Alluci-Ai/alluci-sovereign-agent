import pytest
pytestmark = pytest.mark.unit

from backend.topology.affordance_envelope import ActionAffordanceEnvelope, AffordanceVector


def test_affordance_envelope_safe_action():
    envelope = ActionAffordanceEnvelope(max_hull_radius=1.0)
    vec = envelope.build_affordance_vector(
        action_type="ast_refactor",
        target_resource="backend/routers/memory.py",
        capability_tag="codi_engineering"
    )

    allowed, reason = envelope.evaluate_affordance(vec, subagent_id="codi")
    assert allowed is True
    assert "safe convex envelope" in reason


def test_affordance_envelope_destructive_hitl():
    envelope = ActionAffordanceEnvelope()
    vec = envelope.build_affordance_vector(
        action_type="file_delete",
        target_resource="/etc/system.conf",
        is_destructive=True
    )

    allowed, reason = envelope.evaluate_affordance(vec)
    assert allowed is False
    assert "HITL Executive authorization" in reason


def test_affordance_envelope_subagent_privilege_boundary():
    envelope = ActionAffordanceEnvelope()
    # Rocco (research sub-agent) attempting code refactor
    vec = envelope.build_affordance_vector(
        action_type="ast_refactor",
        target_resource="backend/app.py",
        capability_tag="general"
    )

    allowed, reason = envelope.evaluate_affordance(vec, subagent_id="rocco")
    assert allowed is False
    assert "lacks capability envelope" in reason


def test_affordance_envelope_high_tension_gate():
    envelope = ActionAffordanceEnvelope()
    vec = envelope.build_affordance_vector(
        action_type="file_edit",
        target_resource="backend/models.py"
    )

    # Affective tension exceeds threshold psi=0.9
    allowed, reason = envelope.evaluate_affordance(vec, affective_tension_psi=0.92)
    assert allowed is False
    assert "High affective tension" in reason
