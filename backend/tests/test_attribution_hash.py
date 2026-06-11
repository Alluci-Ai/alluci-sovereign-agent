import pytest
pytestmark = pytest.mark.unit

from backend.security.dpk import DiscreteProjectionKernel

def test_attribution_hash_determinism():
    dpk = DiscreteProjectionKernel()
    betti = [1.0, 0.0, 0.0, 0.0]
    chi = 1
    
    h1 = dpk.compute_signature_hash(betti, chi)
    h2 = dpk.compute_signature_hash(betti, chi)
    
    assert h1 == h2
    assert h1 != 0

def test_attribution_hash_uniqueness():
    dpk = DiscreteProjectionKernel()
    h1 = dpk.compute_signature_hash([1.0, 0.0, 0.0, 0.0], 1)
    h2 = dpk.compute_signature_hash([2.0, 1.0, 0.0, 0.0], 1)
    
    assert h1 != h2
