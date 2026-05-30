import os
import pytest
from sqlmodel import Session, select
from backend.security.audit_ledger import sync_audit_entry
from backend.models import AuditEntry, AuditLog
from backend.security.dpk import PolytopeState
from backend.database import engine as db_engine

@pytest.mark.asyncio
async def test_audit_log_persistence(temp_db):
    state = PolytopeState(
        signature_hash=123, vertices_V=10, edges_E=9, faces_F=0,
        betti=[1.0, 0.0, 0.0, 0.0], affective_tension_psi=0.1,
        phi_total=1, coherence=0.9, budget_used=0.1
    )
    
    import uuid
    from datetime import datetime, timezone
    entry = AuditEntry(
        timestamp=datetime.now(timezone.utc).isoformat(),
        id=str(uuid.uuid4()),
        event="TEST_EVENT",
        details={"objective": "test objective"},
        status="INFO"
    )
    
    topo = {
        "betti": state.betti,
        "phi_total": state.phi_total,
        "coherence": state.coherence,
        "psi": state.affective_tension_psi,
        "pvt": [10.0, 20.0, 30.0]
    }
    
    await sync_audit_entry(entry, topo=topo)
    
    with Session(temp_db) as session:
        stmt = select(AuditLog).where(AuditLog.event_id == entry.id)
        row = session.exec(stmt).first()
        assert row is not None
        assert row.event == "TEST_EVENT"
        assert "test objective" in row.details
        assert row.phi_total == 1.0
        assert row.coherence == 0.9
