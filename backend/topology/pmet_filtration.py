"""
P-MET Topological Ingestion & Simplicial Filtration Engine
==========================================================
Realizes the Perceive Operator (P : W x X -> [0,1]) by sampling raw world data (W),
constructing Vietoris-Rips simplicial complexes, and computing topological Betti invariants.
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple


@dataclass
class SimplicialComplexSummary:
    vertices_count: int
    edges_count: int
    faces_count: int
    euler_characteristic: int
    betti_numbers: List[float]       # [beta_0, beta_1, beta_2, beta_3]
    filtration_epsilon: float
    is_nilpotent: bool               # True if partial_1 o partial_2 == 0
    connected_components: int
    has_circular_dependencies: bool  # True if beta_1 > 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class PMETFiltrationEngine:
    """
    Perception Manifold Evaluation Topology (P-MET) Ingestion Engine.
    Transforms raw multi-dimensional vectors and graph topologies from W
    into bounded simplicial complex invariants X.
    """

    def __init__(self, default_epsilon: float = 0.5, max_dimension: int = 2):
        self.default_epsilon = default_epsilon
        self.max_dimension = max_dimension

    def compute_distance_matrix(self, point_cloud: np.ndarray) -> np.ndarray:
        """Computes pairwise Euclidean distance matrix for a point cloud."""
        if point_cloud.ndim == 1:
            point_cloud = point_cloud.reshape(-1, 1)
        
        diff = point_cloud[:, np.newaxis, :] - point_cloud[np.newaxis, :, :]
        return np.sqrt(np.sum(diff ** 2, axis=-1))

    def build_vietoris_rips_complex(
        self,
        point_cloud: np.ndarray,
        epsilon: Optional[float] = None
    ) -> SimplicialComplexSummary:
        """
        Constructs the Vietoris-Rips simplicial complex up to 2-skeleton (faces)
        at scale radius epsilon and computes homological invariants.
        """
        eps = epsilon if epsilon is not None else self.default_epsilon
        n_points = point_cloud.shape[0]

        if n_points == 0:
            return SimplicialComplexSummary(
                vertices_count=0,
                edges_count=0,
                faces_count=0,
                euler_characteristic=0,
                betti_numbers=[0.0, 0.0, 0.0, 0.0],
                filtration_epsilon=eps,
                is_nilpotent=True,
                connected_components=0,
                has_circular_dependencies=False,
            )

        if n_points == 1:
            return SimplicialComplexSummary(
                vertices_count=1,
                edges_count=0,
                faces_count=0,
                euler_characteristic=1,
                betti_numbers=[1.0, 0.0, 0.0, 0.0],
                filtration_epsilon=eps,
                is_nilpotent=True,
                connected_components=1,
                has_circular_dependencies=False,
            )

        dist_matrix = self.compute_distance_matrix(point_cloud)

        # 1-skeleton: Edges (i < j with dist <= eps)
        edges: List[Tuple[int, int]] = []
        for i in range(n_points):
            for j in range(i + 1, n_points):
                if dist_matrix[i, j] <= eps:
                    edges.append((i, j))

        edge_set = set(edges)

        # 2-skeleton: Triangular Faces (i < j < k where all 3 pairs in edge_set)
        faces: List[Tuple[int, int, int]] = []
        for idx_e, (i, j) in enumerate(edges):
            for k in range(j + 1, n_points):
                if (i, k) in edge_set and (j, k) in edge_set:
                    faces.append((i, j, k))

        V = n_points
        E = len(edges)
        F = len(faces)
        euler = V - E + F

        # Simplicial Boundary Operator Nilpotence check (B_1 @ B_2 = 0)
        is_nilpotent = self._verify_boundary_nilpotence(edges, faces, V)

        # Approximate Betti numbers
        # beta_0 = Connected components
        adj = np.zeros((V, V), dtype=bool)
        for (i, j) in edges:
            adj[i, j] = True
            adj[j, i] = True
        
        visited = np.zeros(V, dtype=bool)
        components = 0
        for start_node in range(V):
            if not visited[start_node]:
                components += 1
                queue = [start_node]
                visited[start_node] = True
                while queue:
                    curr = queue.pop()
                    neighbors = np.where(adj[curr])[0]
                    for nbr in neighbors:
                        if not visited[nbr]:
                            visited[nbr] = True
                            queue.append(nbr)

        beta_0 = float(components)
        # beta_1 approx via Euler-Poincare: chi = beta_0 - beta_1 + beta_2
        # beta_1 = beta_0 - chi + beta_2 (assuming beta_2 ~ 0 for general sparse 2-complex)
        beta_1 = max(0.0, float(E - V + components - F))
        beta_2 = max(0.0, float(F - (E - V + components))) if F > (E - V + components) else 0.0
        beta_3 = 0.0

        return SimplicialComplexSummary(
            vertices_count=V,
            edges_count=E,
            faces_count=F,
            euler_characteristic=euler,
            betti_numbers=[beta_0, beta_1, beta_2, beta_3],
            filtration_epsilon=eps,
            is_nilpotent=is_nilpotent,
            connected_components=components,
            has_circular_dependencies=(beta_1 > 0.0),
        )

    def filter_ast_graph(
        self,
        nodes: List[str],
        edges: List[Tuple[str, str]],
        epsilon: float = 1.0
    ) -> SimplicialComplexSummary:
        """
        Builds a Vietoris-Rips topological summary from an AST dependency graph.
        Assigns spatial embeddings based on graph degree and connectivity.
        """
        if not nodes:
            return self.build_vietoris_rips_complex(np.empty((0, 3)), epsilon)

        node_map = {name: idx for idx, name in enumerate(nodes)}
        n = len(nodes)
        
        # Build 3D pseudo-embedding for nodes based on in/out degree & depth
        in_degree = np.zeros(n)
        out_degree = np.zeros(n)
        
        valid_edges = []
        for src, dst in edges:
            if src in node_map and dst in node_map:
                u, v = node_map[src], node_map[dst]
                out_degree[u] += 1
                in_degree[v] += 1
                valid_edges.append((u, v))

        # Coordinates: [normalized in_degree, normalized out_degree, relative index position]
        coords = np.zeros((n, 3))
        max_in = max(1.0, float(np.max(in_degree)))
        max_out = max(1.0, float(np.max(out_degree)))
        for idx in range(n):
            coords[idx, 0] = in_degree[idx] / max_in
            coords[idx, 1] = out_degree[idx] / max_out
            coords[idx, 2] = idx / max(1.0, float(n - 1))

        return self.build_vietoris_rips_complex(coords, epsilon=epsilon)

    def _verify_boundary_nilpotence(
        self,
        edges: List[Tuple[int, int]],
        faces: List[Tuple[int, int, int]],
        n_vertices: int
    ) -> bool:
        """Verifies that the algebraic boundary composition satisfies partial_1 o partial_2 == 0."""
        if not faces or not edges:
            return True

        # B_1: |V| x |E|
        # B_2: |E| x |F|
        edge_to_idx = {e: idx for idx, e in enumerate(edges)}
        
        # Construct oriented boundary matrices
        B1 = np.zeros((n_vertices, len(edges)), dtype=np.int8)
        for idx, (u, v) in enumerate(edges):
            B1[u, idx] = -1
            B1[v, idx] = 1

        B2 = np.zeros((len(edges), len(faces)), dtype=np.int8)
        for f_idx, (i, j, k) in enumerate(faces):
            # Face boundary: + [j, k] - [i, k] + [i, j]
            if (j, k) in edge_to_idx:
                B2[edge_to_idx[(j, k)], f_idx] += 1
            if (i, k) in edge_to_idx:
                B2[edge_to_idx[(i, k)], f_idx] -= 1
            if (i, j) in edge_to_idx:
                B2[edge_to_idx[(i, j)], f_idx] += 1

        product = B1 @ B2
        return bool(np.all(product == 0))
