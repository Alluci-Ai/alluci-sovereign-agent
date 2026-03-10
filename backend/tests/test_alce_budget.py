import torch
from backend.inference.ppn import PPNEmbeddingModule

def test_alce_budget_tracking():
    ppn = PPNEmbeddingModule(input_dim=8, latent_dim=8)
    x = torch.randn(1, 8)
    
    # First pass: budget should be 0
    _, _, _, _, _, budget1, _, _ = ppn(x)
    assert budget1 == 0.0
    
    # Second pass with same input: budget should be near 0
    _, _, _, _, _, budget2, _, _ = ppn(x)
    assert budget2 < 0.1
    
    # Third pass with different input: budget should be > 0
    x_new = torch.randn(1, 8) * 10.0
    _, _, _, _, _, budget3, _, _ = ppn(x_new)
    assert budget3 > 0.0
