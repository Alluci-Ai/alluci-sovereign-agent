import os
from backend.security.audit_log import TopologicalAuditLog
from backend.security.dpk import PolytopeState

def test_audit_log_persistence(tmp_path):
    log_dir = tmp_path / "topo_logs"
    logger = TopologicalAuditLog(log_dir=str(log_dir))
    
    state = PolytopeState(
        signature_hash=123, vertices_V=10, edges_E=9, faces_F=0,
        betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.1,
        phi_total=1, coherence=0.9, budget_used=0.1
    )
    
    logger.log_entry("test objective", state, "action results")
    
    # Check if file exists and has content
    files = list(log_dir.glob("*.jsonl"))
    assert len(files) == 1
    with open(files[0], "r") as f:
        content = f.read()
        assert "test objective" in content
        assert "0x7b" in content
