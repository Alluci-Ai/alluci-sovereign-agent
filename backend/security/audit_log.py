import json
import hashlib
import os
import time
from typing import List, Dict, Any, Optional
from .dpk import PolytopeState

class TopologicalAuditLog:
    """
    Topological Barcode Audit Log.
    Source: AAP §Audit — audit_logger.cpp::log_barcode()

    Persists the 'Topological Signature' of every sovereign action.
    Enables post-hoc verification of agent alignment.

    Each entry includes a Merkle attribution hash H_P for forensic
    reconstruction: H_P = SHA256(P_t, ψ, g_final, VerusID).
    """
    def __init__(self, log_dir: str = "logs/topology"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, f"audit_{int(time.time())}.jsonl")
        self._prev_hash: str = "0" * 64  # Genesis hash

    def compute_merkle_hash(self, state: PolytopeState, action_summary: str,
                            verus_id: str = "polytope.local",
                            pvt: Optional[Dict[str, float]] = None) -> str:
        """
        Merkle Attribution Hash.
        H_P = SHA256(P_t || ψ || g_final || VerusID || prev_hash || PVT)

        Ensures the agent's actions are forensically traceable and
        form an immutable chain.
        """
        payload_parts = [
            json.dumps(state.betti, sort_keys=True),
            str(state.affective_tension_psi),
            action_summary[:256],  # Truncate for hash consistency
            verus_id,
            self._prev_hash,
            str(state.phi_total),
        ]
        if pvt:
            payload_parts.append(json.dumps(pvt, sort_keys=True))
        
        payload = "|".join(payload_parts)
        h = hashlib.sha256(payload.encode()).hexdigest()
        return h

    def log_entry(self, objective: str, state: PolytopeState, action_summary: str,
                  pvt: Optional[Dict[str, float]] = None):
        """
        Writes a JSONL entry with the topological barcode and Merkle hash.
        """
        # Compute Merkle attribution hash
        h_p = self.compute_merkle_hash(state, action_summary, pvt=pvt)

        entry = {
            "timestamp": time.time(),
            "objective": objective,
            "action": action_summary,
            "barcode": {
                "betti": state.betti,
                "phi_total": state.phi_total,
                "chi": state.vertices_V - state.edges_E + state.faces_F,
                "signature": hex(state.signature_hash)
            },
            "metrics": {
                "coherence": state.coherence,
                "psi": state.affective_tension_psi,
                "budget": state.budget_used
            },
            "pvt": pvt or {},
            "merkle": {
                "H_P": h_p,
                "prev_hash": self._prev_hash
            }
        }
        
        # Update chain
        self._prev_hash = h_p
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_latest_signatures(self, count: int = 10) -> List[Dict[str, Any]]:
        """Retrieves recent entries for verification seeds."""
        entries = []
        try:
            with open(self.log_file, "r") as f:
                lines = f.readlines()
                for line in lines[-count:]:
                    entries.append(json.loads(line.strip()))
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        return entries
