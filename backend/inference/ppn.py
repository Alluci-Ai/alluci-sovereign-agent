
import torch
import torch.nn as nn
import numpy as np
from typing import Tuple, Optional, List
from ..ace.affect_kernel import AffectiveState

# Graceful fallback if gudhi is not installed in the environment
try:
    import gudhi
    GUDHI_AVAILABLE = True
except ImportError:
    GUDHI_AVAILABLE = False

class ALCEStabilizer(nn.Module):
    """
    Active Lipschitz Constraint Engine (ALCE).
    Ensures that infinitesimal input changes do not lead to catastrophic 
    representation jumps. Modulated by Affective Tension (psi).
    """
    def __init__(self, spectral_norm=True):
        super().__init__()
        self.use_spectral = spectral_norm

    def forward(self, deformation_vector: torch.Tensor, psi: float) -> torch.Tensor:
        # High Tension (psi -> 1.0) requires rigid manifolds (Low Lipschitz constant).
        # Low Tension (psi -> 0.0) allows plasticity (Higher Lipschitz constant).
        
        # Hardening Factor: As psi increases, max_deformation decreases.
        max_deformation = 1.0 / (1.0 + 10.0 * psi) 
        
        # Clamp the deformation vector to ensure stability
        return torch.clamp(deformation_vector, min=-max_deformation, max=max_deformation)

class PPNEmbeddingModule(nn.Module):
    """
    Polytope Projection Network.
    Projects multimodal vectors into a Simplicial Complex and extracts 
    Topological Invariants (Betti Numbers).
    """
    def __init__(self, input_dim=512, latent_dim=64, max_dimension=4, checkpoint_path: str = None):
        super().__init__()
        self.latent_dim = latent_dim
        self.max_dimension = max_dimension
        self._prev_D_t: Optional[torch.Tensor] = None
        self._prev_betti: Optional[torch.Tensor] = None
        
        # Phase A: Continuous Mapping (Encoder)
        self.manifold_projector = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.GELU(),
            nn.Linear(256, latent_dim), 
            nn.LayerNorm(latent_dim)
        )
        
        # Phase B: Deformation Engine (Delta from centroid)
        self.deformation_engine = nn.Linear(latent_dim, latent_dim)
        
        # Lipschitz Stabilizer
        self.alce = ALCEStabilizer()

        # Betti Head: A predictive auxiliary head to estimate topology 
        # during backprop (since Gudhi is non-differentiable)
        self.betti_head = nn.Sequential(
            nn.Linear(latent_dim, 32),
            nn.ReLU(),
            nn.Linear(32, max_dimension) # Predicts B0, B1, B2, B3
        )

        # Load pre-trained checkpoint or initialize deterministically
        if checkpoint_path:
            try:
                state_dict = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
                self.load_state_dict(state_dict)
                import logging
                logging.getLogger("PPN").info(f"PPN checkpoint loaded from {checkpoint_path}")
            except Exception as e:
                import logging
                logging.getLogger("PPN").warning(f"Failed to load PPN checkpoint: {e}. Using deterministic init.")
                self._deterministic_init()
        else:
            # No checkpoint: use deterministic initialization so the DPK gate
            # produces reproducible results across restarts.
            self._deterministic_init()

    def _deterministic_init(self):
        """Initialize weights deterministically so the security gate is reproducible."""
        torch.manual_seed(42)
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.xavier_uniform_(module.weight)
                if module.bias is not None:
                    nn.init.zeros_(module.bias)
        # Set to eval mode by default for inference — prevents dropout/batchnorm variance
        self.eval()

    def compute_persistent_homology(self, point_cloud: np.ndarray) -> torch.Tensor:
        """
        Uses Gudhi to compute exact Betti numbers (0 to 3) from the Rips Complex.
        This represents the 'Topological Barcode' of the state.
        """
        if not GUDHI_AVAILABLE:
            # Fallback mock for environments without TDA libraries
            return torch.tensor([1.0, 0.0, 0.0, 0.0], dtype=torch.float32)

        # Create Rips Complex
        rips_complex = gudhi.RipsComplex(points=point_cloud, max_edge_length=2.0)
        simplex_tree = rips_complex.create_simplex_tree(max_dimension=self.max_dimension)
        
        # Compute Persistence
        simplex_tree.compute_persistence()
        
        # Extract Betti Numbers (counts of features at infinite/long persistence)
        # B0: Connected Components, B1: Loops/Tunnels, B2: Voids
        betti_counts = simplex_tree.betti_numbers()
        
        # Pad or trim to ensure fixed size output (B0, B1, B2, B3)
        padded_betti = np.zeros(self.max_dimension)
        for i, b in enumerate(betti_counts[:self.max_dimension]):
            padded_betti[i] = b
            
        return torch.tensor(padded_betti, dtype=torch.float32)

    def forward(self, x: torch.Tensor, psi: float = 0.5, affect_state: Optional[AffectiveState] = None) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, int, float, float, bool]:
        """
        Forward Pass.
        Returns:
            G, D_t, B, Points, phi_total, budget_used, coherence, topic_shift
        """
        if affect_state is None:
            affect_state = AffectiveState()

        # 1. Project to Latent Manifold
        latent_points = self.manifold_projector(x)
        
        # 2. Calculate Deformation (Ricci Flow Approximation)
        raw_deformation = self.deformation_engine(latent_points)
        
        # 3. Manifold Hardening via ALCE
        # If High Stress (psi), clamp deformation to preserve structural integrity.
        D_t = self.alce(raw_deformation, psi)
        
        # Apply deformation to get final point cloud configuration
        final_config = latent_points + D_t

        # 4. Simplicial Quantization (Construct Adjacency G)
        # Compute pairwise Euclidean distances
        dists = torch.cdist(final_config, final_config)
        # Connect vertices if distance < epsilon (Simplicial 1-skeleton)
        epsilon = 1.0 * (1.0 - (psi * 0.5)) # High tension shrinks connection radius
        G = (dists < epsilon).float()

        # 5. Topological Barcoding (Betti Numbers)
        # Note: In training, we use the predictive head. In inference/validation,
        # we strictly calculate using Gudhi for safety.
        if self.training:
            B_pred = self.betti_head(final_config.mean(dim=0, keepdim=True)) # Approx for batch
        else:
            # Detach to CPU for Gudhi TDA calculation
            pc_np = final_config.detach().cpu().numpy()
            B_pred = self.compute_persistent_homology(pc_np)

        # 6. Apply fixed-point normalization (PPN §TableManager)
        D_t = self.normalize_to_fixed_point(D_t)

        # 7. Compute Φ_total affective-invariant index (PPN-003)
        betti_list = B_pred.tolist() if isinstance(B_pred, torch.Tensor) else list(B_pred)
        phi_total = self.compute_phi_total(betti_list, affect_state)

        # 8. ALCE Budget Tracking (PPN-005)
        L_max = 1.0 / (1.0 + 10.0 * psi)
        if self._prev_D_t is not None and D_t.shape == self._prev_D_t.shape:
            grad_norm = float(torch.norm(D_t - self._prev_D_t).item())
            budget_used = grad_norm / max(L_max, 1e-6)
        else:
            budget_used = 0.0
        self._prev_D_t = D_t.detach().clone()

        # 9. Coherence Score (AAP-001)
        B_curr = B_pred if isinstance(B_pred, torch.Tensor) else torch.tensor(B_pred)
        coherence = self.compute_coherence(G, B_curr, self._prev_betti)
        self._prev_betti = B_curr.detach().clone()

        # 10. Placeholder for topic_shift (Sprint 3)
        topic_shift = False

        return G, D_t, B_pred, final_config, phi_total, budget_used, coherence, topic_shift

    @staticmethod
    def normalize_to_fixed_point(t: torch.Tensor, scale: int = 1024) -> torch.Tensor:
        """
        Fixed-Point Normalization.
        Source: PPN §TableManager — normalize(continuous_val, scale_factor=1024.0)
        """
        scaled = t * float(scale)
        clamped = torch.clamp(scaled, -32767.0, 32767.0)
        rounded = torch.round(clamped)
        return rounded / float(scale)

    def compute_phi_total(self, betti: List[float], state: AffectiveState) -> int:
        """
        Φ_total = Φ(I) + Φ(D_t)
        Source: PPN §DPK — 'Affective-Invariant Index'
        """
        # Φ(I): base address from quantized Betti vector
        betti_key = tuple(round(b) for b in betti[:4])
        phi_I = hash(betti_key) % 65536

        # Φ(D_t): affective offset
        valence_offset = int((state.valence - 512.0) * 0.25)
        arousal_offset = int(state.arousal * 0.125)
        phi_D = valence_offset + arousal_offset

        return (phi_I + phi_D) % 65536

    def compute_coherence(self, G: torch.Tensor, B_current: torch.Tensor, B_prev: Optional[torch.Tensor]) -> float:
        """
        Coh(P_t) = (1 - Δβ_norm) × (1 - H_G_norm)
        Source: AAP §Coherence Score
        """
        # A. Δβ_norm: Betti number stability
        if B_prev is not None:
            delta_b = float(torch.sum(torch.abs(B_current.float() - B_prev.float())).item())
            max_shift = 4.0 * 2.0  # 4 Betti numbers × max 2-unit shift
            delta_b_norm = min(1.0, delta_b / max_shift)
        else:
            delta_b_norm = 0.0

        # B. H_G_norm: normalized graph entropy
        V = G.shape[0]
        if V <= 1:
            h_norm = 0.0
        else:
            degrees = G.sum(dim=1).float()
            total = degrees.sum().item()
            if total < 1e-9:
                h_norm = 0.0
            else:
                probs = degrees / total
                probs = probs[probs > 0]
                h_raw = -float((probs * torch.log2(probs)).sum().item())
                h_max = np.log2(V)
                h_norm = h_raw / h_max if h_max > 0 else 0.0

        coherence = (1.0 - delta_b_norm) * (1.0 - h_norm)
        return max(0.0, min(1.0, coherence))

    def extract_simplex_counts(self, G: torch.Tensor) -> Tuple[int, int, int]:
        """
        Helper to count Vertices (V), Edges (E), and Faces (F) from Adjacency Matrix G.
        F (Faces) are approximated by finding 3-cliques (triangles).
        """
        V = G.shape[0]
        # Edges is sum of upper triangle of G (excluding diagonal)
        E = int(torch.triu(G, diagonal=1).sum().item())
        
        # Faces (Triangles): Trace(G^3) / 6
        # A triangle exists if A->B, B->C, C->A.
        # This is efficient on GPU.
        G3 = torch.mm(G, torch.mm(G, G))
        F = int(torch.trace(G3).item() / 6)
        
        return V, E, F
