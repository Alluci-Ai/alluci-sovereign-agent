import pytest
pytestmark = pytest.mark.unit

torch = pytest.importorskip("torch")
from backend.inference.ppn import PPNEmbeddingModule

def test_fixed_point_normalization():
    ppn = PPNEmbeddingModule(input_dim=384, hidden_dim=384)
    t = torch.tensor([0.123456, 1.0, -1.0, 40.0, -40.0])
    
    out = ppn.normalize_to_fixed_point(t, scale=1024)
    
    # Check multiples of 1/1024
    for val in out:
        multiplied = val * 1024.0
        assert torch.isclose(torch.tensor(multiplied), torch.round(torch.tensor(multiplied)))
    
    # Check clamping (32767 / 1024 = 31.999)
    assert out[3] <= 32.0
    assert out[4] >= -32.0
