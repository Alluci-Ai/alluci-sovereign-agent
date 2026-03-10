import torch
from backend.inference.kcm import KCMGeodesicCost

def test_kcm_geodesic_cost():
    kcm = KCMGeodesicCost()
    b1 = torch.tensor([1.0, 0.0, 0.0, 0.0])
    b2 = torch.tensor([2.0, 1.0, 0.0, 0.0]) # dist = 2
    
    # Low tension
    cost_low = kcm.compute(b1, b2, psi=0.0)
    assert cost_low == 2.0
    
    # High tension
    cost_high = kcm.compute(b1, b2, psi=1.0)
    assert cost_high == 4.0
