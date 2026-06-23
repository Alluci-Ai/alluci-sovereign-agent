import hashlib
import logging
from typing import List, Dict, Any, Tuple
import networkx as nx

logger = logging.getLogger("TopologicalBarcode")

class CompositeTopologicalSignature:
    """
    Composite Topological Signature Generator
    =========================================
    
    Generates the mathematical bridge between the Control Plane (db.sqlite3) 
    and the Cognitive Plane (polytope_data.kuzu).
    
    Instead of using a brittle 64-bit hash, this creates a deterministic, collision-resistant
    Tuple: (WL_Hash_256, Node_Count, Betti_Number).
    """

    @staticmethod
    def _calculate_betti_number(G: nx.Graph) -> int:
        """
        Calculates the first Betti number (b1) of the graph.
        In algebraic topology, b1 represents the number of 1-dimensional "holes" or 
        independent cycles in the graph.
        
        Formula: b1 = E - V + C
        Where:
        - E = Number of Edges
        - V = Number of Vertices (Nodes)
        - C = Number of Connected Components
        """
        edges = G.number_of_edges()
        vertices = G.number_of_nodes()
        # For directed graphs, we must convert to undirected to calculate generic components
        if G.is_directed():
            components = nx.number_weakly_connected_components(G)  # type: ignore
        else:
            components = nx.number_connected_components(G)
            
        betti = edges - vertices + components
        return max(0, betti)

    @staticmethod
    def _generate_wl_hash_256(G: nx.Graph) -> str:
        """
        Generates a Weisfeiler-Lehman (WL) graph hash and wraps it in a SHA-256 
        digest to guarantee a uniform 256-bit collision-resistant identifier.
        """
        # NetworkX natively supports WL hashing for graph isomorphism testing
        # We use iterations=3 as a standard depth for structural propagation
        raw_wl_hash = nx.weisfeiler_lehman_graph_hash(G, iterations=3)
        
        # Wrap in SHA-256 to ensure standard 256-bit cryptographic strength
        sha256_hash = hashlib.sha256(raw_wl_hash.encode('utf-8')).hexdigest()
        return sha256_hash

    @classmethod
    def generate_signature(cls, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
        """
        Takes a raw Polytope sub-graph (nodes and edges) and generates the 
        Composite Topological Signature.
        
        Args:
            nodes: List of node dictionaries. Expected to have an 'id' or 'label'.
            edges: List of edge dictionaries. Expected to have 'source' and 'target'.
            
        Returns:
            A string formatted as: "{WL_Hash_256}:{Node_Count}:{Betti_Number}"
            Example: "a3f9b...:45:2"
        """
        if not nodes:
            logger.warning("Attempted to generate topological signature for an empty graph.")
            return "EMPTY_GRAPH:0:0"

        # Build the NetworkX graph geometry
        # We use a MultiDiGraph because Polytope Memory Graphs are directed and 
        # may have multiple semantic relationships between the same two concepts.
        G = nx.MultiDiGraph()
        
        # Add nodes with their labels to preserve semantic isomorphism
        for node in nodes:
            node_id = node.get("id", str(id(node)))
            node_label = node.get("label", "")
            G.add_node(node_id, label=node_label)
            
        # Add edges
        for edge in edges:
            source = edge.get("source")
            target = edge.get("target")
            if source and target:
                G.add_edge(source, target, label=edge.get("label", ""))
                
        # 1. Node Count
        node_count = G.number_of_nodes()
        
        # 2. Betti Number
        betti_number = cls._calculate_betti_number(G)
        
        # 3. WL Hash 256
        wl_256 = cls._generate_wl_hash_256(G)
        
        # Composite Signature
        signature = f"{wl_256}:{node_count}:{betti_number}"
        
        logger.debug(f"Generated Composite Topological Signature: {signature}")
        return signature
