import pytest
torch = pytest.importorskip("torch")
from backend.inference.kcm import KCMGeodesicCost

def test_kcm_cost_basic():
    kcm = KCMGeodesicCost()
    cost = kcm.compute(
        torch.tensor([1.0, 0.0, 0.0]),
        torch.tensor([1.0, 1.0, 0.0]),
        psi=0.5
    )
    assert cost > 0

def test_kcm_hyperbolic_penalty():
    """cosh(ψ/1024) × latency grows exponentially with ψ."""
    kcm = KCMGeodesicCost()
    
    # Low psi: penalty ≈ latency (cosh(0) = 1)
    p_low = kcm.hyperbolic_penalty(psi=0.0, latency_ms=3000.0)
    assert abs(p_low - 3000.0) < 1.0  # cosh(0) = 1.0
    
    # High psi: penalty > latency
    p_high = kcm.hyperbolic_penalty(psi=0.9, latency_ms=3000.0)
    assert p_high > p_low
    
    # Very high psi: exponential growth
    p_very_high = kcm.hyperbolic_penalty(psi=1.0, latency_ms=3000.0)
    assert p_very_high > p_high

def test_kcm_select_model_low_psi():
    """Low ψ → strong model is efficient enough."""
    kcm = KCMGeodesicCost()
    model = kcm.select_model(psi=0.3)
    assert model == "strong"

def test_kcm_select_model_high_psi():
    """High ψ → strong model becomes too expensive, route to light."""
    kcm = KCMGeodesicCost()
    model = kcm.select_model(psi=0.95)
    # At very high psi, the ratio strong_penalty/light_penalty stays constant
    # (both scale by same cosh factor). So it depends on the 2× ratio:
    # strong=3000, light=200, penalty 15× → strong_cost/light_cost = 3000/200 = 15 > 2
    assert model == "light"
