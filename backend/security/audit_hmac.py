import os
import json
import hmac
import hashlib
from typing import Any, Dict, Optional

# Helper to retrieve HMAC key. Preference: vault secret, fallback to env variable.
def get_hmac_key(key_id: Optional[str] = None) -> bytes:
    """Retrieve the HMAC secret.
    Currently reads from the environment variable ``AUDIT_HMAC_KEY``.
    In the future this could integrate with the VaultManager.
    """
    key = os.getenv("AUDIT_HMAC_KEY")
    if not key:
        raise RuntimeError("HMAC key for audit log not configured (set AUDIT_HMAC_KEY)")
    return key.encode()

def _deterministic_payload(entry: Dict[str, Any]) -> bytes:
    """Create a deterministic JSON payload from immutable fields.
    Fields used: timestamp, id, event, details, status.
    ``details`` is JSON‑encoded with sorted keys.
    """
    payload = {
        "timestamp": entry.get("timestamp"),
        "id": entry.get("id"),
        "event": entry.get("event"),
        "details": entry.get("details"),
        "status": entry.get("status", "INFO"),
    }
    # Ensure ``details`` is a JSON string for consistent hashing
    if not isinstance(payload["details"], str):
        payload["details"] = json.dumps(payload["details"], sort_keys=True)
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()

def compute_signature(entry: Dict[str, Any], key: bytes) -> str:
    """Compute an HMAC‑SHA256 signature for an audit entry.
    ``entry`` is a dict representation of :class:`AuditEntry`.
    Returns the hex digest string.
    """
    data = _deterministic_payload(entry)
    return hmac.new(key, data, hashlib.sha256).hexdigest()

def verify_signature(entry: Dict[str, Any], signature: str, key: bytes) -> bool:
    """Verify that ``signature`` matches the computed HMAC for ``entry``.
    Uses a constant‑time comparison.
    """
    expected = compute_signature(entry, key)
    return hmac.compare_digest(expected, signature)
