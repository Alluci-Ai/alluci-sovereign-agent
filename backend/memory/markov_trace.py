"""
Markov Trace & Spectral Geometry Engine for H-LSM Memory.

Implements the formal mathematics of the Markov Trace Operator:
    Tr_A(P) = A + B(I - C)^(-1)D = A + \\sum_{k=0}^\\infty B C^k D

and the Scale-Dependent Spectral Dimension:
    d_s^A(\\sigma) = -2 d(log P_A(\\sigma)) / d(log \\sigma)
                  = 2 \\sigma \\frac{\\sum \\lambda_i e^{-\\sigma \\lambda_i}}{\\sum e^{-\\sigma \\lambda_i}}

where L_A is the normalized symmetrized Laplacian of the traced Markov chain.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from ..logging_config import get_logger

logger = get_logger("MarkovTrace")


class MarkovTraceEngine:
    """
    Computes exact Markov Trace reductions, hidden excursion series,
    and observer-relative spectral geometry over memory graph topologies.
    """

    def __init__(self, regularization_epsilon: float = 1e-7):
        self.eps = regularization_epsilon

    def compute_markov_trace(
        self,
        P: np.ndarray,
        visible_indices: List[int],
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Given a row-stochastic transition matrix P and a set of visible state indices A,
        computes the exact Markov Trace operator:
            Tr_A(P) = A + B(I - C)^(-1) D

        Returns:
            (P_A, excursion_term) where:
                P_A is the |A| x |A| reduced row-stochastic matrix,
                excursion_term is B(I - C)^(-1) D representing multi-hop hidden paths.
        """
        N = P.shape[0]
        if P.shape[0] != P.shape[1]:
            raise ValueError(f"Matrix P must be square, got shape {P.shape}")

        all_indices = set(range(N))
        visible_set = set(visible_indices)
        hidden_indices = sorted(list(all_indices - visible_set))
        vis_indices = sorted(list(visible_set))

        if not vis_indices:
            raise ValueError("Visible indices cannot be empty")

        # If all states are visible, the trace is P itself and excursions are zero
        if not hidden_indices:
            return P[np.ix_(vis_indices, vis_indices)].copy(), np.zeros((len(vis_indices), len(vis_indices)))

        # Partition matrix P into sub-blocks:
        # A: visible -> visible
        # B: visible -> hidden
        # D: hidden -> visible
        # C: hidden -> hidden
        A = P[np.ix_(vis_indices, vis_indices)]
        B = P[np.ix_(vis_indices, hidden_indices)]
        D = P[np.ix_(hidden_indices, vis_indices)]
        C = P[np.ix_(hidden_indices, hidden_indices)]

        num_hidden = len(hidden_indices)
        I_hidden = np.eye(num_hidden)

        # Solve (I - C) with Tikhonov regularization to ensure stability even near absorbing boundaries
        M = I_hidden - C + self.eps * I_hidden
        try:
            inv_M = np.linalg.inv(M)
        except np.linalg.LinAlgError:
            inv_M = np.linalg.pinv(M)

        excursion_term = B @ inv_M @ D
        P_A = A + excursion_term

        # Re-normalize rows to ensure strict row-stochastic property (sum to 1)
        row_sums = P_A.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1.0
        P_A = P_A / row_sums

        return P_A, excursion_term

    def compute_spectral_geometry(
        self,
        P_A: np.ndarray,
        diffusion_scale: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Constructs the symmetrized normalized Laplacian L_A and derives:
        1. Eigenvalues \\lambda_i
        2. Fiedler value \\lambda_2 (algebraic connectivity / mixing rate)
        3. Heat return probability P_A(\\sigma)
        4. Scale-dependent spectral dimension d_s^A(\\sigma)
        """
        n = P_A.shape[0]
        if n == 0:
            return {
                "eigenvalues": [],
                "fiedler_value": 0.0,
                "heat_return_prob": 1.0,
                "spectral_dimension": 0.0,
                "mixing_rate": "disconnected",
            }

        if n == 1:
            return {
                "eigenvalues": [0.0],
                "fiedler_value": 0.0,
                "heat_return_prob": 1.0,
                "spectral_dimension": 0.0,
                "mixing_rate": "singleton",
            }

        # Symmetrized transition matrix W = 0.5 * (P_A + P_A.T)
        W = 0.5 * (P_A + P_A.T)

        # Degree matrix D
        d = W.sum(axis=1)
        d_inv_sqrt = np.zeros(n)
        for i in range(n):
            if d[i] > 1e-12:
                d_inv_sqrt[i] = 1.0 / np.sqrt(d[i])
            else:
                d_inv_sqrt[i] = 0.0

        D_inv_sqrt = np.diag(d_inv_sqrt)

        # Normalized Laplacian L_A = I - D^(-1/2) W D^(-1/2)
        L_A = np.eye(n) - D_inv_sqrt @ W @ D_inv_sqrt

        # Eigenvalues in ascending order
        eigenvalues = np.linalg.eigvalsh(L_A)
        eigenvalues = np.maximum(0.0, eigenvalues)  # Guard against float rounding below 0.0

        # Fiedler eigenvalue (second smallest)
        fiedler = float(eigenvalues[1]) if n > 1 else 0.0

        # Heat return probability: P_A(\\sigma) = (1/|A|) * \\sum e^{-\\sigma \\lambda_i}
        sigma = max(1e-4, float(diffusion_scale))
        exp_terms = np.exp(-sigma * eigenvalues)
        heat_return_prob = float(np.mean(exp_terms))

        # Scale-dependent Spectral Dimension: d_s^A(\\sigma) = 2 \\sigma * (\\sum \\lambda_i e^{-\\sigma \\lambda_i}) / (\\sum e^{-\\sigma \\lambda_i})
        numerator = np.sum(eigenvalues * exp_terms)
        denominator = np.sum(exp_terms)

        if denominator > 1e-12:
            spectral_dim = float(2.0 * sigma * (numerator / denominator))
        else:
            spectral_dim = 0.0

        # Classify mixing regime
        if fiedler > 0.6:
            mixing_rate = "rapid"
        elif fiedler > 0.1:
            mixing_rate = "nominal"
        else:
            mixing_rate = "sparse"

        return {
            "eigenvalues": [float(x) for x in eigenvalues],
            "fiedler_value": fiedler,
            "heat_return_prob": heat_return_prob,
            "spectral_dimension": spectral_dim,
            "mixing_rate": mixing_rate,
        }

    def build_affinity_matrix(
        self,
        embeddings: np.ndarray,
        lexical_overlaps: Optional[np.ndarray] = None,
        temperature: float = 0.2,
    ) -> np.ndarray:
        """
        Builds a normalized row-stochastic transition matrix P from embedding vectors
        and optional lexical/graph co-occurrence scores.
        """
        n = embeddings.shape[0]
        if n == 0:
            return np.empty((0, 0))
        if n == 1:
            return np.ones((1, 1))

        # Normalize embeddings to unit norm for cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = embeddings / norms

        sim_matrix = normalized @ normalized.T  # Cosine similarities in [-1, 1]

        # Fold in lexical overlap if provided
        if lexical_overlaps is not None and lexical_overlaps.shape == (n, n):
            sim_matrix = 0.7 * sim_matrix + 0.3 * lexical_overlaps

        # Softmax with temperature scaling for row-stochastic conversion
        scaled = sim_matrix / max(1e-3, temperature)
        # Shift max for numerical stability
        shifted = scaled - np.max(scaled, axis=1, keepdims=True)
        exp_matrix = np.exp(shifted)
        P = exp_matrix / exp_matrix.sum(axis=1, keepdims=True)

        return P

    def rescore_with_markov_trace(
        self,
        candidate_items: List[Any],
        embeddings: np.ndarray,
        direct_relevance_scores: List[float],
        visible_top_k: int = 5,
        diffusion_scale: float = 1.0,
    ) -> Tuple[List[Tuple[Any, float]], Dict[str, Any]]:
        """
        Performs full Markov Trace rescoring:
        1. Partitions candidate items into visible set A (top direct relevance) and hidden set C (remainder).
        2. Constructs full affinity matrix P.
        3. Computes Tr_A(P) = A + B(I - C)^(-1) D to uncover hidden-excursion couplings.
        4. Adjusts scores based on multi-hop excursion density and spectral dimension.
        """
        num_candidates = len(candidate_items)
        if num_candidates == 0:
            return [], {"spectral_dimension": 0.0, "fiedler_value": 0.0, "mixing_rate": "empty"}

        if num_candidates <= 2:
            results = [(candidate_items[i], float(direct_relevance_scores[i])) for i in range(num_candidates)]
            return results, {"spectral_dimension": 1.0, "fiedler_value": 1.0, "mixing_rate": "minimal"}

        # 1. Determine visible partition A and hidden partition C
        k = max(1, min(visible_top_k, num_candidates - 1))
        # Visible indices are top-k by direct relevance
        sorted_indices = np.argsort(direct_relevance_scores)[::-1]
        visible_indices = sorted_indices[:k].tolist()
        hidden_indices = sorted_indices[k:].tolist()

        # 2. Construct row-stochastic transition matrix
        P = self.build_affinity_matrix(embeddings)

        # 3. Compute Markov Trace
        P_A, excursions = self.compute_markov_trace(P, visible_indices)

        # 4. Derive Spectral Geometry
        spectral_metrics = self.compute_spectral_geometry(P_A, diffusion_scale=diffusion_scale)

        # 5. Rescore visible items combining direct score + excursion influx
        # Excursion influx for visible node i: sum of multi-hop probabilities arriving at i
        excursion_boost = excursions.sum(axis=0)  # column sum represents incoming hidden flux
        max_boost = float(np.max(excursion_boost)) if len(excursion_boost) > 0 and np.max(excursion_boost) > 0 else 1.0

        rescored_items: List[Tuple[Any, float]] = []

        # Add visible items with trace-boosted scores
        for idx_in_vis, orig_idx in enumerate(sorted(visible_indices)):
            base_score = float(direct_relevance_scores[orig_idx])
            boost = float(excursion_boost[idx_in_vis]) / max_boost
            # 80% direct score + 20% topological excursion boost
            final_score = 0.8 * base_score + 0.2 * boost
            rescored_items.append((candidate_items[orig_idx], final_score))

        # Also evaluate hidden candidates to see if any have extraordinarily high excursion coupling
        # D @ inv_M @ B represents hidden-to-hidden-to-visible bridging importance
        for orig_idx in hidden_indices:
            base_score = float(direct_relevance_scores[orig_idx])
            # Direct coupling from this hidden node to all visible nodes
            coupling_to_visible = float(P[orig_idx, sorted(visible_indices)].sum())
            if coupling_to_visible > 0.4:
                # Promote hidden bridge node
                rescored_items.append((candidate_items[orig_idx], base_score * (1.0 + coupling_to_visible * 0.3)))

        # Sort all rescored items in descending order of relevance
        rescored_items.sort(key=lambda x: x[1], reverse=True)
        return rescored_items, spectral_metrics
