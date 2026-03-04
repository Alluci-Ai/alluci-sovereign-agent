
import torch
import torch.nn as nn
import numpy as np
from typing import Tuple

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

    def forward(self, x: torch.Tensor, psi: float = 0.5) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward Pass.
        Args:
            x: Multimodal Input Tensor [Batch, Input_Dim]
            psi: Affective Tension (0.0 to 1.0)
        Returns:
            G: Adjacency Matrix (Simplicial 1-skeleton)
            D_t: Deformation Vector (Stabilized)
            B: Betti Numbers (Topological Signature)
            Points: Final configuration points
        """
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

        return G, D_t, B_pred, final_config

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
