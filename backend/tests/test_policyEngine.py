import pytest
pytestmark = pytest.mark.unit

from backend.security.policyEngine import AutonomyPolicyEngine, ExecutionManifest, AceStateVector, AutonomyLevel

@pytest.fixture
def engine():
    return AutonomyPolicyEngine()

@pytest.fixture
def manifest():
    return ExecutionManifest(objective_id="1", model_version="v1", planner_version="v1")

@pytest.fixture
def ace():
    return AceStateVector(physical_energy=1.0, cognitive_load=0.0)

def test_evaluate_restricted_reject(engine, manifest, ace):
    manifest.autonomy_level = AutonomyLevel.RESTRICTED
    assert engine.evaluate(manifest, risk_score=11.0, ace_state=ace) is False

def test_evaluate_restricted_accept(engine, manifest, ace):
    manifest.autonomy_level = AutonomyLevel.RESTRICTED
    assert engine.evaluate(manifest, risk_score=9.0, ace_state=ace) is True

def test_evaluate_semi_autonomous_accept(engine, manifest, ace):
    manifest.autonomy_level = AutonomyLevel.SEMI_AUTONOMOUS
    assert engine.evaluate(manifest, risk_score=49.0, ace_state=ace) is True

def test_evaluate_semi_autonomous_reject(engine, manifest, ace):
    manifest.autonomy_level = AutonomyLevel.SEMI_AUTONOMOUS
    assert engine.evaluate(manifest, risk_score=51.0, ace_state=ace) is False

def test_evaluate_sovereign_accept(engine, manifest, ace):
    manifest.autonomy_level = AutonomyLevel.SOVEREIGN
    assert engine.evaluate(manifest, risk_score=89.0, ace_state=ace) is True

def test_evaluate_sovereign_reject(engine, manifest, ace):
    manifest.autonomy_level = AutonomyLevel.SOVEREIGN
    assert engine.evaluate(manifest, risk_score=91.0, ace_state=ace) is False

def test_evaluate_missing_attrs(engine):
    assert engine.evaluate(object(), risk_score=5.0, ace_state=object()) is False
    assert engine.evaluate(ExecutionManifest(objective_id="1", model_version="1", planner_version="1"), risk_score=5.0, ace_state=object()) is False

def test_evaluate_ace_modulation(engine, manifest, ace):
    manifest.autonomy_level = AutonomyLevel.SEMI_AUTONOMOUS
    # Base threshold is 50.0
    # energy_modulator = 0.5, load_modulator = 0.5 (1.0 - 0.5)
    # dynamic threshold = 50.0 * 0.5 * 0.5 = 12.5
    ace.physical_energy = 0.5
    ace.cognitive_load = 0.5
    assert engine.evaluate(manifest, risk_score=12.0, ace_state=ace) is True
    assert engine.evaluate(manifest, risk_score=13.0, ace_state=ace) is False
