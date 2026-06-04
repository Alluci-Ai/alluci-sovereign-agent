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
