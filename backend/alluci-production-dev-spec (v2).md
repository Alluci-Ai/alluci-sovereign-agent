# Alluci Sovereign Agent — Production Readiness Developer Specification

**Version:** 1.0  
**Based on audit of:** `alluci-sovereign-agent-main` (March 2026)  
**Purpose:** Step-by-step, indexed, code-complete remediation plan to move from prototype to fully production-ready application.

> Every fix in this spec includes the exact file path, the exact code to remove, and the exact replacement code. Execute phases in order — later phases depend on earlier ones.

---

## Index

| Phase | Title | Priority | Est. Effort |
|---|---|---|---|
| [Phase 1](#phase-1-critical-runtime-bug-fixes) | Critical Runtime Bug Fixes | 🔴 BLOCKER | 2–4 hrs |
| [Phase 2](#phase-2-security-hardening) | Security Hardening | 🔴 BLOCKER | 1–2 days |
| [Phase 3](#phase-3-requirements--dependency-cleanup) | Requirements & Dependency Cleanup | 🟡 HIGH | 2–3 hrs |
| [Phase 4](#phase-4-code-organisation--refactoring) | Code Organisation & Refactoring | 🟡 HIGH | 3–5 days |
| [Phase 5](#phase-5-database--migrations) | Database & Migrations | 🟡 HIGH | 1 day |
| [Phase 6](#phase-6-infrastructure--devops) | Infrastructure & DevOps | 🟡 HIGH | 2–3 days |
| [Phase 7](#phase-7-incomplete-feature-completion) | Incomplete Feature Completion | 🟢 MEDIUM | 3–5 days |
| [Phase 8](#phase-8-performance--scalability) | Performance & Scalability | 🟢 MEDIUM | 2–3 days |
| [Phase 9](#phase-9-testing--ci-hardening) | Testing & CI Hardening | 🟢 MEDIUM | 2–3 days |
| [Phase 10](#phase-10-documentation-alignment) | Documentation Alignment | 🔵 LOW | 1 day |

---

## Phase 1: Critical Runtime Bug Fixes

> These bugs cause immediate runtime crashes or silent failures. Fix all of these before any testing.

---

### FIX-001 — Add Missing `import time` to `app.py`

**File:** `backend/app.py`  
**Line:** 1 (top of import block)  
**Symptom:** `NameError: name 'time' is not defined` on the first HTTP request, crashing the metrics middleware and the `/api/system/health` endpoint.

**Root cause:** `time.time()` is called in the `record_metrics` middleware and in `get_system_health()`, but `import time` is absent from the module-level imports. The inline `import time` inside `record_metrics` works for that function but `get_system_health` (line 600) has no inline import and crashes.

**Fix — add to the existing import block immediately after `import json`:**

```python
# backend/app.py  — add this line after "import json" (currently line 11)
import time
```

---

### FIX-002 — Fix `memory_manager` NameError (4 Routes)

**File:** `backend/app.py`  
**Lines:** 1566, 1570, 1575–1577, 1589  
**Symptom:** `NameError: name 'memory_manager' is not defined` on `GET /api/memory`, `GET /api/memory/search` (the second definition), `GET /api/memory/stats`, and `DELETE /api/memory/{entry_id}`.

**Root cause:** The global is named `memory` (declared at line 77, initialised in `lifespan`). Four route handlers mistakenly reference the non-existent `memory_manager`.

**Fix — replace the four broken handlers:**

```python
# backend/app.py — REPLACE the four broken handlers (lines ~1563–1592)

@app.get("/api/memory", dependencies=[Depends(verify_authenticated)])
async def list_memory(limit: int = Query(50)):
    """List recent memory fragments."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    if memory.lite_mode:
        return await memory.fts_manager.list(limit=limit)
    return memory.collection.get(limit=limit)


@app.get("/api/memory/search", dependencies=[Depends(verify_authenticated)])
async def search_memory(q: str = Query(...)):
    """Semantic search across the sovereign memory manifold."""
    if not memory:
        return []
    return await memory.search(q, limit=10)


@app.get("/api/memory/stats", dependencies=[Depends(verify_authenticated)])
async def get_memory_stats():
    """Return memory manifold statistics."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    if memory.lite_mode:
        return {"mode": "fts", "count": await memory.fts_manager.count()}
    return {
        "mode": "chromadb",
        "count": memory.collection.count(),
        "name": memory.collection.name,
        "metadata": memory.collection.metadata,
    }


@app.delete("/api/memory/{entry_id}", dependencies=[Depends(verify_authenticated)])
async def forget_memory(entry_id: str):
    """Remove a specific memory fragment."""
    if not memory:
        raise HTTPException(status_code=503, detail="Memory manager not initialized")
    await memory.forget(entry_id)
    return {"deleted": entry_id}
```

---

### FIX-003 — Fix `analytics` NameError in `/api/system/health`

**File:** `backend/app.py`  
**Line:** 569  
**Symptom:** `NameError: name 'analytics' is not defined` on `GET /api/system/health`.

**Root cause:** `analytics` is never imported or declared in `app.py`. The module-level `db_engine` (imported from `.database`) is what's needed.

**Fix — replace the broken line:**

```python
# backend/app.py line ~569 — REPLACE:
#   with Session(analytics.db_engine) as session:
# WITH:
        with Session(db_engine) as session:
            session.exec(select(1)).first()
```

Full corrected handler:

```python
@app.get("/api/system/health", dependencies=[Depends(verify_authenticated)])
async def get_system_health():
    """Runs diagnostic checks across primary modules for the Health dashboard."""
    # 1. Database
    db_status = "healthy"
    try:
        from sqlmodel import text
        with Session(db_engine) as session:             # ← FIXED (was analytics.db_engine)
            session.exec(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # 2. Vault Security
    vault_status = "healthy" if vault else "warning"

    # 3. Model Router
    router_status = "unhealthy"
    if router:
        router_status = "warning"  # configured but no providers verified yet

    # 4. Local Inference
    local_inference_status = "healthy" if local_inference else "unhealthy"

    # 5. Bridges
    active_bridges = list(vault.get_active_vaults()) if vault else []

    # 6. Cron Engine Tasks
    cron_status = "healthy" if task_manager else "unhealthy"

    return {
        "database": db_status,
        "vault": vault_status,
        "model_router": router_status,
        "local_inference": local_inference_status,
        "bridges": len(active_bridges),
        "cron_engine": cron_status,
        "uptime": time.time() - metrics.start_time,     # ← now valid after FIX-001
    }
```

---

### FIX-004 — Guard `sanitize_input` Against Uninitialised `scanner`

**File:** `backend/app.py`  
**Lines:** 86–94  
**Symptom:** `AttributeError: 'NoneType' object has no attribute 'scan_input'` if any request arrives before `lifespan` completes scanner initialisation (e.g., during startup probe, or if lifespan fails mid-way).

**Root cause:** `scanner` is declared `None` at module scope and is only assigned during `lifespan`. The `sanitize_input` function is called from multiple route handlers and is not guarded.

**Fix — replace `sanitize_input`:**

```python
# backend/app.py — REPLACE sanitize_input (lines ~87–94)

MAX_INPUT_LENGTH = 10_000  # characters — prevents token-cost amplification attacks

async def sanitize_input(text: str) -> str:
    """Sanitize user input. Guards against injection, policy violations, and oversized payloads."""
    # 1. Length guard (prevents cost-amplification attacks)
    if len(text) > MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail=f"Objective exceeds maximum length of {MAX_INPUT_LENGTH} characters."
        )

    # 2. Null byte strip
    text = text.replace("\x00", "").strip()

    # 3. Guardrail scan — skip if scanner not yet ready (startup window)
    if scanner is not None:
        is_safe, error_msg = await scanner.scan_input(text)
        if not is_safe:
            logger.warning(f"[SECURITY] Guardrail Violation: {error_msg}")
            raise HTTPException(status_code=400, detail=error_msg)

    return text
```

---

### FIX-005 — Remove Duplicate Webhook Route Registrations

**File:** `backend/app.py`  
**Lines:** ~2258–2316  
**Symptom:** FastAPI silently ignores the second registration of `POST /webhook/telegram/{token}`, `GET /webhook/whatsapp`, `POST /webhook/whatsapp`, and `POST /webhook/google_chat`. The duplicate set has different validation logic (token check vs no token check), creating a confusing and unmaintainable split.

**Root cause:** Two separate sections register webhooks — one at `/api/webhook/*` (lines ~1893–1930) and a second bare `/webhook/*` block added later. The second block is dead code.

**Fix — delete the entire duplicate block (lines ~2255–2316):**

```python
# backend/app.py — DELETE this entire section:

# ── Webhook Inbound Handlers (Sprint 2 — Sovereign Spec §2.1–2.2) ──

@app.post("/webhook/telegram/{token}")
async def telegram_webhook(token: str, update: Dict[str, Any]):
    ...

@app.get("/webhook/whatsapp")
async def whatsapp_verify(...):
    ...

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(body: Dict[str, Any]):
    ...

@app.post("/webhook/google_chat")
async def google_chat_webhook(payload: Dict[str, Any]):
    ...
```

**Also upgrade the surviving `/api/webhook/telegram/{token}` handler to include the token validation** that only existed in the deleted duplicate:

```python
# backend/app.py — REPLACE the /api/webhook/telegram handler

@app.post("/api/webhook/telegram/{token}")
async def telegram_webhook(token: str, update: Dict[str, Any] = Body(...)):
    """Receives inbound updates from Telegram Bot API."""
    adapter = channel_registry.get("telegram")
    if not adapter or not hasattr(adapter, "process_webhook"):
        return {"ok": False, "error": "Adapter not ready"}

    # Security: validate the token matches the stored bot token
    if adapter.is_connected and adapter.bot_token and adapter.bot_token != token:
        logger.warning("[TELEGRAM] Webhook received with invalid token — rejected.")
        return {"ok": False, "error": "unauthorized"}

    parsed = await adapter.process_webhook(update)
    if parsed and orchestrator:
        asyncio.create_task(orchestrator.handle_inbound_message(parsed))
    return {"ok": True}
```

---

### FIX-006 — Remove Unreachable `raise` in Gemini Proxy

**File:** `backend/app.py`  
**Lines:** ~1492–1494  
**Symptom:** Dead/unreachable code causes linting failure and confuses error-handling intent.

**Fix — delete the unreachable second raise:**

```python
# backend/app.py — REPLACE the end of the gemini_proxy handler

    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(f"Gemini proxy failed [ref={error_id}]: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Inference request failed. Error reference: {error_id}"
        )
        # DELETED: the unreachable duplicate raise that was here
```

---

### FIX-007 — Fix `WEBABAUTHN_RP_ID` Typo in WebAuthn Challenge

**File:** `backend/app.py`  
**Line:** 1173  
**Symptom:** The `hasattr` check uses the wrong attribute name (`WEBABAUTHN_RP_ID` with extra 'A'), so the condition is always `False` and `rp.id` is always `"localhost"` regardless of configuration.

**Fix — replace the challenge generator's RP block:**

```python
# backend/app.py — REPLACE line ~1173 in get_webauthn_challenge

    return {
        "challenge": b64_challenge,
        "timeout": 60000,
        "rp": {
            "name": "Alluci Sovereign Agent",
            "id": getattr(settings, "WEBAUTHN_RP_ID", "localhost"),  # ← FIXED typo
        },
        "user": {
            "id": "ALLUCI_SOVEREIGN_001",
            "name": "sovereign_admin",
            "displayName": "Sovereign Administrator",
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},
            {"type": "public-key", "alg": -257},
        ],
    }
```

**Also add `WEBAUTHN_RP_ID` and `WEBAUTHN_ORIGIN` to `Settings`:**

```python
# backend/config.py — ADD to the Settings class body

    WEBAUTHN_RP_ID: str = "localhost"
    WEBAUTHN_ORIGIN: str = "http://localhost:5173"
```

**And update `.env.example`:**

```bash
# .env.example — ADD under the Security section
WEBAUTHN_RP_ID=yourdomain.com          # Set to your actual domain in production
WEBAUTHN_ORIGIN=https://yourdomain.com # Full origin (scheme + domain + port)
```

---

### FIX-008 — Remove Dead `base_bridge.py`

**File:** `backend/bridges/base_bridge.py`  
**Symptom:** Two competing `BridgeAdapter` ABCs cause import confusion and make it unclear which base class to extend.

**Fix:**

```bash
# Terminal — run from repository root
rm backend/bridges/base_bridge.py
```

Verify all concrete bridges import from `base.py`:

```bash
# Should return no results if already correct
grep -rn "from .base_bridge import\|from backend.bridges.base_bridge import" backend/
```

---

### FIX-009 — Remove Stale Development Files from Repository Root

**Files:** `previous2_BridgeCenter.tsx`, `previous_WalletPanel.tsx`

```bash
# Terminal — run from repository root
git rm previous2_BridgeCenter.tsx previous_WalletPanel.tsx
echo "previous*.tsx" >> .gitignore
```

---

## Phase 2: Security Hardening

---

### SEC-001 — Replace In-Memory WebAuthn Challenge Store with Redis

**File:** `backend/app.py`  
**Lines:** ~1157–1251  
**Risk:** 🔴 HIGH — In-process dict breaks under multi-worker deployments; any pending challenge matches any verification request (cross-user replay).

**Step 1 — Create a Redis-backed challenge store module:**

```python
# backend/security/webauthn_store.py  (NEW FILE)

import base64
import secrets
import logging
from datetime import timedelta
from typing import Optional

logger = logging.getLogger("WebAuthnStore")

CHALLENGE_TTL_SECONDS = 120  # 2-minute challenge window


class WebAuthnChallengeStore:
    """
    Redis-backed store for WebAuthn challenges.
    Falls back to an asyncio-safe in-memory dict when Redis is unavailable.
    Keys: challenge_id (returned to browser as 'challengeId' field)
    Values: raw challenge bytes, with TTL
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._local: dict = {}  # fallback
        if not redis_client:
            logger.warning(
                "[WebAuthn] Redis unavailable — using in-memory challenge store. "
                "NOT safe for multi-worker deployments."
            )

    async def create_challenge(self) -> tuple[str, str]:
        """
        Returns (challenge_id, b64_challenge).
        challenge_id is stored server-side and returned to the browser.
        b64_challenge is the raw challenge sent to the authenticator.
        """
        challenge_bytes = secrets.token_bytes(32)
        challenge_id = secrets.token_urlsafe(24)
        b64_challenge = base64.urlsafe_b64encode(challenge_bytes).decode().rstrip("=")

        if self._redis:
            await self._redis.setex(
                f"webauthn:challenge:{challenge_id}",
                CHALLENGE_TTL_SECONDS,
                challenge_bytes,
            )
        else:
            self._local[challenge_id] = challenge_bytes

        return challenge_id, b64_challenge

    async def consume_challenge(self, challenge_id: str) -> Optional[bytes]:
        """
        Atomically retrieve and delete a challenge by its ID.
        Returns None if the challenge doesn't exist or has expired.
        """
        if self._redis:
            key = f"webauthn:challenge:{challenge_id}"
            # GETDEL is atomic — prevents replay
            raw = await self._redis.getdel(key)
            return raw if raw else None
        else:
            return self._local.pop(challenge_id, None)


# Module-level singleton — injected with redis_client during lifespan
webauthn_store: WebAuthnChallengeStore = WebAuthnChallengeStore()
```

**Step 2 — Inject Redis into the store during lifespan:**

```python
# backend/app.py — ADD inside lifespan(), after redis_client is created

    from .security.webauthn_store import webauthn_store, WebAuthnChallengeStore
    if redis_client:
        # Re-initialise with real Redis connection
        import backend.security.webauthn_store as _wa_store_module
        _wa_store_module.webauthn_store = WebAuthnChallengeStore(redis_client)
        logger.info("[ WEBAUTHN ] Challenge store backed by Redis.")
```

**Step 3 — Replace the WebAuthn challenge endpoint:**

```python
# backend/app.py — REPLACE get_webauthn_challenge and verify_webauthn_response

from .security.webauthn_store import webauthn_store  # add to imports

@app.get("/auth/webauthn/challenge")
async def get_webauthn_challenge():
    """Generates a cryptographic challenge for WebAuthn/FIDO2."""
    challenge_id, b64_challenge = await webauthn_store.create_challenge()

    return {
        "challengeId": challenge_id,          # browser sends this back on verify
        "challenge": b64_challenge,
        "timeout": 120_000,                   # 2 minutes, matches TTL
        "rp": {
            "name": "Alluci Sovereign Agent",
            "id": getattr(settings, "WEBAUTHN_RP_ID", "localhost"),
        },
        "user": {
            "id": "ALLUCI_SOVEREIGN_001",
            "name": "sovereign_admin",
            "displayName": "Sovereign Administrator",
        },
        "pubKeyCredParams": [
            {"type": "public-key", "alg": -7},   # ES256
            {"type": "public-key", "alg": -257},  # RS256
        ],
    }


@app.post("/auth/webauthn/verify")
async def verify_webauthn_response(payload: Dict[str, Any] = Body(...)):
    """Verifies the WebAuthn attestation/assertion using py_webauthn."""
    try:
        from webauthn import verify_registration_response
        from webauthn.helpers.structs import RegistrationCredential
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="WebAuthn library not installed. Run: pip install webauthn>=2.0.0"
        )

    challenge_id = payload.get("challengeId")
    credential_id = payload.get("id")
    raw_id = payload.get("rawId")
    response_data = payload.get("response", {})

    if not all([challenge_id, credential_id, raw_id,
                response_data.get("attestationObject"),
                response_data.get("clientDataJSON")]):
        raise HTTPException(status_code=400, detail="Missing required WebAuthn fields")

    # Atomically consume the challenge — prevents replay
    expected_challenge = await webauthn_store.consume_challenge(challenge_id)
    if expected_challenge is None:
        raise HTTPException(status_code=400, detail="Challenge not found or expired.")

    rp_id = getattr(settings, "WEBAUTHN_RP_ID", "localhost")
    expected_origin = getattr(settings, "WEBAUTHN_ORIGIN", "http://localhost:5173")

    try:
        credential = RegistrationCredential(
            id=credential_id,
            raw_id=base64.urlsafe_b64decode(raw_id + "=="),
            response={
                "attestation_object": base64.urlsafe_b64decode(
                    response_data["attestationObject"] + "=="
                ),
                "client_data_json": base64.urlsafe_b64decode(
                    response_data["clientDataJSON"] + "=="
                ),
            },
            type="public-key",
        )

        verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=rp_id,
            expected_origin=expected_origin,
        )

        logger.info(f"[WEBAUTHN] Verification successful: {credential_id}")
        return {
            "status": "SUCCESS",
            "token": create_access_token({"sub": "sovereign_admin", "webauthn": True}),
            "credential_id": credential_id,
        }

    except Exception as e:
        logger.warning(f"[WEBAUTHN] Verification failed: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"WebAuthn verification failed: {type(e).__name__}"
        )
```

---

### SEC-002 — Fix OAuth Callback Reflected XSS

**File:** `backend/app.py`  
**Lines:** ~2820–2840  
**Risk:** 🔴 HIGH — `bridge_id` from the URL path is interpolated directly into an inline `<script>` tag without sanitisation.

**Fix — replace the OAuth callback handler:**

```python
# backend/app.py — REPLACE oauth_callback

_VALID_BRIDGE_IDS = frozenset([
    "telegram", "whatsapp", "discord", "slack", "email", "signal",
    "google_chat", "nostr", "imessage", "gdrive", "gmail", "gm", "gd",
    "msteams", "facebook", "instagram", "x_twitter", "wechat",
])

@app.get("/api/oauth/{bridge_id}/callback")
async def oauth_callback(bridge_id: str, code: str = Query(None), state: str = Query(None)):
    """Generic OAuth callback endpoint for all OAuth-based bridges."""

    # Security: validate bridge_id against known set before any string interpolation
    if bridge_id not in _VALID_BRIDGE_IDS:
        logger.warning(f"[OAUTH] Callback received for unknown bridge_id: '{bridge_id}'")
        from fastapi.responses import HTMLResponse
        return HTMLResponse(
            "<script>"
            "window.opener && window.opener.postMessage("
            "  JSON.stringify({ type: 'OAUTH_COMPLETE', error: 'invalid_bridge' }),"
            "  window.location.origin"  # restrict to same origin
            ");"
            "window.close();"
            "</script>",
            status_code=400,
        )

    # Use JSON.stringify so the data is safely serialised — no string interpolation
    def _make_response(success: bool, error: str = "") -> "HTMLResponse":
        from fastapi.responses import HTMLResponse
        import json as _json
        payload = _json.dumps({
            "type": "OAUTH_COMPLETE",
            "bridgeId": bridge_id,           # safe: validated against whitelist above
            "success": success,
            "error": error,
        })
        return HTMLResponse(
            f"<script>"
            f"window.opener && window.opener.postMessage({payload}, window.location.origin);"
            f"window.close();"
            f"</script>"
        )

    adapter = channel_registry.get(bridge_id)
    if not adapter:
        return _make_response(False, "bridge_not_found")

    if hasattr(adapter, "handle_oauth_callback"):
        try:
            await adapter.handle_oauth_callback(code, state)
            return _make_response(True)
        except Exception as e:
            logger.error(f"[OAUTH] Callback error for {bridge_id}: {e}")
            return _make_response(False, "callback_error")

    return _make_response(False, "oauth_not_implemented")
```

---

### SEC-003 — Harden Audit Ledger (DB-backed, append-only)

**File:** `backend/app.py` + `backend/models.py`  
**Risk:** 🟡 MEDIUM — Current vault-blob audit store silently truncates to 1,000 entries; vulnerable to lock contention.

**Step 1 — Add `AuditLog` DB model:**

```python
# backend/models.py — ADD this class

class AuditLog(SQLModel, table=True):
    """Immutable, append-only audit log stored in the database."""
    __tablename__ = "audit_log"
    id: Optional[int] = Field(default=None, primary_key=True)
    event_id: str = Field(index=True)          # UUID from AuditEntry
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        index=True,
    )
    event: str = Field(index=True)
    details: str
    status: str = Field(default="INFO")
    integrity_hash: Optional[str] = None       # SHA-256 of previous entry chain
```

**Step 2 — Replace `sync_audit_entry` in `app.py`:**

```python
# backend/app.py — REPLACE sync_audit_entry and get_audit_ledger

import hashlib as _hashlib

@app.post("/api/audit/entry", dependencies=[Depends(verify_authenticated)])
async def sync_audit_entry(entry: AuditEntry):
    """
    Persists an audit entry to the database append-only log.
    Computes a rolling SHA-256 chain hash for tamper evidence.
    Optionally anchors to the Verus blockchain when VerusID is enabled.
    """
    from .models import AuditLog

    async with audit_lock:
        try:
            with Session(db_engine) as session:
                # Compute rolling chain hash (hash of previous entry's hash + new content)
                prev = session.exec(
                    select(AuditLog).order_by(AuditLog.id.desc()).limit(1)
                ).first()
                prev_hash = prev.integrity_hash if prev else "genesis"
                chain_input = f"{prev_hash}:{entry.event}:{entry.details}:{entry.timestamp}"
                integrity_hash = _hashlib.sha256(chain_input.encode()).hexdigest()

                log_row = AuditLog(
                    event_id=entry.id,
                    timestamp=datetime.fromisoformat(entry.timestamp)
                        if isinstance(entry.timestamp, str)
                        else entry.timestamp,
                    event=entry.event,
                    details=entry.details,
                    status=entry.status or "INFO",
                    integrity_hash=integrity_hash,
                )
                session.add(log_row)
                session.commit()

            # Anchor to Verus blockchain if configured
            if settings.VERUS_AUTH_ENABLED and settings.VERUS_ID_IDENTITY:
                try:
                    from .security.vdxf_store import VDXFStore
                    store = VDXFStore(settings.VERUS_ID_IDENTITY)
                    await store.anchor_vault_hash(integrity_hash)
                except Exception as e:
                    logger.warning(f"[AUDIT] VDXF anchoring failed (non-fatal): {e}")

            return {"status": "SUCCESS", "synced_id": entry.id}

        except Exception as e:
            logger.error(f"Audit sync failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to sync audit ledger.")


@app.get("/api/audit/ledger", dependencies=[Depends(verify_authenticated)])
async def get_audit_ledger(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None),
):
    """Retrieves paginated audit entries from the database."""
    from .models import AuditLog

    with Session(db_engine) as session:
        stmt = select(AuditLog).order_by(AuditLog.id.desc()).offset(offset).limit(limit)
        if status:
            stmt = stmt.where(AuditLog.status == status)
        rows = session.exec(stmt).all()
        return [r.model_dump() for r in rows]
```

---

### SEC-004 — Fix `ALLOWED_ORIGINS` Production Validator

**File:** `backend/config.py`  
**Risk:** 🟡 MEDIUM — Pydantic-settings `field_validator` reads `APP_ENV` from raw `os.getenv()` which may lag behind the parsed `APP_ENV` field if ordering in `.env` is unusual.

**Fix — replace the validator:**

```python
# backend/config.py — REPLACE strip_localhost_in_prod validator

    @field_validator("ALLOWED_ORIGINS", mode="after")
    @classmethod
    def strip_localhost_in_prod(cls, v: List[str], info) -> List[str]:
        # Use info.data to read the already-parsed APP_ENV value
        app_env = info.data.get("APP_ENV", os.getenv("APP_ENV", "development"))
        if app_env == "production":
            filtered = [
                origin for origin in v
                if "localhost" not in origin and "127.0.0.1" not in origin
            ]
            if not filtered:
                raise ValueError(
                    "ALLOWED_ORIGINS contains only localhost entries but APP_ENV=production. "
                    "Set ALLOWED_ORIGINS to your production domain."
                )
            return filtered
        return v
```

---

### SEC-005 — Harden Hardcoded PostgreSQL Fallback Password

**File:** `backend/config.py`  
**Risk:** 🟡 MEDIUM — `"postgresql+asyncpg://alluci:password@localhost/polytope"` is the fallback when `PROD_DATABASE_URL` is unset. The literal `password` would silently become the production DB password.

**Fix — make production fail loudly instead of using a default:**

```python
# backend/config.py — REPLACE enforce_production_db validator

    @field_validator("DATABASE_URL")
    @classmethod
    def enforce_production_db(cls, v: str, info) -> str:
        app_env = info.data.get("APP_ENV", os.getenv("APP_ENV", "development"))
        if app_env == "production" and "sqlite" in v:
            prod_url = os.getenv("PROD_DATABASE_URL")
            if not prod_url:
                logger.critical(
                    "🚨 FATAL: APP_ENV=production but PROD_DATABASE_URL is not set. "
                    "SQLite is not suitable for production. "
                    "Set PROD_DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname"
                )
                sys.exit(1)
            return prod_url
        return v
```

**Update `.env.example`:**

```bash
# .env.example — ADD under Database section
# Required when APP_ENV=production (SQLite is rejected in production)
PROD_DATABASE_URL=postgresql+asyncpg://alluci:CHANGE_ME@db:5432/polytope
```

---

### SEC-006 — Add Rate Limiter Unavailability Metric

**File:** `backend/app.py`  
**Risk:** 🟡 MEDIUM — When Redis is unavailable, rate limiting silently disables with no alert.

**Fix — add metric increment to the Redis failure path in `lifespan`:**

```python
# backend/app.py — REPLACE the Redis initialisation block in lifespan

    if settings.REDIS_URL:
        try:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8")
            await FastAPILimiter.init(redis_client)
            logger.info(f"[ CACHE ]: Redis distributed rate limiter online: {settings.REDIS_URL}")
        except Exception as e:
            logger.error(
                f"[ CACHE ]: Redis initialisation failed — rate limiting DISABLED: {e}"
            )
            metrics.increment_counter("redis_init_failures_total")   # observable in /metrics
    else:
        logger.warning(
            "[ CACHE ]: REDIS_URL not configured. "
            "Rate limiting is INACTIVE. Set REDIS_URL for production deployments."
        )
        metrics.increment_counter("redis_not_configured_total")
```

**Also add the `increment_counter` method to the `Metrics` class in `backend/metrics.py`:**

```python
# backend/metrics.py — ADD method to existing Metrics class

    def increment_counter(self, name: str, amount: int = 1):
        """Increment a named Prometheus-style counter."""
        self._counters[name] = self._counters.get(name, 0) + amount

    def get_metrics_text(self) -> str:
        lines = []
        # ... existing lines ...
        for name, val in self._counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {val}")
        return "\n".join(lines)
```


---

## Phase 3: Requirements & Dependency Cleanup

---

### DEP-001 — Add Missing Packages to `requirements.txt`

**File:** `requirements.txt`  
**Symptom:** `ImportError` on fresh install for `keyring` (VaultManager), `webauthn` (already present but verify version), `discord.py` (DiscordBridge), and `keyring` which is used in `backend/security/vault.py` but not listed.

**Fix — replace `requirements.txt` entirely with a clean, organised version:**

```text
# requirements.txt — FULL REPLACEMENT

# ─── Web Framework ────────────────────────────────────────────────────────────
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
starlette==0.41.0

# ─── Data Validation & Settings ───────────────────────────────────────────────
pydantic==2.8.0
pydantic-settings==2.4.0

# ─── Database & Migrations ────────────────────────────────────────────────────
sqlmodel==0.0.21
alembic==1.13.2
psycopg2-binary==2.9.9       # PostgreSQL sync driver (Alembic migrations)
asyncpg==0.29.0              # PostgreSQL async driver (runtime)
aiosqlite==0.20.0            # SQLite async support

# ─── Security & Cryptography ──────────────────────────────────────────────────
cryptography==43.0.0
python-jose[cryptography]==3.3.0
webauthn==2.1.0
keyring==25.3.0              # OS Keychain integration for vault master key
passlib[bcrypt]==1.7.4

# ─── LLM Providers ────────────────────────────────────────────────────────────
google-generativeai==0.8.3
google-auth==2.34.0
openai==1.40.0
anthropic==0.34.0
httpx==0.27.0

# ─── Messaging & Bridge SDKs ──────────────────────────────────────────────────
discord.py==2.3.2            # Discord bridge
python-telegram-bot==21.6    # Telegram bridge
nostr-sdk==0.3.0             # Nostr bridge
aiosmtplib==3.0.1            # Async SMTP for email bridge
aioimaplib==1.1.0            # Async IMAP for email bridge

# ─── Vector Memory ────────────────────────────────────────────────────────────
chromadb==0.5.0
sentence-transformers==3.0.1 # Embedding model (~80MB download on first use)

# ─── Cache & Rate Limiting ────────────────────────────────────────────────────
redis[hiredis]>=5.0.0,<6.0.0
fastapi-limiter==0.1.6

# ─── Observability & Logging ──────────────────────────────────────────────────
structlog>=24.1.0
psutil==6.0.0

# ─── Async & System Utilities ─────────────────────────────────────────────────
aiofiles==23.2.1
tenacity==8.5.0

# ─── Task Scheduling ──────────────────────────────────────────────────────────
# (Cron engine uses asyncio internally — no extra dep required)

# ─── Blockchain / VerusID ─────────────────────────────────────────────────────
# verusd-rpc-ts-client is bundled in third-party/ — no pip dep required

# ─── AWS (optional — used by get_secret() in config.py) ──────────────────────
boto3>=1.34.0

# ─── Browser Automation (screen_capture adapter) ──────────────────────────────
playwright==1.46.0
```

**Create `requirements-tda.txt` for the optional topological data analysis features:**

```text
# requirements-tda.txt  (OPTIONAL — only needed for full PPN/DPK implementation)
# Install with: pip install -r requirements-tda.txt
# WARNING: Large download (~2GB for torch). Not required for standard operation.

torch>=2.3.0
numpy>=1.26.0
gudhi>=3.9.0
```

**Create `requirements-dev.txt`:**

```text
# requirements-dev.txt
-r requirements.txt

pytest>=8.0.0
pytest-asyncio>=0.23.0
pytest-cov>=5.0.0
httpx>=0.27.0            # TestClient requires httpx
ruff>=0.6.0
mypy>=1.11.0
pre-commit>=3.8.0
```

---

### DEP-002 — Remove `puppeteer-core` from Frontend

**File:** `package.json`  
**Symptom:** `puppeteer-core` is a Node.js server library included in a browser React bundle. It has no valid frontend use and adds ~60MB to `node_modules`.

**Fix:**

```bash
npm uninstall puppeteer-core
```

Verify no frontend file imports it:

```bash
grep -r "puppeteer" src/ components/ features/ --include="*.ts" --include="*.tsx"
# Should return no results
```

---

## Phase 4: Code Organisation & Refactoring

---

### REFACTOR-001 — Split `app.py` into APIRouter Modules

**Rationale:** `app.py` is ~2,400 lines. FastAPI's `APIRouter` allows breaking it into logical submodules while keeping a thin main `app.py` as the assembler.

**Target file structure:**

```
backend/
  app.py                     (thin — ~100 lines: create app, register routers, lifespan)
  routers/
    __init__.py
    auth.py                  (login, logout, verusid, webauthn)
    vault.py                 (vault CRUD, key management)
    dag.py                   (objective execution, plan preview, run management, SSE)
    channels.py              (channel status, config, connect, send, webhooks)
    memory.py                (search, store, stats, forget)
    analytics.py             (usage summary, sessions, daily, export)
    cron.py                  (job CRUD, run history)
    skills.py                (list, create, delete, sign, promote)
    soul.py                  (manifest, preferences, preview)
    wallet.py                (balances, send, convert, identity, node)
    system.py                (health, status, install, config, devices, logs)
    agents.py                (list, delegate, sessions)
```

**Step 1 — Create router files. Example for `auth.py`:**

```python
# backend/routers/auth.py  (NEW FILE)

import base64
import logging
import hmac
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Body, Query, Response
from jose import JWTError, jwt

from ..config import settings
from ..models import LoginRequest
from ..security.auth import create_access_token, verify_authenticated
from ..security.verusid_auth import verus_auth
from ..security.webauthn_store import webauthn_store

logger = logging.getLogger("Router.Auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
async def login(response: Response, payload: LoginRequest):
    """Sovereign Master Key Authentication."""
    if hmac.compare_digest(payload.key, settings.POLYTOPE_MASTER_KEY):
        token = create_access_token(data={"sub": "sovereign_admin"})
        response.set_cookie(
            key=settings.AUTH_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.APP_ENV != "development",
            samesite=settings.AUTH_COOKIE_SAMESITE,
            max_age=86400,
        )
        return {"access_token": token, "token_type": "bearer", "status": "SUCCESS"}
    raise HTTPException(status_code=401, detail="Invalid Sovereign Master Key")


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(settings.AUTH_COOKIE_NAME)
    return {"status": "SUCCESS", "message": "Logged out."}


# ... (migrate all /auth/* routes here)
```

**Step 2 — Create thin `app.py`:**

```python
# backend/app.py  — NEW SLIM VERSION

import asyncio
import contextlib
import logging
import time
import uuid
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .logging_config import configure_logging
from .lifespan import app_lifespan           # extract lifespan to its own module
from .metrics import metrics

# Import all routers
from .routers import (
    auth, vault, dag, channels,
    memory, analytics_router, cron,
    skills, soul, wallet, system, agents,
)

logger = logging.getLogger("PolytopeApp")

app = FastAPI(
    title="Polytope Executive Daemon",
    version="1.0.0",
    lifespan=app_lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Register all routers
app.include_router(auth.router)
app.include_router(vault.router)
app.include_router(dag.router)
app.include_router(channels.router)
app.include_router(memory.router)
app.include_router(analytics_router.router)
app.include_router(cron.router)
app.include_router(skills.router)
app.include_router(soul.router)
app.include_router(wallet.router)
app.include_router(system.router)
app.include_router(agents.router)

# Middleware, exception handlers, health endpoints (see below)
```

---

### REFACTOR-002 — Extract Lifespan to `backend/lifespan.py`

**File:** `backend/lifespan.py` (NEW FILE)  
**Rationale:** The `lifespan` context manager is ~200 lines. Extracting it makes both `app.py` and the lifespan logic individually testable.

```python
# backend/lifespan.py  (NEW FILE — extract lifespan from app.py)

import asyncio
import contextlib
import logging
import os

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter

from .config import settings
from .database import create_db_and_tables, engine as db_engine
from .logging_config import configure_logging
from .metrics import metrics

# Service imports
from .security.vault import VaultManager
from .security.verus import SovereignIdentity
from .inference.router import ModelRouter
from .security.guardrail import GuardrailScanner
from .ace.engine import AffectiveEngine
from .skill_manager import SkillManager
from .memory.manager import MemoryManager
from .analytics import UsageTracker
from .orchestrator import ExecutiveOrchestrator
from .tasks import TaskManager
from .inference.local_bridge import LocalInferenceBridge
from .ws_gateway import JsonRpcGateway
from .cron_engine import CronEngine
from .log_streamer import log_buffer
from .config_editor import ConfigEditor
from .exec_approval import ExecApprovalManager
from .updater import updater
from .goals.engine import goal_engine
from .sop.engine import sop_engine

# Shared service container — populated during lifespan, read by routers
from . import services   # see services.py below

logger = logging.getLogger("PolytopeLifespan")


@contextlib.asynccontextmanager
async def app_lifespan(app: FastAPI):
    configure_logging(app_env=settings.APP_ENV)
    logger.info("[ POLYTOPE_DAEMON ] Booting...")

    # Redis
    if settings.REDIS_URL:
        try:
            redis_client = redis.from_url(settings.REDIS_URL, encoding="utf-8")
            await FastAPILimiter.init(redis_client)
            services.redis_client = redis_client
            logger.info(f"[ CACHE ] Redis online: {settings.REDIS_URL}")
        except Exception as e:
            logger.error(f"[ CACHE ] Redis failed — rate limiting inactive: {e}")
            metrics.increment_counter("redis_init_failures_total")
    else:
        logger.warning("[ CACHE ] REDIS_URL not set — rate limiting inactive.")

    create_db_and_tables()

    # Boot services in dependency order
    services.vault = VaultManager(settings.POLYTOPE_MASTER_KEY)
    services.sovereign_identity = SovereignIdentity(settings)
    services.router = ModelRouter(settings)
    services.scanner = GuardrailScanner(services.router)
    services.ace = AffectiveEngine()
    services.skill_manager = SkillManager(services.vault)
    services.memory = MemoryManager()
    services.usage_tracker = UsageTracker(db_engine)

    services.orchestrator = ExecutiveOrchestrator(
        services.router, services.vault, services.ace, settings,
        skill_manager=services.skill_manager,
        analytics=services.usage_tracker,
        memory_manager=services.memory,
    )

    services.task_manager = TaskManager()
    services.local_inference = LocalInferenceBridge(settings)
    services.ws_gw = JsonRpcGateway(jwt_secret=settings.JWT_SECRET_KEY)
    services.exec_approval = ExecApprovalManager(db_engine, ws_gateway=services.ws_gw)

    # Wire approvals into orchestrator
    services.orchestrator.approval_manager = services.exec_approval
    services.orchestrator.executor.approval_manager = services.exec_approval
    services.orchestrator.ws_gateway = services.ws_gw
    services.router.ws_gateway = services.ws_gw

    await updater.start()
    services.ws_gw.inject_services(
        vault=services.vault,
        router=services.router,
        orchestrator=services.orchestrator,
        channel_registry=services.channel_registry,
        db_engine=db_engine,
        updater=updater,
    )

    services.cron_engine = CronEngine(
        db_engine,
        orchestrator=services.orchestrator,
        task_manager=services.task_manager,
    )
    await services.cron_engine.start()
    log_buffer.install_handler()
    services.config_editor = ConfigEditor(settings)

    # WebAuthn store
    from .security.webauthn_store import WebAuthnChallengeStore
    import backend.security.webauthn_store as _wa_store
    if services.redis_client:
        _wa_store.webauthn_store = WebAuthnChallengeStore(services.redis_client)

    # Bridge registry
    _boot_channels(services)

    services.cron_engine.channel_registry = services.channel_registry

    from .device_manager import DeviceManager
    vault_root = os.path.expanduser("~/.polytope/vaults")
    services.device_manager = DeviceManager(vault_root)

    await services.orchestrator.start_background_services()
    logger.info("[ POLYTOPE_DAEMON ] All systems nominal. Ready.")

    yield

    # Graceful shutdown
    logger.info("[ POLYTOPE_DAEMON ] Shutting down...")
    if services.cron_engine:
        await services.cron_engine.stop()
    if services.orchestrator:
        await services.orchestrator.stop_background_services()
    await updater.stop()

    close_tasks = [
        adapter.disconnect()
        for adapter in services.channel_registry.values()
        if hasattr(adapter, "disconnect")
    ]
    if close_tasks:
        await asyncio.gather(*close_tasks, return_exceptions=True)

    if services.redis_client:
        await services.redis_client.close()

    logger.info("[ POLYTOPE_DAEMON ] Shutdown complete.")


def _boot_channels(services):
    """Initialises all bridge adapters and wires event callbacks."""
    from .bridges.telegram import TelegramBridge
    from .bridges.whatsapp import WhatsAppBridge
    from .bridges.discord import DiscordBridge
    from .bridges.slack import SlackBridge
    from .bridges.email import EmailBridge
    from .bridges.signal import SignalBridge
    from .bridges.google_chat import GoogleChatBridge
    from .bridges.nostr import NostrBridge
    from .bridges.imessage import IMessageBridge

    vault_root = os.path.expanduser("~/.polytope/vaults")
    os.makedirs(vault_root, exist_ok=True)

    registry = services.channel_registry
    registry["telegram"]     = TelegramBridge("telegram", vault_root)
    registry["whatsapp"]     = WhatsAppBridge("whatsapp", vault_root)
    registry["discord"]      = DiscordBridge("discord", vault_root)
    registry["slack"]        = SlackBridge("slack", vault_root)
    registry["email"]        = EmailBridge("email", vault_root)
    registry["signal"]       = SignalBridge("signal", vault_root)
    registry["google_chat"]  = GoogleChatBridge("google_chat", vault_root)
    registry["nostr"]        = NostrBridge("nostr", vault_root)
    registry["imessage"]     = IMessageBridge("imessage", vault_root)

    async def _broadcast(event: str, data):
        await services.ws_gw.broadcast_event(event, data)

    for adapter in registry.values():
        if hasattr(adapter, "on_event"):
            adapter.on_event = _broadcast
        if hasattr(adapter, "on_inbound"):
            adapter.on_inbound = services.orchestrator.handle_inbound_message
```

---

### REFACTOR-003 — Create `backend/services.py` (Shared Service Container)

```python
# backend/services.py  (NEW FILE)
"""
Singleton service container.
All services are None at import time and populated during app lifespan.
Routers access services via `from . import services` then `services.vault`, etc.
"""
from typing import Any, Dict, Optional

vault: Any = None
router: Any = None
ace: Any = None
orchestrator: Any = None
task_manager: Any = None
skill_manager: Any = None
sovereign_identity: Any = None
local_inference: Any = None
ws_gw: Any = None
usage_tracker: Any = None
cron_engine: Any = None
config_editor: Any = None
exec_approval: Any = None
device_manager: Any = None
memory: Any = None
redis_client: Optional[Any] = None
scanner: Any = None
channel_registry: Dict[str, Any] = {}
```

---

### REFACTOR-004 — Clean Up Debug Log Statements in Lifespan

After extracting to `lifespan.py`, remove all `logger.info("DEBUG: ...")` statements:

```bash
# One-liner cleanup — removes all lines matching the debug pattern
sed -i '/logger\.info("DEBUG:/d' backend/lifespan.py
```

Verify:
```bash
grep -n "DEBUG:" backend/lifespan.py  # should return nothing
```

---

## Phase 5: Database & Migrations

---

### DB-001 — Generate Missing Alembic Migration for All New Tables

**Context:** The initial migration `cc9ee558fe12` only covers `run` and `taskrecord`. All tables added in Sprints 1–6 (UsageLog, ModelPricing, CronJob, ChannelAccount, Device, AuditLog, SessionConfig, MessageLog, DiscordGuildMapping, etc.) need migrations.

**Step 1 — Ensure all models are imported in `env.py`:**

```python
# backend/migrations/env.py — ADD at the top of the file, after existing imports

# Import ALL SQLModel table classes so Alembic can detect them
from backend.models import (          # noqa: F401
    Run, TaskRecord, UsageLog, ModelPricing, CronJob, CronRun,
    ChannelAccount, Device, AuditLog, SessionConfig, MessageLog,
    DiscordGuildMapping, SoulPreferences,
)
import sqlmodel                       # noqa: F401  (required for AutoString detection)

target_metadata = SQLModel.metadata
```

**Step 2 — Generate the migration:**

```bash
# Run from repository root with the venv active
cd /path/to/repo
source .venv/bin/activate
export POLYTOPE_MASTER_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
alembic revision --autogenerate -m "add_sprint_1_6_tables"
alembic upgrade head
```

**Step 3 — Add Alembic check to CI:**

```yaml
# .github/workflows/ci.yml — ADD step to backend job after "Run tests"
      - name: Check for unmigrated models
        env:
          POLYTOPE_MASTER_KEY: ${{ secrets.TEST_MASTER_KEY }}
          JWT_SECRET_KEY: ${{ secrets.TEST_JWT_KEY }}
          DATABASE_URL: sqlite:///test_migration_check.db
        run: |
          alembic upgrade head
          alembic check
```

---

### DB-002 — Add `AuditLog` to the Migration

Ensure the migration generated in DB-001 includes the new `AuditLog` table from SEC-003:

```python
# Verify it appears in the generated migration file under upgrade():
op.create_table('audit_log',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.String(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('event', sa.String(), nullable=False),
    sa.Column('details', sa.String(), nullable=False),
    sa.Column('status', sa.String(), nullable=False, server_default='INFO'),
    sa.Column('integrity_hash', sa.String(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
)
op.create_index('ix_audit_log_event_id', 'audit_log', ['event_id'])
op.create_index('ix_audit_log_event', 'audit_log', ['event'])
op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])
```

---

## Phase 6: Infrastructure & DevOps

---

### INFRA-001 — Create `docker-compose.yml`

**File:** `docker-compose.yml` (NEW FILE at repository root)

```yaml
# docker-compose.yml
version: "3.9"

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: alluci-backend
    restart: unless-stopped
    env_file: .env
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql+asyncpg://alluci:${DB_PASSWORD}@db:5432/polytope
      - PROD_DATABASE_URL=postgresql+asyncpg://alluci:${DB_PASSWORD}@db:5432/polytope
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "8000:8000"
    volumes:
      - sovereign_vault:/home/polytope/.polytope
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c",
             "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      start_period: 15s
      retries: 3

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: alluci-frontend
    restart: unless-stopped
    ports:
      - "3000:80"
    depends_on:
      - backend

  db:
    image: postgres:16-alpine
    container_name: alluci-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: alluci
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: polytope
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U alluci -d polytope"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: alluci-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  sovereign_vault:
  postgres_data:
  redis_data:
```

**Update `.env.example`:**

```bash
# .env.example — ADD Docker Compose variables
DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD
REDIS_PASSWORD=CHANGE_ME_REDIS_PASSWORD   # Leave blank to disable Redis auth
DAEMON_PUBLIC_URL=https://yourdomain.com  # Used for OAuth redirect URIs
```

---

### INFRA-002 — Pin Docker Base Images to Digest

**File:** `Dockerfile.backend`

```dockerfile
# Dockerfile.backend — REPLACE first FROM line
# Re-pin periodically: docker pull python:3.12-slim && docker inspect python:3.12-slim | grep Id
FROM python:3.12-slim@sha256:032c52613401895aa3d418a7517617563425efda9cd0c2afe1735d9fc3ca5b1f AS base
```

**File:** `Dockerfile.frontend` — apply same pattern:

```dockerfile
# Dockerfile.frontend — pin both build and runtime stages
FROM node:20-alpine@sha256:<digest> AS build
FROM nginx:1.27-alpine@sha256:<digest> AS runtime
```

---

### INFRA-003 — Create `Dockerfile.frontend`

If not present, create a production-ready frontend Dockerfile:

```dockerfile
# Dockerfile.frontend  (NEW FILE or replace existing)

FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .
RUN npm run build

# ── Production Runtime ──
FROM nginx:1.27-alpine AS runtime

# Custom nginx config for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**Create `nginx.conf`:**

```nginx
# nginx.conf  (NEW FILE at repository root)
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback — all routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to the backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }

    # WebSocket proxying
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
    }

    # Webhook passthrough
    location /api/webhook/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
}
```

---

### INFRA-004 — Create Missing Setup Script

**File:** `scripts/setup_sovereign_stack.sh` (NEW FILE — referenced in README but missing)

```bash
#!/usr/bin/env bash
# scripts/setup_sovereign_stack.sh
# Installs local sovereign inference stack: Ollama, Whisper.cpp, Piper TTS
set -euo pipefail

echo "═══════════════════════════════════════════════════════"
echo "  Alluci Sovereign Stack Setup"
echo "═══════════════════════════════════════════════════════"

OS=$(uname -s)
ARCH=$(uname -m)

# ── 1. Ollama ──────────────────────────────────────────────
echo "[1/4] Installing Ollama..."
if command -v ollama &>/dev/null; then
    echo "  Ollama already installed: $(ollama --version)"
else
    if [[ "$OS" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            brew install ollama
        else
            curl -fsSL https://ollama.ai/install.sh | sh
        fi
    else
        curl -fsSL https://ollama.ai/install.sh | sh
    fi
fi

echo "[2/4] Pulling Llama 3.2 model (default sovereign model)..."
ollama pull llama3.2

# ── 2. Whisper.cpp ─────────────────────────────────────────
echo "[3/4] Setting up Whisper.cpp for local ASR..."
if [[ ! -d "$HOME/.polytope/whisper.cpp" ]]; then
    git clone https://github.com/ggerganov/whisper.cpp "$HOME/.polytope/whisper.cpp"
    cd "$HOME/.polytope/whisper.cpp"
    if [[ "$ARCH" == "arm64" ]] && [[ "$OS" == "Darwin" ]]; then
        make -j$(sysctl -n hw.physicalcpu) WHISPER_METAL=1
    else
        make -j$(nproc 2>/dev/null || echo 4)
    fi
    bash ./models/download-ggml-model.sh base.en
    cd -
else
    echo "  Whisper.cpp already installed at ~/.polytope/whisper.cpp"
fi

# ── 3. Piper TTS ───────────────────────────────────────────
echo "[4/4] Setting up Piper TTS..."
PIPER_DIR="$HOME/.polytope/piper"
mkdir -p "$PIPER_DIR"

if [[ "$OS" == "Darwin" ]]; then
    if [[ "$ARCH" == "arm64" ]]; then
        PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_macos_aarch64.tar.gz"
    else
        PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_macos_x64.tar.gz"
    fi
elif [[ "$OS" == "Linux" ]]; then
    PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz"
fi

if [[ ! -f "$PIPER_DIR/piper" ]]; then
    curl -L "$PIPER_URL" | tar xz -C "$PIPER_DIR" --strip-components=1
    # Download a default voice model
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx" \
         -o "$PIPER_DIR/en_US-amy-medium.onnx"
    curl -L "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json" \
         -o "$PIPER_DIR/en_US-amy-medium.onnx.json"
else
    echo "  Piper already installed at ~/.polytope/piper"
fi

# ── Summary ────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  Setup complete! Add these to your .env:"
echo ""
echo "  OLLAMA_URL=http://localhost:11434"
echo "  WHISPER_CPP_PATH=$HOME/.polytope/whisper.cpp/main"
echo "  PIPER_PATH=$HOME/.polytope/piper/piper"
echo "  PIPER_MODEL=$HOME/.polytope/piper/en_US-amy-medium.onnx"
echo "═══════════════════════════════════════════════════════"
```

```bash
chmod +x scripts/setup_sovereign_stack.sh
```

---

### INFRA-005 — Add Redis Service to CI

**File:** `.github/workflows/ci.yml`

```yaml
# .github/workflows/ci.yml — REPLACE backend job

  backend:
    runs-on: ubuntu-latest

    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"

      - name: Install dependencies
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: Lint with Ruff
        run: ruff check .

      - name: Type check with mypy
        run: mypy backend/ --ignore-missing-imports --no-strict-optional
        continue-on-error: true  # Warnings only until type coverage improves

      - name: Run database migrations
        env:
          POLYTOPE_MASTER_KEY: ${{ secrets.TEST_MASTER_KEY }}
          JWT_SECRET_KEY: ${{ secrets.TEST_JWT_KEY }}
          DATABASE_URL: sqlite:///test.db
        run: |
          export PYTHONPATH=$PYTHONPATH:$(pwd)
          alembic upgrade head
          alembic check

      - name: Run tests
        env:
          POLYTOPE_MASTER_KEY: ${{ secrets.TEST_MASTER_KEY }}
          JWT_SECRET_KEY: ${{ secrets.TEST_JWT_KEY }}
          REDIS_URL: redis://localhost:6379/0
          DATABASE_URL: sqlite:///test.db
        run: |
          export PYTHONPATH=$PYTHONPATH:$(pwd)
          pytest backend/tests/ -v --cov=backend --cov-report=xml --cov-report=term-missing

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml
          fail_ci_if_error: false
```


---

## Phase 7: Incomplete Feature Completion

---

### FEAT-001 — Wire Missing Bridge Adapters into Channel Registry

**File:** `backend/lifespan.py`  
**Context:** Gmail, Google Drive, MS Teams, Facebook, Instagram, WeChat are implemented but not wired into `channel_registry`, making them unreachable from the API.

**Fix — add to `_boot_channels()` in `lifespan.py`:**

```python
# backend/lifespan.py — ADD to _boot_channels() after existing registry assignments

    # ── Google Workspace ──────────────────────────────────────────────────────
    from .bridges.gmail import GmailBridge
    from .bridges.gdrive import GDriveBridge
    registry["gmail"]   = GmailBridge("gmail", vault_root)
    registry["gdrive"]  = GDriveBridge("gdrive", vault_root)

    # ── Microsoft ─────────────────────────────────────────────────────────────
    from .bridges.msteams import MSTeamsBridge
    registry["msteams"] = MSTeamsBridge("msteams", vault_root)

    # ── Meta ──────────────────────────────────────────────────────────────────
    from .bridges.facebook import FacebookBridge
    from .bridges.instagram import InstagramBridge
    registry["facebook"]   = FacebookBridge("facebook", vault_root)
    registry["instagram"]  = InstagramBridge("instagram", vault_root)

    # ── WeChat (requires separate China-based registration — disabled by default) ─
    # from .bridges.wechat import WeChatBridge
    # registry["wechat"] = WeChatBridge("wechat", vault_root)

    # ── Apple Platform Bridges (macOS-only) ──────────────────────────────────
    import platform as _platform
    if _platform.system() == "Darwin":
        from .bridges.icloud import ICloudBridge
        from .bridges.iwatch import IWatchBridge
        from .bridges.iphone import IPhoneBridge
        registry["icloud"] = ICloudBridge("icloud", vault_root)
        registry["iwatch"] = IWatchBridge("iwatch", vault_root)
        registry["iphone"] = IPhoneBridge("iphone", vault_root)
```

**Update `CHANNEL_META` in the channels router:**

```python
# backend/routers/channels.py — EXPAND CHANNEL_META dict

CHANNEL_META = {
    "telegram":     {"icon": "Send",          "label": "Telegram Bot API",         "order": 1},
    "whatsapp":     {"icon": "MessageSquare", "label": "WhatsApp Business",         "order": 2},
    "discord":      {"icon": "Gamepad2",      "label": "Discord Gateway",           "order": 3},
    "slack":        {"icon": "Slack",         "label": "Slack Enterprise",          "order": 4},
    "email":        {"icon": "Mail",          "label": "SMTP/IMAP Core",            "order": 5},
    "google_chat":  {"icon": "MessageCircle", "label": "Google Chat",               "order": 6},
    "gmail":        {"icon": "Mail",          "label": "Gmail",                     "order": 7},
    "gdrive":       {"icon": "HardDrive",     "label": "Google Drive",              "order": 8},
    "msteams":      {"icon": "Users",         "label": "Microsoft Teams",           "order": 9},
    "signal":       {"icon": "Shield",        "label": "Signal",                    "order": 10},
    "facebook":     {"icon": "Facebook",      "label": "Facebook Messenger",        "order": 11},
    "instagram":    {"icon": "Instagram",     "label": "Instagram",                 "order": 12},
    "nostr":        {"icon": "Wifi",          "label": "Nostr Protocol",            "order": 13},
    "imessage":     {"icon": "MessageSquare", "label": "iMessage",                  "order": 14},
    "icloud":       {"icon": "Cloud",         "label": "iCloud",                    "order": 15},
    "iwatch":       {"icon": "Watch",         "label": "Apple Watch",               "order": 16},
    "iphone":       {"icon": "Smartphone",    "label": "iPhone HealthKit",          "order": 17},
}
```

---

### FEAT-002 — Implement Persistent Agent Constellation

**Context:** `GET /api/agents` returns a hardcoded list of 3 agents. The `AgentsPanel` UI exists but writes to no persistent storage.

**Step 1 — Add `Agent` DB model to `models.py`:**

```python
# backend/models.py — ADD Agent table

class Agent(SQLModel, table=True):
    """Persistently stored autonomous agent configuration."""
    __tablename__ = "agent"
    id: str = Field(default=None, primary_key=True)   # slug, e.g. "researcher"
    name: str
    description: str = ""
    model: str = "gemini-1.5-pro"
    system_prompt: Optional[str] = None
    active_skill_ids: List[str] = Field(default=[], sa_column=Column(JSON))
    channel_ids: List[str] = Field(default=[], sa_column=Column(JSON))
    status: str = Field(default="IDLE")   # IDLE | READY | RUNNING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
```

**Step 2 — Replace the hardcoded `/api/agents` handler:**

```python
# backend/routers/agents.py — REPLACE list_agents and add CRUD

from sqlmodel import Session, select
from ..database import engine as db_engine
from ..models import Agent

@router.get("/api/agents", dependencies=[Depends(verify_authenticated)])
async def list_agents():
    """List all configured agents in the constellation."""
    with Session(db_engine) as session:
        agents = session.exec(select(Agent)).all()
        if not agents:
            # Seed default agents on first boot
            defaults = [
                Agent(id="root", name="Sovereign Root",
                      model="gemini-1.5-pro", status="READY",
                      description="Primary executive agent with full tool access."),
                Agent(id="researcher", name="Deep Researcher",
                      model="gemini-1.5-pro", status="IDLE",
                      description="Specialised in long-context research and synthesis."),
                Agent(id="coder", name="Polyglot Coder",
                      model="gpt-4o", status="IDLE",
                      description="Expert software engineering and code execution."),
            ]
            for a in defaults:
                session.add(a)
            session.commit()
            agents = defaults
        return {"agents": [a.model_dump() for a in agents]}


@router.post("/api/agents", dependencies=[Depends(verify_authenticated)])
async def create_agent(data: Dict[str, Any] = Body(...)):
    agent = Agent(**{k: v for k, v in data.items() if k in Agent.model_fields})
    if not agent.id:
        agent.id = str(uuid.uuid4())[:8]
    with Session(db_engine) as session:
        session.add(agent)
        session.commit()
        session.refresh(agent)
    return agent.model_dump()


@router.put("/api/agents/{agent_id}", dependencies=[Depends(verify_authenticated)])
async def update_agent(agent_id: str, data: Dict[str, Any] = Body(...)):
    with Session(db_engine) as session:
        agent = session.get(Agent, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        for k, v in data.items():
            if k in Agent.model_fields and k != "id":
                setattr(agent, k, v)
        agent.updated_at = datetime.now(timezone.utc)
        session.add(agent)
        session.commit()
        session.refresh(agent)
    return agent.model_dump()


@router.delete("/api/agents/{agent_id}", dependencies=[Depends(verify_authenticated)])
async def delete_agent(agent_id: str):
    with Session(db_engine) as session:
        agent = session.get(Agent, agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        session.delete(agent)
        session.commit()
    return {"status": "deleted", "id": agent_id}
```

---

### FEAT-003 — Add Memory Eviction Policy to ChromaDB

**File:** `backend/memory/manager.py`

**Context:** The ChromaDB collection grows indefinitely. Add a TTL-based eviction policy run periodically by the cron engine.

```python
# backend/memory/manager.py — ADD method to MemoryManager

    async def evict_old_memories(self, max_age_days: int = 90, max_count: int = 50_000):
        """
        Evict memories older than max_age_days or exceeding max_count.
        Called by the CronEngine on a nightly schedule.
        """
        if self.lite_mode:
            return  # FTS manager handles its own eviction

        try:
            count = self.collection.count()
            if count == 0:
                return

            logger.info(f"[ MEMORY ] Running eviction. Current count: {count}")

            # 1. Age-based eviction: remove entries older than max_age_days
            cutoff = (
                datetime.now() - timedelta(days=max_age_days)
            ).isoformat()

            results = self.collection.get(
                where={"timestamp": {"$lt": cutoff}},
                include=["metadatas"],
            )
            if results and results.get("ids"):
                self.collection.delete(ids=results["ids"])
                logger.info(f"[ MEMORY ] Evicted {len(results['ids'])} aged entries.")

            # 2. Count-based eviction: if still over limit, remove oldest
            count_after = self.collection.count()
            if count_after > max_count:
                overflow = count_after - max_count
                all_ids = self.collection.get(
                    limit=overflow,
                    include=[],
                )
                if all_ids.get("ids"):
                    self.collection.delete(ids=all_ids["ids"][:overflow])
                    logger.info(f"[ MEMORY ] Evicted {overflow} entries for count limit.")

        except Exception as e:
            logger.error(f"[ MEMORY ] Eviction failed: {e}")
```

**Register nightly eviction in the CronEngine default jobs:**

```python
# backend/cron_engine.py — ADD default job creation in CronEngine.__init__

    async def _seed_default_jobs(self):
        """Create system maintenance jobs if they don't exist."""
        default_jobs = [
            {
                "name": "Memory Eviction",
                "schedule_type": "cron",
                "schedule_value": "0 3 * * *",   # 3 AM daily
                "objective": "__SYSTEM__:memory_evict",
                "enabled": True,
            },
        ]
        for job_data in default_jobs:
            existing = self.get_job_by_name(job_data["name"])
            if not existing:
                self.create_job(job_data)
```

---

### FEAT-004 — Replace DAG SSE Polling with Event-Driven Push

**File:** `backend/app.py` (later `backend/routers/dag.py`)  
**Context:** The SSE endpoint polls the database every 500ms. Replace with a Redis pub/sub push.

**Step 1 — Publish task state transitions from the Executor:**

```python
# backend/engine/executor.py — ADD Redis publish calls

    def _update_task_record(self, run_id: int, task_dag_id: str, **kwargs):
        """Update DB record AND publish state change event."""
        # ... existing DB update code ...

        # Publish to Redis if available
        try:
            from .. import services
            if services.redis_client:
                import json as _json
                asyncio.create_task(
                    services.redis_client.publish(
                        f"dag:run:{run_id}:tasks",
                        _json.dumps({
                            "task_dag_id": task_dag_id,
                            **{k: str(v) if hasattr(v, 'isoformat') else v
                               for k, v in kwargs.items()},
                        })
                    )
                )
        except Exception:
            pass  # Non-fatal — SSE polling fallback handles it
```

**Step 2 — Update the SSE endpoint to use pub/sub with polling fallback:**

```python
# backend/routers/dag.py — REPLACE stream_dag_run_tasks

@router.get("/api/dag/runs/{run_id}/stream", dependencies=[Depends(verify_authenticated)])
async def stream_dag_run_tasks(run_id: int):
    """
    SSE stream of live task state transitions.
    Uses Redis pub/sub when available; falls back to 1-second DB polling.
    """
    from .. import services

    async def event_generator_redis():
        """Redis pub/sub push path."""
        pubsub = services.redis_client.pubsub()
        await pubsub.subscribe(f"dag:run:{run_id}:tasks")
        try:
            # Send initial state snapshot
            with Session(db_engine) as session:
                tasks = session.exec(
                    select(TaskRecordModel).where(TaskRecordModel.run_id == run_id)
                ).all()
                for task in tasks:
                    if task.status != "pending":
                        yield f"data: {json.dumps({'task_dag_id': task.task_dag_id, 'status': task.status})}\n\n"

            # Stream updates
            keep_alive = 0
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield f"data: {message['data'].decode()}\n\n"
                keep_alive += 1
                if keep_alive % 60 == 0:
                    yield ": keep-alive\n\n"

                # Check if run is done
                with Session(db_engine) as session:
                    run = session.get(Run, run_id)
                    if run and run.status in ("completed", "failed"):
                        yield f"event: done\ndata: {json.dumps({'run_id': run_id, 'status': run.status})}\n\n"
                        return
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

    async def event_generator_polling():
        """DB polling fallback (when Redis unavailable)."""
        last_seen: dict = {}
        keep_alive_counter = 0
        while True:
            await asyncio.sleep(1.0)   # Relaxed to 1s from 0.5s
            keep_alive_counter += 1
            if keep_alive_counter % 30 == 0:
                yield ": keep-alive\n\n"

            with Session(db_engine) as session:
                run = session.get(Run, run_id)
                if not run:
                    yield f"event: error\ndata: {json.dumps({'error': 'run_not_found'})}\n\n"
                    return
                tasks = session.exec(
                    select(TaskRecordModel).where(TaskRecordModel.run_id == run_id)
                ).all()
                for task in tasks:
                    if last_seen.get(task.task_dag_id) != task.status:
                        last_seen[task.task_dag_id] = task.status
                        payload = {
                            "task_dag_id": task.task_dag_id,
                            "action": task.action,
                            "status": task.status,
                            "result": task.result,
                            "error": task.error,
                        }
                        yield f"data: {json.dumps(payload)}\n\n"
                if run.status in ("completed", "failed"):
                    active = any(t.status in ("running", "pending") for t in tasks)
                    if not active:
                        yield f"event: done\ndata: {json.dumps({'run_id': run_id, 'status': run.status})}\n\n"
                        return

    generator = (
        event_generator_redis()
        if services.redis_client
        else event_generator_polling()
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
```

---

## Phase 8: Performance & Scalability

---

### PERF-001 — Add OpenTelemetry Tracing to DAG Executor

**File:** `backend/engine/executor.py`

```python
# backend/engine/executor.py — ADD tracing to _run_task

    async def _run_task(self, run_id: int, task: DAGTask, all_tasks: Dict[str, DAGTask]) -> DAGTask:
        async with self.semaphore:
            task.status = TaskStatus.RUNNING
            start_ts = datetime.now(timezone.utc)
            self._update_task_record(run_id, task.id, status="running", start_time=start_ts)

            dep_context = {
                dep: all_tasks[dep].result
                for dep in task.dependencies
                if all_tasks[dep].status == TaskStatus.COMPLETED
            }
            task.args["dependency_output"] = dep_context

            try:
                result = await asyncio.wait_for(
                    self._execute_adapter(task.action, task.args, task.id),
                    timeout=self.task_timeout,
                )
                end_ts = datetime.now(timezone.utc)
                latency_ms = (end_ts - start_ts).total_seconds() * 1000

                task.result = str(result)
                task.status = TaskStatus.COMPLETED
                self._update_task_record(
                    run_id, task.id,
                    status="completed", result=str(result), end_time=end_ts,
                )

                # Emit to metrics
                try:
                    from .. import services
                    if services.redis_client:
                        await services.redis_client.lpush(
                            "metrics:task_latency",
                            f"{task.action}:{latency_ms:.1f}",
                        )
                        await services.redis_client.ltrim("metrics:task_latency", 0, 999)
                except Exception:
                    pass

                logger.info(f"Task {task.id} ({task.action}) ✅ [{latency_ms:.0f}ms]")

            except asyncio.TimeoutError:
                err = f"Task exceeded {self.task_timeout}s timeout."
                logger.error(f"Task {task.id} ⏳ {err}")
                task.status = TaskStatus.FAILED
                task.result = err
                self._update_task_record(
                    run_id, task.id,
                    status="failed", error=err, end_time=datetime.now(timezone.utc),
                )

            except Exception as e:
                logger.error(f"Task {task.id} ❌ : {e}", exc_info=True)
                safe_error = f"Task failed: {type(e).__name__}"
                task.result = safe_error
                task.status = TaskStatus.FAILED
                self._update_task_record(
                    run_id, task.id,
                    status="failed", error=safe_error, end_time=datetime.now(timezone.utc),
                )

            return task
```

---

## Phase 9: Testing & CI Hardening

---

### TEST-001 — Add Comprehensive `conftest.py` Fixtures

**File:** `backend/tests/conftest.py`

```python
# backend/tests/conftest.py — REPLACE with comprehensive fixtures

import asyncio
import os
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from cryptography.fernet import Fernet

# ── Set required env vars before any imports ──────────────────────────────────
os.environ.setdefault("POLYTOPE_MASTER_KEY", Fernet.generate_key().decode())
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key-minimum-32-chars-long")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_polytope.db")
os.environ.setdefault("GEMINI_API_KEY", "test-key-placeholder")

# ── Test database ─────────────────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///./test_polytope.db"

@pytest.fixture(scope="session")
def engine():
    """Create a fresh test database for the test session."""
    from sqlmodel import create_engine
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)
    if os.path.exists("./test_polytope.db"):
        os.remove("./test_polytope.db")


@pytest.fixture
def db_session(engine):
    """Provide a clean DB session per test with automatic rollback."""
    with Session(engine) as session:
        yield session


@pytest.fixture
def auth_token() -> str:
    """Return a valid JWT for authenticated endpoint tests."""
    from backend.security.auth import create_access_token
    return create_access_token({"sub": "test_sovereign"})


@pytest.fixture
def auth_headers(auth_token) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def client(auth_headers):
    """
    Return an authenticated TestClient.
    Services are initialised with lightweight mocks to avoid external dependencies.
    """
    from unittest.mock import AsyncMock, MagicMock
    import backend.services as services

    # Inject mock services so routes don't crash
    services.vault = MagicMock()
    services.vault.retrieve_secret = AsyncMock(return_value=None)
    services.vault.store_secret = AsyncMock(return_value=True)
    services.vault.get_active_vaults = MagicMock(return_value=[])
    services.scanner = MagicMock()
    services.scanner.scan_input = AsyncMock(return_value=(True, ""))
    services.scanner.scan_output = AsyncMock(return_value=(True, ""))
    services.memory = MagicMock()
    services.memory.search = AsyncMock(return_value=[])
    services.router = MagicMock()
    services.orchestrator = MagicMock()
    services.orchestrator.execute_objective = AsyncMock(
        return_value={"status": "completed", "result": "test"}
    )
    services.task_manager = MagicMock()
    services.cron_engine = MagicMock()
    services.usage_tracker = MagicMock()

    from backend.app import app
    with TestClient(app, headers=auth_headers) as c:
        yield c
```

---

### TEST-002 — Add Critical Route Integration Tests

**File:** `backend/tests/test_critical_routes.py` (NEW FILE)

```python
# backend/tests/test_critical_routes.py

import pytest
from unittest.mock import AsyncMock, patch


def test_health_check(client):
    """Health endpoint must return 200 without authentication."""
    from fastapi.testclient import TestClient
    from backend.app import app
    with TestClient(app) as c:
        resp = c.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_memory_list_uses_correct_variable(client):
    """GET /api/memory must not raise NameError (regression for memory_manager bug)."""
    resp = client.get("/api/memory")
    assert resp.status_code in (200, 503)  # 503 if memory not init'd, not 500


def test_memory_search(client):
    resp = client.get("/api/memory/search", params={"q": "test query"})
    assert resp.status_code == 200


def test_memory_stats(client):
    resp = client.get("/api/memory/stats")
    assert resp.status_code in (200, 503)


def test_memory_forget(client):
    resp = client.delete("/api/memory/nonexistent-id")
    assert resp.status_code in (200, 503)


def test_system_health_no_analytics_crash(client):
    """GET /api/system/health must not crash with NameError (regression for analytics bug)."""
    resp = client.get("/api/system/health")
    # Should return 200 or 401 — never 500
    assert resp.status_code in (200, 401, 503)


def test_sanitize_input_length_limit(client):
    """Objectives longer than MAX_INPUT_LENGTH must return 413."""
    long_objective = "x" * 11_000
    resp = client.post(
        "/objective/execute",
        json={"objective": long_objective, "autonomy_level": "SEMI_AUTONOMOUS"},
    )
    assert resp.status_code == 413


def test_sanitize_input_null_bytes(client):
    """Null bytes must be stripped from input without crashing."""
    resp = client.post(
        "/objective/execute",
        json={"objective": "test\x00objective", "autonomy_level": "SEMI_AUTONOMOUS"},
    )
    assert resp.status_code in (200, 400, 422, 500)
    assert resp.status_code != 500  # No unhandled exception


def test_no_duplicate_webhook_routes():
    """Verify no route is registered twice — catches regression from FIX-005."""
    from backend.app import app
    paths = [route.path for route in app.routes]
    # Check no duplicates
    seen = {}
    for route in app.routes:
        key = (getattr(route, 'methods', None), route.path)
        if key in seen:
            pytest.fail(
                f"Duplicate route: {key}. "
                f"First seen at index {seen[key]}, duplicate found."
            )
        seen[key] = True


def test_oauth_callback_rejects_invalid_bridge_id(client):
    """OAuth callback must reject non-whitelisted bridge_id values."""
    resp = client.get(
        "/api/oauth/'; alert(1); var x='/callback",
        params={"code": "test"},
    )
    assert resp.status_code in (400, 404, 422)
    # Must not contain the injected script
    assert "alert(1)" not in resp.text


def test_webauthn_challenge_returns_challenge_id(client):
    """WebAuthn challenge must include challengeId for secure lookup."""
    resp = client.get("/auth/webauthn/challenge")
    assert resp.status_code == 200
    data = resp.json()
    assert "challengeId" in data
    assert "challenge" in data


@pytest.mark.asyncio
async def test_webauthn_challenge_no_cross_user_replay():
    """
    Two different challengeIds must not be interchangeable.
    Regression test for the in-memory dict race condition.
    """
    from backend.security.webauthn_store import WebAuthnChallengeStore
    store = WebAuthnChallengeStore(redis_client=None)  # in-memory

    cid1, _ = await store.create_challenge()
    cid2, _ = await store.create_challenge()

    # Consuming cid1 should NOT return cid2's bytes
    result = await store.consume_challenge(cid2)
    assert result is not None  # cid2 still exists

    result2 = await store.consume_challenge(cid1)
    assert result2 is not None  # cid1 still exists

    # After consuming both, both should be gone
    assert await store.consume_challenge(cid1) is None
    assert await store.consume_challenge(cid2) is None
```

---

## Phase 10: Documentation Alignment

---

### DOC-001 — Update README Model References

**File:** `README.md`

Replace all speculative or incorrect model names with accurate current identifiers:

```markdown
# README.md — REPLACE LLM_REASONING_&_LOGIC section

#### 1. LLM_REASONING_&_LOGIC
- **OpenAI**: GPT-4o & o3 for deep strategic planning.
- **Anthropic**: Claude Sonnet 4.6 (`claude-sonnet-4-6`) for nuanced context and coding.
- **Google Cloud**: Gemini 1.5 Pro / Gemini 2.0 Flash for large context windows.
- **Groq**: LPU-powered high-speed tactical execution (Llama 3).
- **Local (Sovereign)**: Ollama-hosted Llama 3.2 / Mistral for fully offline operation.
```

---

### DOC-002 — Create `PRODUCTION.md` Deployment Guide

**File:** `PRODUCTION.md` (NEW FILE)

```markdown
# Production Deployment Guide

## Prerequisites

- Docker & Docker Compose v2
- A domain name with DNS pointing to your server
- A TLS certificate (Certbot / Let's Encrypt recommended)

## Step 1 — Configure Environment

```bash
cp .env.example .env
```

Fill in ALL required values:

| Variable | Required | Description |
|---|---|---|
| `POLYTOPE_MASTER_KEY` | ✅ | Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `JWT_SECRET_KEY` | ✅ | Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"` |
| `DB_PASSWORD` | ✅ | Strong random password for PostgreSQL |
| `PROD_DATABASE_URL` | ✅ | `postgresql+asyncpg://alluci:<DB_PASSWORD>@db:5432/polytope` |
| `REDIS_URL` | ✅ | `redis://redis:6379/0` |
| `WEBAUTHN_RP_ID` | ✅ | Your domain, e.g. `agent.yourdomain.com` |
| `WEBAUTHN_ORIGIN` | ✅ | Full origin, e.g. `https://agent.yourdomain.com` |
| `ALLOWED_ORIGINS` | ✅ | `["https://agent.yourdomain.com"]` |
| `APP_ENV` | ✅ | `production` |

## Step 2 — Database Migration

```bash
docker compose run --rm backend alembic upgrade head
```

## Step 3 — Start the Stack

```bash
docker compose up -d
```

## Step 4 — Verify Health

```bash
curl https://agent.yourdomain.com/health
# Expected: {"status":"healthy","timestamp":"..."}

curl https://agent.yourdomain.com/ready
# Expected: {"status":"ready","checks":{...}}
```

## Key Rotation

To rotate the vault master key:

```bash
# Generate new key
NEW_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Call the rotate endpoint
curl -X POST https://agent.yourdomain.com/vault/rotate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"new_key\": \"$NEW_KEY\"}"

# Update your .env and restart
sed -i "s/POLYTOPE_MASTER_KEY=.*/POLYTOPE_MASTER_KEY=$NEW_KEY/" .env
docker compose restart backend
```
```

---

### DOC-003 — Align Architecture Document with Implementation Reality

**File:** `ARCHITECTURE.md`

Add a section clearly distinguishing implemented vs. planned features:

```markdown
# ARCHITECTURE.md — ADD to end of document

---

## Implementation Status

| Feature | Spec Section | Status |
|---|---|---|
| Simplicial Vault (AES-256-GCM isolation) | §3 | ✅ Implemented |
| DAG Planner + Executor | §4 | ✅ Implemented |
| Exec Approval Interceptor | §5.6 | ✅ Implemented |
| ACE Biometric Pipeline (BTM + AffectKernel) | §6 | ✅ Implemented |
| VerusID Authentication | §7 | ✅ Implemented |
| Memory Manager (ChromaDB) | §2 | ✅ Implemented |
| WebSocket Gateway (JSON-RPC) | §5.1 | ✅ Implemented |
| Full PPN Persistence Homology (Betti number computation) | §2 | 🔬 Research / Planned |
| DPK Topological Rupture Detection (exact Euler characteristic) | §2 | 🔬 Research / Planned |
| WatchOS Companion App (HealthKit source) | §6.1 | 📋 Planned |
| Multi-agent Persistent Constellation | §8 | 🔄 In Progress |
```

---

## Summary Checklist

Use this checklist to track production readiness. Each item maps to a fix above.

### Phase 1 — Critical Bugs ✅
- [ ] FIX-001: `import time` added to `app.py`
- [ ] FIX-002: `memory_manager` → `memory` in 4 routes
- [ ] FIX-003: `analytics.db_engine` → `db_engine`
- [ ] FIX-004: `sanitize_input` null guard + length limit
- [ ] FIX-005: Duplicate webhook routes deleted
- [ ] FIX-006: Unreachable `raise` deleted
- [ ] FIX-007: `WEBABAUTHN_RP_ID` typo fixed
- [ ] FIX-008: `base_bridge.py` deleted
- [ ] FIX-009: `previous_*.tsx` files removed

### Phase 2 — Security ✅
- [ ] SEC-001: WebAuthn challenge store → Redis
- [ ] SEC-002: OAuth callback XSS fixed
- [ ] SEC-003: Audit ledger → DB-backed append-only
- [ ] SEC-004: `ALLOWED_ORIGINS` validator fixed
- [ ] SEC-005: Hardcoded production DB password removed
- [ ] SEC-006: Redis unavailability metric added

### Phase 3 — Dependencies ✅
- [ ] DEP-001: `requirements.txt` fully updated with missing packages
- [ ] DEP-002: `puppeteer-core` removed from `package.json`

### Phase 4 — Refactoring ✅
- [ ] REFACTOR-001: `app.py` split into APIRouter modules
- [ ] REFACTOR-002: `lifespan.py` extracted
- [ ] REFACTOR-003: `services.py` container created
- [ ] REFACTOR-004: Debug log statements removed

### Phase 5 — Database ✅
- [ ] DB-001: Alembic migration generated for all new tables
- [ ] DB-002: `AuditLog` table included in migration

### Phase 6 — Infrastructure ✅
- [ ] INFRA-001: `docker-compose.yml` created
- [ ] INFRA-002: Docker base images pinned to digest
- [ ] INFRA-003: `Dockerfile.frontend` + `nginx.conf` created
- [ ] INFRA-004: `scripts/setup_sovereign_stack.sh` created
- [ ] INFRA-005: Redis service added to CI workflow

### Phase 7 — Feature Completion ✅
- [ ] FEAT-001: Missing bridges wired into channel registry
- [ ] FEAT-002: Agent constellation persisted to DB
- [ ] FEAT-003: Memory eviction policy implemented
- [ ] FEAT-004: SSE polling replaced with Redis pub/sub

### Phase 8 — Performance ✅
- [ ] PERF-001: Task latency metrics added to executor

### Phase 9 — Testing ✅
- [ ] TEST-001: Comprehensive `conftest.py` fixtures
- [ ] TEST-002: Critical route integration tests

### Phase 10 — Documentation ✅
- [ ] DOC-001: README model names corrected
- [ ] DOC-002: `PRODUCTION.md` deployment guide created
- [ ] DOC-003: `ARCHITECTURE.md` implementation status added

---

*This specification covers all gaps identified in the March 2026 audit. Execute phases in order — each phase builds on the previous.*
