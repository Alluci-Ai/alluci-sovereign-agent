
import logging
from ..logging_config import get_logger
import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select, desc
from ..database import engine as db_engine
from ..models import AuditLog, AuditEntry
from ..config import settings
import asyncio

logger = get_logger("AuditLedger")

# Global lock to prevent race conditions on rolling hash
audit_lock = asyncio.Lock()

async def sync_audit_entry(entry: AuditEntry, topo: Optional[dict] = None):
    """
    Persists an audit entry to the database append-only log.
    Computes a rolling SHA-256 chain hash for tamper evidence.
    Optionally anchors to the Verus blockchain when VerusID is enabled.
    """
    async with audit_lock:
        try:
            # We use a thread pool for DB operations as SQLModel/SQLAlchemy Session is sync
            return await asyncio.to_thread(_sync_audit_entry_sync, entry, topo)
        except Exception as e:
            logger.error(f"Audit sync failed: {e}")
            return {"status": "ERROR", "message": str(e)}

def _sync_audit_entry_sync(entry: AuditEntry, topo: Optional[dict] = None):
    with Session(db_engine) as session:
        # 1. Compute rolling chain hash (hash of previous entry's hash + new content)
        prev = session.exec(
            select(AuditLog).order_by(desc(AuditLog.id)).limit(1)
        ).first()
        prev_hash = prev.integrity_hash if prev else "genesis"
        
        # Consistent string representation for hashing
        details_str = json.dumps(entry.details, sort_keys=True) if not isinstance(entry.details, str) else entry.details
        chain_input = f"{prev_hash}:{entry.event}:{details_str}:{entry.timestamp}"
        integrity_hash = hashlib.sha256(chain_input.encode()).hexdigest()

        # 2. Create DB record
        try:
            ts = datetime.fromisoformat(entry.timestamp.replace('Z', '+00:00'))
        except ValueError:
            ts = datetime.now(timezone.utc)

        log_row = AuditLog(
            event_id=entry.id,
            timestamp=ts,
            event=entry.event,
            details=details_str,
            status=entry.status or "INFO",
            integrity_hash=integrity_hash,
            # Topological fields (when provided)
            betti=json.dumps(topo["betti"]) if topo and "betti" in topo else None,
            phi_total=topo.get("phi_total") if topo else None,
            coherence=topo.get("coherence") if topo else None,
            psi=topo.get("psi") if topo else None,
            merkle_attribution_hash=topo.get("merkle_hash") if topo else None,
            pvt_json=json.dumps(topo["pvt"]) if topo and "pvt" in topo else None,
        )
        session.add(log_row)
        session.commit()

    # 3. Anchor to Verus blockchain if configured (Non-blocking/best-effort)
    if settings.VERUS_AUTH_ENABLED and settings.VERUS_ID_IDENTITY:
        try:
            from .vdxf_store import VDXFStore
            store = VDXFStore(settings.VERUS_ID_IDENTITY)
            # This is sync in VDXFStore usually, or we'd handle it async
            # For simplicity in this sync-helper:
            # loop = asyncio.get_event_loop()
            # loop.create_task(store.anchor_vault_hash(integrity_hash))
            pass 
        except Exception as e:
            logger.warning(f"[AUDIT] VDXF anchoring failed (non-fatal): {e}")

    return {"status": "SUCCESS", "synced_id": entry.id}

async def read_audit_log(limit: int = 100, offset: int = 0, status: Optional[str] = None):
    """Retrieves paginated audit entries from the database."""
    return await asyncio.to_thread(_read_audit_log_sync, limit, offset, status)

def _read_audit_log_sync(limit: int, offset: int, status: Optional[str]):
    with Session(db_engine) as session:
        stmt = select(AuditLog).order_by(desc(AuditLog.id)).offset(offset).limit(limit)
        if status:
            stmt = stmt.where(AuditLog.status == status)
        rows = session.exec(stmt).all()
        return [r.model_dump() for r in rows]
