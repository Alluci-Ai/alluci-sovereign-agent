import torch
from backend.inference.ppn import PPNEmbeddingModule

def test_coherence_score_stability():
    ppn = PPNEmbeddingModule(input_dim=8, latent_dim=8)
    
    # Identical states -> high coherence (max 1.0)
    G = torch.eye(10)
    B = torch.tensor([1.0, 0.0, 0.0, 0.0])
    
    coh1, d1, h1 = ppn.compute_coherence(G, B, B)
    # Entropy of eye matrix: degrees are all 1. 
    # probs = 1/10. H = -sum(0.1 * log2(0.1)) = log2(10). 
    # h_norm = log2(10)/log2(10) = 1.0. 
    # coh = (1-0)*(1-1) = 0.0? 
    # Wait, graph entropy H_norm is HIGH for uniform degrees. 
    # Coherence is (1-H_norm). So high entropy -> low coherence.
    # High entropy means disorganized connections.
    assert coh1 < 0.5
    
    # Low entropy (one node connected to all) -> higher coherence
    G_star = torch.zeros(10, 10)
    G_star[0, :] = 1.0
    G_star[:, 0] = 1.0
    coh2, d2, h2 = ppn.compute_coherence(G_star, B, B)
    assert coh2 > coh1
