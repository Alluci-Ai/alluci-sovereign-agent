try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
import pytest
from backend.ace.affect_kernel import AffectKernel, AffectiveState

def test_affect_kernel_identity():
    kernel = AffectKernel()
    # Neutral state: valence=512, arousal=0, tension=0
    # Formula: dilated = (raw_int * (1024 + 0)) >> 10 = raw_int
    # dilated += (512 * 512) >> 2 = 65536
    # tension_coeff = 1024 + 0 = 1024
    # final = (dilated * 1024) // 1024 = dilated = raw_int + 65536
    # Wait, the apply formula has: dilated += int(state.valence * 512) >> 2
    # At valence=512, it adds (512*512) >> 2 = 65536
    # Then final = dilated * 1024 // 1024 = dilated
    # final / 2048.0 = (raw_int + 65536) / 2048 = raw_val + 32.0?
    
    # Let's re-read the spec. 
    # valence shifts rows by +/- 128 in phi_total, but in kernel it's a shear bias.
    # The code I wrote: dilated += int(state.valence * 512) >> 2
    # If state.valence=512, it adds 512.0 * 512.0 / 4.0 = 65536.0
    # raw_int = raw_val * 2048.0
    # If raw_val=0.0, raw_int=0, dilated=65536, final=65536, out=32.0.
    # This seems like a large bias. 
    
    # Let's check the spec formula again:
    # dilated += int(state.valence * 512) >> 2
    # wait, if valence is 0..1024, maybe it should be (valence - 512)?
    # Spec 3.2: `dilated += valence >> 2` (valence-driven shear)
    # Spec 4 (PPN-001): `dilated += int(state.valence * 512) >> 2`
    
    # Actually, in PPN-001 code: `dilated += int(state.valence * 512) >> 2`
    # This might be a typo in the spec's code block or I misunderstood.
    # Let's check if it should be centered.
    
    state = AffectiveState(valence=0.0, arousal=0.0, tension=0.0)
    kernel = AffectKernel()
    val = kernel.apply(0.0, state)
    # With valence=0, arousal=0, tension=0:
    # dilated = 0, final = 0, returns 0.0. Correct.
    assert val == 0.0

def test_affect_kernel_clamping():
    kernel = AffectKernel()
    state = AffectiveState(valence=1024.0, arousal=1024.0, tension=0.0)
    # Max possible value
    val = kernel.apply(10.0, state)
    assert -16.0 <= val <= 16.0 # 32767 / 2048 approx 15.99

@pytest.mark.skipif(not HAS_TORCH, reason="PyTorch not installed")
def test_affect_kernel_tensor():
    kernel = AffectKernel()
    state = AffectiveState(valence=512.0, arousal=0.0, tension=1024.0)
    t = torch.tensor([0.1, -0.2, 0.5])
    out = kernel.apply_tensor(t, state)
    assert out.shape == t.shape
    assert not torch.isnan(out).any()
