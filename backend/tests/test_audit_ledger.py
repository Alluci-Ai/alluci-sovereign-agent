import pytest
import asyncio
import json
import hashlib
from datetime import datetime, timezone
from sqlmodel import Session, select, SQLModel
from unittest.mock import AsyncMock, patch, MagicMock

from backend.database import engine as db_engine
from backend.models import AuditLog, AuditEntry
from backend.security.audit_ledger import sync_audit_entry, anchor_audit_batch
from backend.security.audit_verifier import AuditVerifier

@pytest.fixture(autouse=True)
def setup_teardown():
    # Setup: Create tables in the in-memory SQLite (if not already)
    SQLModel.metadata.create_all(db_engine)
    # Clear audit_log table before each test
    with Session(db_engine) as session:
        session.exec(select(AuditLog)).all()
        for log in session.exec(select(AuditLog)).all():
            session.delete(log)
        session.commit()
    yield

@pytest.mark.asyncio
async def test_sync_audit_entry():
    entry = AuditEntry(
        id="test-event-1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        event="test.event",
        details="test detail",
        status="INFO"
    )
    result = await sync_audit_entry(entry)
    assert result["status"] == "SUCCESS"

    with Session(db_engine) as session:
        db_entry = session.exec(select(AuditLog).where(AuditLog.event_id == "test-event-1")).first()
        assert db_entry is not None
        assert db_entry.event == "test.event"
        assert db_entry.integrity_hash is not None
        assert db_entry.verus_txid is None

@pytest.mark.asyncio
@patch("backend.security.vdxf_store.VDXFStore.anchor_audit_batch")
async def test_anchor_audit_batch(mock_anchor):
    mock_anchor.return_value = "mock_txid_123"
    
    # Create an unanchored entry
    entry = AuditEntry(
        id="test-event-2",
        timestamp=datetime.now(timezone.utc).isoformat(),
        event="test.event",
        details="test detail",
        status="INFO"
    )
    await sync_audit_entry(entry)

    with patch("backend.security.audit_ledger.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_settings.VERUS_ID_IDENTITY = "test@id"
        result = await anchor_audit_batch(limit=10)
        
    assert result["status"] == "SUCCESS"
    assert result["txid"] == "mock_txid_123"

    with Session(db_engine) as session:
        db_entry = session.exec(select(AuditLog).where(AuditLog.event_id == "test-event-2")).first()
        assert db_entry is not None
        assert db_entry.verus_txid == "mock_txid_123"
        assert db_entry.vdxf_key == "alluci.audit.ledger@"
        assert db_entry.anchored_timestamp is not None

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_content_multimap", new_callable=AsyncMock)
async def test_audit_verifier_tamper_alert(mock_get_content):
    # Setup the mock vault
    mock_vault = MagicMock()
    mock_vault.lock_vault = MagicMock()

    # 1. Create entry and anchor it
    entry = AuditEntry(
        id="test-tamper-1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        event="test.tamper",
        details="secure data",
        status="INFO"
    )
    await sync_audit_entry(entry)
    
    with Session(db_engine) as session:
        db_entry = session.exec(select(AuditLog).where(AuditLog.event_id == "test-tamper-1")).first()
        assert db_entry is not None
        db_entry.verus_txid = "mock_txid_456"
        session.add(db_entry)
        session.commit()

        # Capture legitimate hash exactly as verifier does
        batch_records = session.exec(select(AuditLog).where(AuditLog.verus_txid == "mock_txid_456").order_by(AuditLog.id)).all()  # type: ignore
        batch_data = json.dumps([r.model_dump(exclude={"verus_txid", "vdxf_key", "anchored_timestamp"}) for r in batch_records], default=str)
        legit_hash = hashlib.sha256(batch_data.encode()).hexdigest()

    # Setup the RPC to return the legit hash
    mock_get_content.return_value = [{"audit_hash": f"sha256:{legit_hash}"}]

    verifier = AuditVerifier(vault=mock_vault)
    
    # 2. Run verification (should succeed)
    with patch("backend.security.audit_verifier.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_settings.VERUS_ID_IDENTITY = "test@id"
        await verifier.verify_ledger()
    
    # Vault should NOT be locked
    mock_vault.lock_vault.assert_not_called()

    # 3. TAMPER THE DATABASE
    with Session(db_engine) as session:
        db_entry = session.exec(select(AuditLog).where(AuditLog.event_id == "test-tamper-1")).first()
        assert db_entry is not None
        db_entry.details = "hacked data" # Tamper!
        session.add(db_entry)
        session.commit()

    # 4. Run verification again (should trigger tamper alert)
    with patch("backend.security.audit_verifier.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_settings.VERUS_ID_IDENTITY = "test@id"
        await verifier.verify_ledger()
    
    # Vault SHOULD be locked
    mock_vault.lock_vault.assert_called_once()
    
    # Check that a TAMPER_ALERT event was logged
    with Session(db_engine) as session:
        tamper_log = session.exec(select(AuditLog).where(AuditLog.event_id == "TAMPER_ALERT")).first()
        assert tamper_log is not None
        assert tamper_log.status == "CRITICAL"

@pytest.mark.asyncio
async def test_sync_audit_entry_chaining():
    e1 = AuditEntry(id="e1", timestamp=datetime.now(timezone.utc).isoformat(), event="EV1", details="1")
    e2 = AuditEntry(id="e2", timestamp=datetime.now(timezone.utc).isoformat(), event="EV2", details="2")
    
    await sync_audit_entry(e1)
    await sync_audit_entry(e2)

    with Session(db_engine) as session:
        logs = session.exec(select(AuditLog).order_by(AuditLog.id)).all()
        assert len(logs) >= 2
        l1, l2 = logs[-2], logs[-1]
        assert l1.integrity_hash != l2.integrity_hash

@pytest.mark.asyncio
async def test_sync_audit_entry_with_topo():
    entry = AuditEntry(id="topo-event", timestamp=datetime.now(timezone.utc).isoformat(), event="TOPO", details="topo details")
    topo_data = {
        "betti": [1, 2, 3],
        "phi_total": 0.5,
        "coherence": 0.8,
        "psi": 1.1,
        "merkle_hash": "abc123hash",
        "pvt": {"proof": "xyz"}
    }
    await sync_audit_entry(entry, topo=topo_data)
    with Session(db_engine) as session:
        log = session.exec(select(AuditLog).where(AuditLog.event_id == "topo-event")).first()
        assert log is not None
        assert log.betti == json.dumps([1, 2, 3])
        assert log.phi_total == 0.5
        assert log.coherence == 0.8
        assert log.psi == 1.1
        assert log.merkle_attribution_hash == "abc123hash"
        assert log.pvt_json == json.dumps({"proof": "xyz"})

@pytest.mark.asyncio
async def test_sync_audit_entry_error():
    with patch("asyncio.to_thread", side_effect=Exception("DB Error")):
        entry = AuditEntry(id="err1", timestamp="", event="ERR", details="")
        res = await sync_audit_entry(entry)
        assert res["status"] == "ERROR"
        assert "DB Error" in res["message"]

@pytest.mark.asyncio
async def test_sync_audit_entry_bad_timestamp():
    entry = AuditEntry(id="bad-ts", timestamp="invalid-time", event="EV", details="")
    res = await sync_audit_entry(entry)
    assert res["status"] == "SUCCESS"
    with Session(db_engine) as session:
        log = session.exec(select(AuditLog).where(AuditLog.event_id == "bad-ts")).first()
        assert log is not None

@pytest.mark.asyncio
async def test_anchor_audit_batch_disabled():
    with patch("backend.security.audit_ledger.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = False
        res = await anchor_audit_batch()
        assert res["status"] == "SKIPPED"

@pytest.mark.asyncio
async def test_anchor_audit_batch_no_records():
    with patch("backend.security.audit_ledger.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_settings.VERUS_ID_IDENTITY = "test_identity@"
        # db is cleared
        res = await anchor_audit_batch()
        assert res["status"] == "SKIPPED"
        assert "No unanchored records" in res["message"]

@pytest.mark.asyncio
@patch("backend.security.vdxf_store.VDXFStore.anchor_audit_batch")
async def test_anchor_audit_batch_failure(mock_anchor):
    mock_anchor.return_value = None
    
    entry = AuditEntry(id="anchor2", timestamp=datetime.now(timezone.utc).isoformat(), event="ANC", details="")
    await sync_audit_entry(entry)
    
    with patch("backend.security.audit_ledger.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_settings.VERUS_ID_IDENTITY = "test_identity@"
        res = await anchor_audit_batch()
        assert res["status"] == "ERROR"
        assert "Failed to anchor" in res["message"]

@pytest.mark.asyncio
async def test_read_audit_log_pagination_status():
    from backend.security.audit_ledger import read_audit_log
    await sync_audit_entry(AuditEntry(id="p1", timestamp=datetime.now(timezone.utc).isoformat(), event="EV", details="", status="INFO"))
    await sync_audit_entry(AuditEntry(id="p2", timestamp=datetime.now(timezone.utc).isoformat(), event="EV", details="", status="WARN"))
    await sync_audit_entry(AuditEntry(id="p3", timestamp=datetime.now(timezone.utc).isoformat(), event="EV", details="", status="WARN"))
    
    logs = await read_audit_log(status="WARN")
    assert len(logs) == 2
    for log in logs:
        assert log["status"] == "WARN"
        
    logs_limited = await read_audit_log(limit=1, offset=1)
@pytest.mark.asyncio
async def test_audit_verifier_lifecycle():
    vault = MagicMock()
    verifier = AuditVerifier(vault=vault, interval_minutes=1)
    
    # Not running yet
    assert not verifier._running
    
    # Start it
    # We patch verify_ledger so it doesn't do real DB/Network work during the test
    with patch.object(verifier, 'verify_ledger', new_callable=AsyncMock) as mock_verify:
        await verifier.start()
        assert verifier._running
        assert verifier._task is not None
        
        # Calling start again should return early
        await verifier.start()
        
        # Let the loop run once
        await asyncio.sleep(0.01)
        
        # Stop it
        await verifier.stop()
        assert not verifier._running
        
        # Force a loop error
        verifier._running = True
        mock_verify.side_effect = Exception("Test Loop Error")
        task = asyncio.create_task(verifier._verification_loop())
        await asyncio.sleep(0.01)
        verifier._running = False
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

@pytest.mark.asyncio
async def test_audit_verifier_disabled_auth():
    vault = MagicMock()
    verifier = AuditVerifier(vault=vault)
    with patch("backend.security.audit_verifier.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = False
        await verifier.verify_ledger()
        # Should return early
        
@pytest.mark.asyncio
async def test_audit_verifier_no_anchored_logs():
    vault = MagicMock()
    verifier = AuditVerifier(vault=vault)
    with patch("backend.security.audit_verifier.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_settings.VERUS_ID_IDENTITY = "test@id"
        await verifier.verify_ledger()
        # Should return early

@pytest.mark.asyncio
@patch("backend.security.verus_rpc.verus_rpc.get_content_multimap", new_callable=AsyncMock)
async def test_audit_verifier_invalid_onchain_data(mock_get_content):
    vault = MagicMock()
    verifier = AuditVerifier(vault=vault)
    
    entry = AuditEntry(id="test-tamper-3", timestamp=datetime.now(timezone.utc).isoformat(), event="test.tamper", details="", status="INFO")
    res = await sync_audit_entry(entry)
    assert res["status"] == "SUCCESS", f"Sync failed: {res}"
    with Session(db_engine) as session:
        db_entry = session.exec(select(AuditLog)).first()
        assert db_entry is not None
        db_entry.verus_txid = "mock_txid_789"
        session.add(db_entry)
        session.commit()
        
    with patch("backend.security.audit_verifier.settings") as mock_settings:
        mock_settings.VERUS_AUTH_ENABLED = True
        mock_settings.VERUS_ID_IDENTITY = "test@id"
        
        # Return non-list
        mock_get_content.return_value = {"error": "not a list"}
        await verifier.verify_ledger()
        
        # Exception path
        mock_get_content.side_effect = Exception("RPC down")
        await verifier.verify_ledger()

