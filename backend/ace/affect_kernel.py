from dataclasses import dataclass
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@dataclass
class AffectiveState:
    # Core Affective Dimensions
    valence: float = 512.0   # 0=pessimistic, 512=neutral, 1024=optimistic
    arousal: float = 0.0     # 0=calm, 1024=maximum arousal
    tension: float = 0.0     # 0=relaxed, 1024=maximum contraction
    
    # [ PPN-010 ] Physical Biometrics (Multimodal Polytope Fusion)
    heart_rate: float = 70.0       # bpm
    hrv: float = 50.0              # ms
    respiratory_rate: float = 16.0 # breaths/min
    
    def fuse_biometrics(self):
        """
        Sub-microsecond projection of raw biometrics into affective dimensions.
        Avoids slow string-to-vector conversion.
        """
        # Baseline heuristics mapping biometrics to affective dimensions
        # High HR + Low HRV + High RR = High Arousal, High Tension, Low Valence (Stress)
        self.arousal = max(0.0, min(1024.0, (self.heart_rate - 60.0) * 10.0 + (self.respiratory_rate - 12.0) * 20.0))
        self.tension = max(0.0, min(1024.0, (100.0 - self.hrv) * 10.0))
        self.valence = max(0.0, min(1024.0, 512.0 + (self.hrv - 50.0) * 5.0 - (self.heart_rate - 70.0) * 2.0))



class AffectKernel:
    """
    Integer-based affective deformation kernel.
    Source: PPN §affect_op.cpp — apply_deformation()

    Applies three sequential fixed-point transforms:
      1. Tension-driven contraction (denominator scaling)
      2. Arousal-driven dilation (bit-shifted multiply)
      3. Valence-driven shear (register bias)
    """
    SCALE = 2048            # Fixed-point scale factor
    NEUTRAL_TENSION = 1024  # Neutral tension coefficient
    MAX_VAL = 32767         # int16 max for manifold safety

    def apply(self, raw_val: float, state: AffectiveState) -> float:
        """
        Apply affective deformation to a single scalar value.

        Formula:
            tension_coeff = 1024 + (tension × 8)
            dilated = (raw_int × (1024 + arousal)) >> 10
            dilated += int(valence × 512) >> 2
            final = clamp((dilated × 1024) // tension_coeff, -32767, 32767)
            return final / 2048.0
        """
        # 1. Tension coefficient — contraction denominator
        tension_coeff = self.NEUTRAL_TENSION + int(state.tension * 8)

        # 2. Arousal dilation — fixed-point multiply + bit-shift
        raw_int = int(raw_val * self.SCALE)
        dilated = (raw_int * (self.NEUTRAL_TENSION + int(state.arousal))) >> 10

        # 3. Valence shear — biases semantic register
        dilated += int(state.valence * 512) >> 2

        # 4. ALCE Lipschitz normalization — prevent manifold tearing
        final = (dilated * self.NEUTRAL_TENSION) // max(tension_coeff, 1)
        final = max(-self.MAX_VAL, min(self.MAX_VAL, final))

        return final / float(self.SCALE)

    def apply_tensor(self, t: 'torch.Tensor', state: AffectiveState) -> 'torch.Tensor':
        """Batch-apply deformation to an entire embedding tensor."""
        if not HAS_TORCH:
            raise ImportError("PyTorch required for apply_tensor. Install 'torch' to enable tensor deformation.")
        # Optimization: use vectorized torch operations if possible, 
        # but the spec provides a scalar loop for precision matching with C++ ref.
        # However, for performance on tensors, we should vectorize.
        
        # 1. Tension coefficient
        tension_coeff = self.NEUTRAL_TENSION + int(state.tension * 8)
        
        # 2. Arousal dilation
        raw_int = (t * self.SCALE).to(torch.long)
        dilated = (raw_int * (self.NEUTRAL_TENSION + int(state.arousal))) >> 10
        
        # 3. Valence shear
        dilated += int(state.valence * 512) >> 2
        
        # 4. ALCE Lipschitz normalization
        final = (dilated * self.NEUTRAL_TENSION) // max(tension_coeff, 1)
        final = torch.clamp(final, -self.MAX_VAL, self.MAX_VAL)
        
        return final.to(torch.float32) / float(self.SCALE)
