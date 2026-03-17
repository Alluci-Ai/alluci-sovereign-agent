import pytest
torch = pytest.importorskip("torch")
from backend.inference.ppn import PPNEmbeddingModule
from backend.ace.affect_kernel import AffectiveState

def test_phi_total_determinism():
    ppn = PPNEmbeddingModule(input_dim=384, latent_dim=384)
    betti = [1.0, 0.0, 0.0, 0.0]
    state = AffectiveState(valence=512.0, arousal=0.0)
    
    phi1 = ppn.compute_phi_total(betti, state)
    phi2 = ppn.compute_phi_total(betti, state)
    
    assert phi1 == phi2
    assert 0 <= phi1 < 65536

def test_phi_total_modulation():
    ppn = PPNEmbeddingModule(input_dim=384, latent_dim=384)
    betti = [1.0, 0.0, 0.0, 0.0]
    
    # Neutral state
    state_neutral = AffectiveState(valence=512.0, arousal=0.0)
    phi_neutral = ppn.compute_phi_total(betti, state_neutral)
    
    # High valence (optimistic)
    state_high = AffectiveState(valence=1024.0, arousal=0.0)
    phi_high = ppn.compute_phi_total(betti, state_high)
    
    # Should be different
    assert phi_neutral != phi_high
