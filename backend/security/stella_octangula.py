"""
Stella Octangula S8 Geometric & Simplicial Chain Complex Engine.
================================================================
Implements Donald Hoffman & Chetan Prakash's Conscious Agent Formalism
on discrete silicon geometry via:
1. Stella Octangula S8 (Compound of two dual regular tetrahedra T+ and T-)
2. Simplicial Boundary Operators ∂k (C2 -> C1 -> C0) with exact nilpotence ∂1 ∘ ∂2 = 0
3. Idempotent Fusion Simplex Operator F_n^1 satisfying Π ∘ Π = Π
4. Entropic Arrow of Time Monotonicity H(X_n | X_1) >= H(X_{n-1} | X_1)
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional


class StellaOctangulaGeometry:
    """
    Mathematical Representation of Kepler's Stella Octangula S8.
    
    Structure:
      - T+ (Positive Tetrahedron): 4 vertices
      - T- (Negative Tetrahedron): 4 vertices
      - O6 (Central Octahedron Intersection): 6 vertices
      - Total Compound Vertices: V = 8
      - 1-Skeleton Edges: E = 12
      - 2-Skeleton Faces: F = 8
      - Euler Characteristic: chi = V - E + F = 8 - 12 + 8 = 4 (compound) or 2 (topological 2-sphere boundary)
    """

    def __init__(self):
        # 1. 8 Primary Vertices in R^3
        # T+ (Tetrahedron A)
        self.vertices_T_plus = np.array([
            [ 1.0,  1.0,  1.0],  # V0
            [ 1.0, -1.0, -1.0],  # V1
            [-1.0,  1.0, -1.0],  # V2
            [-1.0, -1.0,  1.0],  # V3
        ], dtype=np.float64)

        # T- (Tetrahedron B, dual)
        self.vertices_T_minus = np.array([
            [-1.0, -1.0, -1.0],  # V4
            [-1.0,  1.0,  1.0],  # V5
            [ 1.0, -1.0,  1.0],  # V6
            [ 1.0,  1.0, -1.0],  # V7
        ], dtype=np.float64)

        # Combined 8 vertices
        self.vertices = np.vstack([self.vertices_T_plus, self.vertices_T_minus])

        # 2. Central Octahedron Intersection Vertices O6
        self.octahedron_vertices = np.array([
            [ 0.5,  0.0,  0.0],
            [-0.5,  0.0,  0.0],
            [ 0.0,  0.5,  0.0],
            [ 0.0, -0.5,  0.0],
            [ 0.0,  0.0,  0.5],
            [ 0.0,  0.0, -0.5],
        ], dtype=np.float64)

        # 3. 12 Edges for the dual tetrahedra (6 for T+, 6 for T-)
        # Oriented edges: (source, target)
        self.edges = [
            # T+ Edges (e0 .. e5)
            (0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3),
            # T- Edges (e6 .. e11)
            (4, 5), (4, 6), (4, 7), (5, 6), (5, 7), (6, 7)
        ]

        # 4. 8 Triangular Faces (4 for T+, 4 for T-)
        # Oriented faces: (v0, v1, v2)
        self.faces = [
            # T+ Faces (f0 .. f3)
            (0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2),
            # T- Faces (f4 .. f7)
            (4, 6, 5), (4, 7, 6), (4, 5, 7), (5, 6, 7)
        ]

        # 5. Build Simplicial Boundary Matrices
        self.B1, self.B2 = self._build_boundary_matrices()

    def _build_boundary_matrices(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Constructs the boundary matrices B1 and B2 for the chain complex:
            C2 (Faces, dim 8) --∂2--> C1 (Edges, dim 12) --∂1--> C0 (Vertices, dim 8)
        
        ∂1([v_i, v_j]) = [v_j] - [v_i]
        ∂2([v_i, v_j, v_k]) = [v_j, v_k] - [v_i, v_k] + [v_i, v_j]
        """
        num_v = len(self.vertices)
        num_e = len(self.edges)
        num_f = len(self.faces)

        # B1: (num_v x num_e) -> maps C1 to C0
        B1 = np.zeros((num_v, num_e), dtype=np.float64)
        edge_map: Dict[Tuple[int, int], Tuple[int, int]] = {}

        for edge_idx, (src, tgt) in enumerate(self.edges):
            B1[src, edge_idx] = -1.0
            B1[tgt, edge_idx] = 1.0
            edge_map[(src, tgt)] = (edge_idx, 1)   # forward orientation
            edge_map[(tgt, src)] = (edge_idx, -1)  # reverse orientation

        # B2: (num_e x num_f) -> maps C2 to C1
        B2 = np.zeros((num_e, num_f), dtype=np.float64)
        for face_idx, (v0, v1, v2) in enumerate(self.faces):
            # Face boundary: +[v1, v2] - [v0, v2] + [v0, v1]
            face_edges = [(v1, v2, 1.0), (v0, v2, -1.0), (v0, v1, 1.0)]
            for src, tgt, sign in face_edges:
                if (src, tgt) in edge_map:
                    e_idx, orient = edge_map[(src, tgt)]
                    B2[e_idx, face_idx] += sign * orient

        return B1, B2

    def verify_boundary_nilpotence(self) -> bool:
        """
        Fundamental Theorem of Algebraic Topology: ∂1 ∘ ∂2 = 0.
        Verifies that B1 @ B2 is exactly the zero matrix.
        """
        product = self.B1 @ self.B2
        return bool(np.allclose(product, 0.0, atol=1e-10))

    def compute_betti_numbers(self) -> List[float]:
        """
        Computes formal Betti numbers [β₀, β₁, β₂, β₃] using rank-nullity theorem:
            β_k = dim(ker ∂_k) - dim(im ∂_{k+1})
        """
        rank_B1 = np.linalg.matrix_rank(self.B1)
        rank_B2 = np.linalg.matrix_rank(self.B2)

        dim_C0 = len(self.vertices)
        dim_C1 = len(self.edges)
        dim_C2 = len(self.faces)

        # β₀ = dim(C0) - rank(B1)
        b0 = float(dim_C0 - rank_B1)

        # β₁ = dim(ker B1) - rank(B2) = (dim(C1) - rank(B1)) - rank(B2)
        b1 = float(dim_C1 - rank_B1 - rank_B2)

        # β₂ = dim(ker B2) = dim(C2) - rank(B2)
        b2 = float(dim_C2 - rank_B2)

        b3 = 0.0
        return [b0, b1, b2, b3]

    def get_euler_characteristic(self) -> int:
        """
        Computes Euler characteristic χ = V - E + F.
        """
        return len(self.vertices) - len(self.edges) + len(self.faces)

    def project_to_simplex(self, x: np.ndarray) -> np.ndarray:
        """
        [ F_n^1 ] Idempotent Fusion Simplex Operator.
        Projects an arbitrary vector x ∈ R^d onto the convex hull of the Stella Octangula S8.
        
        Guarantees:
          1. Point lies strictly in the convex hull of the 8 vertices: x_i ∈ [-1.0, 1.0].
          2. Exact Idempotence: Π(Π(x)) = Π(x) identically.
        """
        x_flat = np.asarray(x, dtype=np.float64).flatten()
        if len(x_flat) != 3:
            if len(x_flat) < 3:
                x_3d = np.pad(x_flat, (0, 3 - len(x_flat)))
            else:
                x_3d = np.array([
                    float(np.mean(x_flat[0::3])),
                    float(np.mean(x_flat[1::3])),
                    float(np.mean(x_flat[2::3]))
                ], dtype=np.float64)
        else:
            x_3d = x_flat

        # Convex hull of { (±1, ±1, ±1) } is the unit cube [-1, 1]^3
        projected = np.clip(x_3d, -1.0, 1.0)
        return projected

    def verify_idempotence(self, x: np.ndarray, atol: float = 1e-5) -> bool:
        """
        Verifies the Idempotent Fusion condition: Π(Π(x)) = Π(x).
        """
        p1 = self.project_to_simplex(x)
        p2 = self.project_to_simplex(p1)
        return bool(np.allclose(p1, p2, atol=atol))

    def get_support_point(self, direction: np.ndarray) -> np.ndarray:
        """
        [ GJK Support Function S_{S8}(d) ]
        Returns the vertex v ∈ V(S8) that maximizes the dot product (v · d).
        """
        d = np.asarray(direction, dtype=np.float64).flatten()
        if len(d) != 3:
            if len(d) < 3:
                d_3d = np.pad(d, (0, 3 - len(d)))
            else:
                d_3d = np.array([
                    float(np.mean(d[0::3])),
                    float(np.mean(d[1::3])),
                    float(np.mean(d[2::3]))
                ], dtype=np.float64)
        else:
            d_3d = d
            
        dots = self.vertices @ d_3d  # (8,)
        max_idx = int(np.argmax(dots))
        return self.vertices[max_idx].copy()

    def compute_gjk_distance(self, point: np.ndarray) -> Tuple[float, np.ndarray]:
        """
        [ GJK Convex Polytope Distance & Projection ]
        Computes the Euclidean distance d(p, S8) from an arbitrary point p to the 
        convex hull of the Stella Octangula S8, and returns (distance, projected_boundary_point).
        
        If point is strictly inside Conv(S8), distance is 0.0.
        If point is outside, distance > 0.0 and projected_boundary_point is the nearest point on the hull.
        """
        p_flat = np.asarray(point, dtype=np.float64).flatten()
        if len(p_flat) != 3:
            if len(p_flat) < 3:
                p_3d = np.pad(p_flat, (0, 3 - len(p_flat)))
            else:
                p_3d = np.array([
                    float(np.mean(p_flat[0::3])),
                    float(np.mean(p_flat[1::3])),
                    float(np.mean(p_flat[2::3]))
                ], dtype=np.float64)
        else:
            p_3d = p_flat

        # Convex hull of S8 is the cube [-1, 1]^3
        projected = np.clip(p_3d, -1.0, 1.0)
        distance = float(np.linalg.norm(p_3d - projected))
        return distance, projected

    def compute_conditional_entropy(self, p_xn_given_x1: np.ndarray) -> float:
        """
        Computes conditional Shannon entropy H(X_n | X_1) = - sum p log p.
        """
        p_clean = np.clip(p_xn_given_x1, 1e-12, 1.0)
        # Normalize to probability distribution
        p_norm = p_clean / np.sum(p_clean)
        return float(-np.sum(p_norm * np.log2(p_norm)))

    def verify_entropic_arrow_of_time(self, state_distributions: List[np.ndarray]) -> bool:
        """
        [ Entropic Arrow of Time ]
        Verifies that conditional entropy is non-decreasing across a state sequence:
            H(X_n | X_1) >= H(X_{n-1} | X_1) - epsilon
        """
        if len(state_distributions) < 2:
            return True

        entropies = [self.compute_conditional_entropy(dist) for dist in state_distributions]
        for i in range(1, len(entropies)):
            # Allow small numerical epsilon
            if entropies[i] < entropies[i-1] - 1e-4:
                return False
        return True
