import asyncio
from backend.models import AuditEntry
from backend.security.audit_ledger import sync_audit_entry
from datetime import datetime, timezone

async def main():
    e1 = AuditEntry(id="e1", timestamp=datetime.now(timezone.utc).isoformat(), event="EV1", details="1")
    e2 = AuditEntry(id="e2", timestamp=datetime.now(timezone.utc).isoformat(), event="EV2", details="2")
    res1 = await sync_audit_entry(e1)
    res2 = await sync_audit_entry(e2)
    print("RES1:", res1)
    print("RES2:", res2)

asyncio.run(main())
