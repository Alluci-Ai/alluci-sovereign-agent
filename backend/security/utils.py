
import logging
from ..logging_config import get_logger
import uuid
from datetime import datetime, timezone
from fastapi import HTTPException
from ..config import settings
from ..models import AuditEntry

logger = get_logger("PolytopeSecurityUtils")

MAX_INPUT_LENGTH = 10_000

async def sanitize_input(text: str, scanner=None) -> str:
    """Sanitize user input. Guards against injection, policy violations, and oversized payloads."""
    if len(text) > MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail=f"Objective exceeds maximum length of {MAX_INPUT_LENGTH} characters."
        )

    text = text.replace("\x00", "").strip()

    if scanner is not None:
        is_safe, error_msg = await scanner.scan_input(text)
        if not is_safe:
            logger.warning(f"[SECURITY] Guardrail Violation: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

    return text

async def log_system_event(event: str, details: str, status: str = "INFO"):
    """Internal helper to record immutable system events."""
    from .audit_ledger import sync_audit_entry # Local import to avoid circularity if needed
    try:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            event=event,
            details=details,
            status=status
        )
        await sync_audit_entry(entry)
    except Exception as e:
        logger.error(f"Failed to log system event {event}: {e}")
