# Alluci Sovereign Agent — Full Code Audit & Production Readiness Report

**Repository:** `alluci-sovereign-agent-main`  
**Audit Date:** March 2026  
**Codebase Size:** ~1,169 files | Python (FastAPI) backend + React/TypeScript frontend  
**Assessment:** Advanced Prototype → Production-Readiness Gap Analysis

---

## Table of Contents

1. [What It Is](#1-what-it-is)
2. [How It Works — Architecture Deep Dive](#2-how-it-works--architecture-deep-dive)
3. [What Is Genuinely Innovative](#3-what-is-genuinely-innovative)
4. [Critical Bugs — Will Break in Production](#4-critical-bugs--will-break-in-production)
5. [Security Issues](#5-security-issues)
6. [Incomplete & Stub Implementations](#6-incomplete--stub-implementations)
7. [Code Quality Issues](#7-code-quality-issues)
8. [Infrastructure & DevOps Gaps](#8-infrastructure--devops-gaps)
9. [Performance & Scalability Concerns](#9-performance--scalability-concerns)
10. [The Mathematical Architecture — Honest Assessment](#10-the-mathematical-architecture--honest-assessment)
11. [Prioritised Remediation Roadmap](#11-prioritised-remediation-roadmap)
12. [Overall Verdict](#12-overall-verdict)

---

## 1. What It Is

Alluci Sovereign Agent is an ambitious **self-sovereign AI executive assistant** — a locally-hosted, privacy-first system that acts as a single intelligent hub for your entire digital life. The core thesis is that AI assistants should operate under *your* cryptographic control, not a cloud provider's.

**In practice, it is:**

- A **FastAPI Python backend** daemon ("Polytope Executive Daemon") that orchestrates LLM reasoning, tool execution, and multi-channel communication.
- A **React/TypeScript frontend** (Vite-based) providing a rich admin UI — terminal, DAG visualiser, bridge manager, analytics, soul customisation, and more.
- A **multi-bridge communication hub** with adapters for 18+ platforms: Telegram, WhatsApp, Discord, Slack, Signal, iMessage, Gmail, Google Drive, MS Teams, Nostr, WeChat, Instagram, Facebook, X/Twitter, and more.
- An **agentic task engine** that converts natural-language objectives into Directed Acyclic Graph (DAG) plans, executes them through typed "adapter" tools, and self-corrects on failure.
- A **biometric-aware system** (the Affective Computing Engine, "ACE") that reads Apple Watch/HealthKit data and adjusts the agent's behaviour based on your physiological state — silencing notifications during deep work, throttling tasks during high stress.
- A **cryptographic identity layer** built on VerusID (a blockchain-anchored decentralised identity) and a local "Simplicial Vault" (AES-256-GCM encrypted key store).

The agent is designed to run entirely on local hardware (Apple Silicon, x86 desktop, or Raspberry Pi) with fallback to cloud APIs, embodying a "sovereign-first" philosophy.

---

## 2. How It Works — Architecture Deep Dive

### 2.1 The Backend Stack

```
FastAPI App (app.py)
  ├── Lifespan Manager — sequential boot of all services
  ├── VaultManager — AES-256-GCM + RSA-4096 local secret store
  ├── ModelRouter — LLM provider fan-out (Gemini → OpenAI → Groq → Ollama)
  ├── AffectiveEngine (ACE) — biometric telemetry → flow state
  ├── ExecutiveOrchestrator
  │     ├── Planner — LLM → DAG (JSON steps with typed tool IDs)
  │     ├── Executor — async parallel DAG runner with semaphore + retry
  │     ├── Critic — quality gate between planning and execution
  │     └── PPN/DPK — "Polytopological Persistence Network" stability logic
  ├── SkillManager — user-defined cognitive modules (.polytype packages)
  ├── MemoryManager — ChromaDB vector store for semantic recall
  ├── CronEngine — scheduled task execution
  ├── Channel Registry — 18 bridge adapters
  ├── WebSocket Gateways — sovereign chat (/ws/sovereign) + JSON-RPC admin (/ws/admin)
  └── Analytics/UsageTracker — per-session token cost accounting
```

### 2.2 The Execution Loop

1. User submits a natural-language objective via the terminal UI.
2. The `GuardrailScanner` sanitises the input for prompt injection.
3. The `Planner` calls the LLM with the Soul Manifest context + ACE affective tension and receives a structured JSON DAG.
4. The `Critic` scores the plan; if quality is below threshold, the plan is regenerated.
5. The `Executor` runs the DAG: tasks with satisfied dependencies execute concurrently (up to `MAX_CONCURRENT_TASKS`), with timeouts and exponential-backoff retries.
6. For sensitive tools (shell, file write, DB write), the `ExecApprovalManager` pauses execution and pushes a prompt to the admin WebSocket for human approval.
7. Results propagate as dependency context to downstream tasks.
8. The `GuardrailScanner` scans the output for PII/secret leakage before returning.

### 2.3 The Frontend

The React UI is feature-rich and includes:
- **Terminal/CommandBar** — direct objective entry with streaming LLM output.
- **VisualDAGEditor** — real-time SSE-powered visualisation of running task graphs.
- **BridgeCenter** — OAuth flow launcher + connection status for all 18 channels.
- **SoulPreferencesPanel / PersonalityField** — personality customisation with live preview.
- **AffectiveEnginePanel** — biometric dashboard (HR, HRV, flow state).
- **SkillBuilderWizard / SkillGrid** — skill creation and marketplace.
- **AnalyticsPanel** — token cost charts, session history, CSV export.
- **CronPanel** — visual cron job management.
- **LogPanel** — real-time WebSocket log streaming.
- **Wallet/Identity Panels** — VerusID blockchain interaction, DeFi AMM, mining controls.

### 2.4 The Simplicial Vault

Each external bridge runs in its own cryptographically isolated directory (`~/.polytope/vaults/{bridge_id}`). The `VaultManager` uses:
- **AES-256-GCM** for secrets (with a versioned prefix byte for future key rotation).
- **RSA-4096** for asymmetric signing operations (skill manifest signing).
- **OS Keychain integration** (`keyring`) to avoid storing the master key in `.env` on macOS.
- **VDXF anchoring** — optionally hashes the audit ledger to the Verus blockchain for tamper-proof immutability.

---

## 3. What Is Genuinely Innovative

### 3.1 ✅ Affective Computing Integration
The biometric-aware agent behaviour is a legitimate research concept implemented with thoughtful domain modelling. The `BTMMapper`, `AffectKernel`, and `EntropyMonitor` compose a coherent pipeline: raw Apple Watch telemetry (HR, HRV, skin conductance, sleep efficiency) → affective state (valence/arousal/tension) → flow mode (STANDARD / DEEP_WORK / RECOVERY_MODE / PEAK_PERFORMANCE) → agent autonomy adjustment. This is genuinely novel in consumer AI agent tooling.

### 3.2 ✅ Self-Sovereign Identity as Auth
Using VerusID (a UTXO-based blockchain identity) as the authentication layer — generating a challenge QR code, having the mobile wallet sign it, and verifying the cryptographic signature — is a real decentralised alternative to OAuth that doesn't rely on any third-party identity provider. The VDXF (Verus Data eXchange Format) audit anchoring gives you an immutable, on-chain record of every agent action.

### 3.3 ✅ DAG-Based Agentic Planning with Topology Validation
The planner doesn't just generate a list of steps — it builds a proper DAG with dependency validation (cycle detection via DFS, phantom dependency pruning, self-dependency rejection). The executor then runs nodes in parallel based on dependency resolution, with upstream failure propagation. This is production-grade agentic execution architecture.

### 3.4 ✅ Exec Approval Interceptor
The `ExecApprovalManager` pattern — where a running agent pauses before executing sensitive tools (shell, DB writes, file overwrites) and waits for a human approval signal over WebSocket — is an elegant human-in-the-loop safety mechanism. The policy system (persist allow/deny decisions) allows progressive trust building.

### 3.5 ✅ Harmonic Lattice / PPN Architecture
The `PolytopologicalPersistenceNetwork` (PPN) concept — using persistence homology Betti numbers to assess the "topological soundness" of an execution plan, and halting via the Discrete Projection Kernel on "topological rupture" — is an ambitious and original framing for agentic plan stability, even if the current implementation is partially aspirational.

### 3.6 ✅ Simplicial Vault Isolation Pattern
Giving each bridge its own vault subdirectory with separate encryption context is a strong security architecture. Combined with the `GuardrailScanner` scanning both input and output (including checking output against all active vault secrets to detect key leakage), this creates meaningful defence-in-depth.

### 3.7 ✅ Soul Manifest + Skill System
The "Soul Manifest" — a user-defined identity, voice, reasoning style, and directive set that's injected into every LLM context — combined with a cryptographically-signed skill package system (`.polytype` packages) is a thoughtful approach to personalised AI ownership.

### 3.8 ✅ Lite Mode Auto-Detection
The automatic detection of low-RAM environments (< 2.5 GB → `LITE_MODE`) and ARM hardware (Raspberry Pi detection) shows genuine consideration for local/edge deployment scenarios, not just cloud.

---

## 4. Critical Bugs — Will Break in Production

### 4.1 🔴 `memory_manager` NameError — Runtime Crash
**File:** `backend/app.py`, lines 1566–1589

The global variable is named `memory` (initialised in lifespan), but four route handlers reference `memory_manager`:

```python
# Line 1566 — crashes with NameError on every /api/memory GET
return memory_manager.collection.get(limit=limit)

# Line 1570 — crashes on /api/memory/search
return await memory_manager.recall(q, top_k=10)

# Line 1589 — crashes on DELETE /api/memory/{id}
await memory_manager.forget(entry_id)
```

**Fix:** Replace `memory_manager` with `memory` throughout, or introduce an alias at the top of the app module.

### 4.2 🔴 `time` Module Not Imported — Runtime Crash
**File:** `backend/app.py`, lines 315, 318, 322, 600

`time.time()` is used in the metrics middleware and health endpoint, but `import time` is missing from the top-level imports.

```python
# Line 315 — NameError on first HTTP request
start_time = time.time()
```

**Fix:** Add `import time` to the import block.

### 4.3 🔴 `analytics` NameError in Health Endpoint
**File:** `backend/app.py`, line 569

```python
with Session(analytics.db_engine) as session:  # 'analytics' is undefined
```

The local variable `analytics` is never imported or assigned in `app.py`; the correct reference is `db_engine` (already imported directly).

**Fix:** Replace `analytics.db_engine` with `db_engine`.

### 4.4 🔴 `scanner` Used Before Initialisation
**File:** `backend/app.py`, line 89 (`sanitize_input` function)

`scanner` is a module-level variable initialised to `None` and only created inside the `lifespan()` context manager. However, `sanitize_input` is a top-level async function that references `scanner` immediately. If any request arrives before the lifespan completes (or if lifespan fails midway), this crashes with `AttributeError: 'NoneType' object has no attribute 'scan_input'`.

**Fix:** Add a null guard: `if not scanner: return text` or initialise `scanner` eagerly at module level with a default passthrough implementation.

### 4.5 🔴 Duplicate Webhook Route Registrations
**File:** `backend/app.py`

Both `/api/webhook/telegram/{token}` (line 1893) and `/webhook/telegram/{token}` (line 2258) are registered — as are duplicate WhatsApp webhook routes. FastAPI silently uses the first registered route, making the second dead code that confuses webhook configuration and could cause security issues (the duplicates have slightly different validation logic).

**Fix:** Remove the duplicate set (lines 2258–2306) and standardise on `/api/webhook/{platform}` paths.

### 4.6 🔴 Unreachable `raise HTTPException` — Dead Code
**File:** `backend/app.py`, lines 1492–1493 (Gemini proxy handler)

```python
    except HTTPException:
        raise
        raise HTTPException(status_code=500, detail="Inference request failed.")  # UNREACHABLE
```

The second `raise` statement is unreachable. This appears to be a merge artefact.

### 4.7 🔴 WebAuthn Challenge Store — Race Condition + Insecure Lookup
**File:** `backend/app.py`, lines 1157–1251

The challenge store `_webauthn_challenges` is a plain Python `dict` (not thread-safe, not distributed). Under concurrent requests:
1. Challenge collisions are possible.
2. The verification code iterates the dict and takes `break` on the first found challenge — meaning any pending challenge matches any incoming verification, allowing challenge replay across users.

**Fix:** Key challenges by a session ID returned to the client; use Redis for multi-worker deployments.

### 4.8 🟡 `WEBABAUTHN_RP_ID` Typo
**File:** `backend/app.py`, line 1173

```python
settings.WEBAUTHN_RP_ID if hasattr(settings, 'WEBABAUTHN_RP_ID') else "localhost"
```

The `hasattr` check uses `WEBABAUTHN_RP_ID` (with extra 'A') but then accesses `WEBAUTHN_RP_ID`. The condition always falls through to `"localhost"` even when the correct setting exists. WebAuthn will always use `localhost` as the RP ID regardless of configuration.

### 4.9 🟡 `wallet_service` Referenced Before Import
**File:** `backend/app.py`, line ~518 (`/api/wallet/login/status/{challenge_id}`)

`wallet_service.set_identity(result["identity"])` is called, but the `wallet_service` import (`from .verus_wallet import wallet_service`) appears later in the file (~line 2000). Python processes imports at load time so this works, but the reference in the `get_wallet_login_status` route depends on a service that may not be connected yet at call time.

---

## 5. Security Issues

### 5.1 🔴 Master Key Stored in `.env` — Default Configuration
The `POLYTOPE_MASTER_KEY` is a Fernet key required at startup. The `.env.example` instructs users to generate and store it in a `.env` file. In a truly sovereign deployment on a shared machine or in a container, this key at rest on disk (even in `.env`) represents a significant risk.

**The `_ensure_keychain_sync` method is the right idea** (OS Keychain migration) but it only runs on macOS and is purely optional. This should be the *default* and mandatory for production deployments, with explicit documentation on secure key management.

### 5.2 🔴 In-Memory WebAuthn Challenge Store
As noted in Bug 4.7 — using a process-local dict for WebAuthn challenges breaks under multi-worker uvicorn deployments (all production deployments use `--workers N > 1`). Challenges issued by Worker A cannot be verified by Worker B.

### 5.3 🟡 `sanitize_input` Only Checks `scanner` — No Length Limit
The input sanitiser runs the GuardrailScanner but imposes no maximum length limit. A malicious actor could submit a 10MB objective string, causing the LLM to consume excessive tokens (cost amplification attack) or causing timeout failures.

**Fix:** Add `if len(text) > 10000: raise HTTPException(status_code=413, detail="Objective too long")`.

### 5.4 🟡 Rate Limiter Falls Back Silently on Redis Failure
If Redis is unavailable, `FastAPILimiter` is never initialised and the `RateLimiter` dependency silently passes all requests through without limiting. This is the right fail-open behaviour for availability, but there is no alerting or metric increment when this happens.

### 5.5 🟡 `ALLOWED_ORIGINS` Validator Has a Logic Gap
The `strip_localhost_in_prod` validator reads `APP_ENV` from the raw environment variable inside the validator, but Pydantic-settings processes fields sequentially. If `APP_ENV` is set *after* `ALLOWED_ORIGINS` in the `.env` file, the validator may see a stale value.

### 5.6 🟡 OAuth Callback XSS Vector
The OAuth callback endpoints at `/api/oauth/{bridge_id}/callback` directly interpolate `bridge_id` into an inline `<script>` tag in the HTML response without sanitisation:

```python
return HTMLResponse("<script>window.opener.postMessage({ ..., bridgeId: '" + bridge_id + "', ... </script>")
```

If an attacker can craft a request with a `bridge_id` containing JavaScript (e.g., `'; alert(1); //`), this becomes a reflected XSS. The bridge_id should be validated against the known `channel_registry` keys before use.

### 5.7 🟡 Audit Ledger Truncation Policy
The audit ledger is trimmed to the last 1,000 entries in the local vault. If the VDXF blockchain anchoring is not enabled, older audit events are silently discarded. For a system claiming immutable audit trails, this needs to either persist to the DB or always require VDXF anchoring.

---

## 6. Incomplete & Stub Implementations

### 6.1 🔴 Multiple Social Bridge Adapters Are Stubs
Several bridge files exist with full method signatures but no real implementation body (confirmed by `grep -c "pass"` returning 0 but methods containing only `return {}` or `return False`). The following bridges are either not in `channel_registry` at boot (not wired) or have unimplemented methods:

| Bridge | Status |
|---|---|
| `instagram.py` | Not wired into `channel_registry` in `lifespan` |
| `x_twitter.py` | Has 1 stub (`pass` in validation logic) |
| `facebook.py` | Not wired into `channel_registry` |
| `wechat.py` | Not wired; WeChat API requires China-based registration |
| `iphone.py` | Not wired; iOS HealthKit bridge is macOS-only |
| `iwatch.py` | Not wired; requires companion app |
| `icloud.py` | Not wired; requires `pyicloud` + 2FA handling |
| `gdrive.py` | Not wired; OAuth configured but adapter not in registry |
| `gmail.py` | Not wired |
| `msteams.py` | Not wired |

**The production channel_registry initialises only 9 channels**: Telegram, WhatsApp, Discord, Slack, Email, Signal, Google Chat, Nostr, iMessage.

### 6.2 🟡 Agent Constellation Is Hardcoded
The `/api/agents` endpoint returns a hardcoded list of three agents (Sovereign Root, Deep Researcher, Polyglot Coder) with no persistence. The `multi_agent_delegate` orchestrator method is implemented but agents cannot be created, configured, or persisted through the API. The `AgentsPanel` UI component exists but writes to nowhere.

### 6.3 🟡 `goals` and `sops` Engines Are Minimal Stubs
`goal_engine` and `sop_engine` are imported from `backend/goals/engine.py` and `backend/sop/engine.py`. The list/create endpoints exist but these engines are simple in-memory dicts with no persistence, no execution hooks, and no integration with the DAG planner.

### 6.4 🟡 Verus Wallet — Lite Mode Is the Real Mode
`VERUS_LITE_MODE` defaults to `True`, meaning the wallet uses the public RPC endpoint (`https://api.verus.services`) rather than a locally synced `verusd` node. The full node management endpoints (`/api/wallet/node/action`) exist but the `provision_binary` and `start`/`stop` node lifecycle management are partially implemented. A user cannot run a fully sovereign node out of the box.

### 6.5 🟡 WatchOS Companion App Is a README Placeholder
`watchos/README.md` describes the companion Apple Watch app architecture but there is no Swift/WatchKit code. The biometric data pipeline works end-to-end, but the data source (actual Apple Watch → HTTPS POST to `/api/telemetry`) requires a native app that doesn't exist yet.

### 6.6 🟡 Screen Capture Adapter Is a Playwright Bridge
`backend/adapters/screen_capture.py` uses Playwright for browser automation and screenshot capture. This is a powerful capability but the dependency (`playwright`) is pinned to 1.41.1 and the adapter requires a separate `playwright install chromium` step that is not in the Dockerfile or setup scripts.

### 6.7 🟡 `puppeteer-core` in Frontend Dependencies
`package.json` includes `puppeteer-core@^24.38.0` as a frontend dependency. Puppeteer is a Node.js server-side library and has no valid use in a browser-based React frontend. This is either an accidental dependency or a placeholder for a future Electron app layer.

---

## 7. Code Quality Issues

### 7.1 Two Competing `BridgeAdapter` Base Classes
Both `backend/bridges/base.py` and `backend/bridges/base_bridge.py` define a `BridgeAdapter` abstract base class. The concrete bridges import from `base.py` (the richer version), making `base_bridge.py` dead code that causes confusion.

**Fix:** Delete `base_bridge.py`.

### 7.2 `app.py` Is 2,400+ Lines — Monolithic God File
The entire API surface, all middleware, all route handlers, all lifespan logic, and all global state management live in a single file. This makes testing, review, and reasoning extremely difficult.

**Fix:** Extract route groups into FastAPI `APIRouter` submodules: `auth_router`, `vault_router`, `dag_router`, `channel_router`, `wallet_router`, `analytics_router`, etc.

### 7.3 Duplicate Route Handler Bodies
`/api/sessions` appears twice as a GET route (lines ~1614 and ~2365) with slightly different query parameter signatures. `/api/usage/daily` appears twice (lines ~1630 and later). FastAPI uses only the first registration — the second is silently dead.

### 7.4 Requirements Are Pinned Too Tightly (or Too Loosely)
`requirements.txt` mixes exact pins (`fastapi==0.109.0`) with range pins (`torch>=2.0.0`). `torch>=2.0.0` will pull in the latest PyTorch (potentially several GB of dependencies) on every clean install. PyTorch is only needed for the optional `gudhi` topological analysis module — it should be split into a separate `requirements-tda.txt` optional dependency group.

### 7.5 `requirements.txt` Is Incomplete
`keyring` (used in `vault.py`), `py_webauthn` (used in `app.py`), and `discord.py` (used in `bridges/discord.py`) are not in `requirements.txt`. This causes `ImportError` on a fresh install.

### 7.6 DEBUG Logging Statements Left in Lifespan
The `lifespan` function in `app.py` contains dozens of `logger.info("DEBUG: Passed X")` statements that were clearly added during development and not cleaned up:

```python
logger.info("DEBUG: Passed config_editor")
logger.info("DEBUG: Passed bridge imports")
logger.info("DEBUG: Passed channel_registry instances")
```

These pollute production logs and suggest the file was never reviewed before commit.

### 7.7 Hardcoded Model Names in Documentation vs. Reality
The `README.md` references "GPT-5.1", "Claude 4.5 / 4.6", and "Gemini 3" — none of which are real model identifiers at time of writing (Claude Sonnet 4.6 is the correct current identifier; GPT-5.1 doesn't exist; Gemini 3 is not publicly available). The actual `ModelRouter` uses `gemini-1.5-pro` and `gpt-4o`. This suggests README-driven marketing rather than documentation-driven development.

### 7.8 `previous2_BridgeCenter.tsx` and `previous_WalletPanel.tsx` Committed to Root
Two superseded component files sit in the repository root, not in `src/` or any organised directory, and not `.gitignore`d. These are development leftovers.

---

## 8. Infrastructure & DevOps Gaps

### 8.1 Dockerfile Does Not Pin Base Image
```dockerfile
FROM python:3.12-slim AS base
```

No digest pin means `docker build` can silently pull a different base image. In production, use `FROM python:3.12-slim@sha256:<digest>`.

### 8.2 No `docker-compose.yml`
The README references Docker and the `.env.example` mentions a `DB_PASSWORD` for Docker Compose, but no `docker-compose.yml` exists in the repository. A user cannot spin up the full stack (backend + Redis + PostgreSQL) without writing their own.

### 8.3 SQLite Default in Production Path
`config.py` has an `enforce_production_db` validator that converts SQLite URLs to PostgreSQL when `APP_ENV=production`. However, the fallback PostgreSQL URL is hardcoded: `postgresql+asyncpg://alluci:password@localhost/polytope` — including the literal password `password`. If `PROD_DATABASE_URL` is not set, a production deployment silently uses a default password.

### 8.4 Only One Alembic Migration
A single migration file (`cc9ee558fe12_initial_schema.py`) exists. The schema has clearly evolved substantially since this was written (Sprint 4+ additions). Running `alembic upgrade head` on an existing database will likely fail or produce an inconsistent schema.

**Fix:** Generate migration files for all schema changes since the initial migration. Add a CI step that runs `alembic check` to verify no unmigrated models exist.

### 8.5 No `docker-compose.test.yml` / Test Environment
The CI pipeline runs `pytest backend/tests/` with real environment variables but no isolated test database. Tests that touch the database will use SQLite in-memory (if configured) but there's no explicit test database fixture in `conftest.py`. Some tests appear to make live network calls (the `live/` test directories in the third-party VerusID client).

### 8.6 No Health Check for Redis in CI
The CI workflow does not spin up a Redis service, so any test that depends on `FastAPILimiter` initialisation will silently skip rate limiting in tests — masking bugs where rate limiting is a correctness invariant.

### 8.7 Setup Script Referenced But Not Present
`README.md` instructs users to run `./scripts/setup_sovereign_stack.sh` but this script does not exist in the repository. New users cannot complete the setup.

---

## 9. Performance & Scalability Concerns

### 9.1 Audit Ledger Read-Modify-Write Under Lock Is Slow
The `sync_audit_entry` endpoint reads the entire audit ledger from the vault, appends an entry, and rewrites the whole blob — all inside an `asyncio.Lock`. As the ledger grows (up to 1,000 entries), this becomes an increasingly expensive operation on every auditable action. This is a write bottleneck.

**Fix:** Write audit entries to a proper database table (already exists in the schema) and use the vault/VDXF anchoring only for periodic checkpoint hashing.

### 9.2 SSE DAG Stream Polls DB Every 500ms
The `/api/dag/runs/{run_id}/stream` SSE endpoint opens a new `Session` and queries all tasks every 500ms in a tight loop:

```python
while True:
    await asyncio.sleep(0.5)
    with Session(db_engine) as session:
        # Full query every 500ms
```

For a DAG with many tasks and many simultaneous viewers, this creates significant DB read pressure. Use a pub/sub pattern (Redis pub/sub or the existing WebSocket gateway's broadcast mechanism) to push state transitions instead of polling.

### 9.3 Memory Manifold Has No Eviction Policy
The ChromaDB vector store grows indefinitely. For a long-running sovereign agent accumulating memories over months, this will consume significant disk and degrade semantic search performance without a TTL or relevance-based eviction strategy.

### 9.4 `torch` and `gudhi` Are Heavy Dependencies for Optional Features
PyTorch and the GUDHI topological data analysis library are required at install time (`requirements.txt`) even for users who don't use the PPN/DPK manifold stability features. On a Raspberry Pi, installing these would take hours and likely exhaust disk space.

---

## 10. The Mathematical Architecture — Honest Assessment

The ARCHITECTURE.md presents an impressive mathematical formalism using persistence homology, Betti numbers, and simplicial complexes to describe the "Polytopological Persistence Network." The equations are formally correct in notation.

**However, there is a significant gap between the formalism and the implementation:**

The `backend/ace/` modules (`entropy_monitor.py`, `btm_mapper.py`, `affect_kernel.py`) implement meaningful computations (signal processing, stress scoring, arousal mapping). But the actual **PPN/DPK cycle detection** described in the architecture — computing Betti numbers on the plan's topological representation — is not implemented in the execution path. The `orchestrator.ppn.stabilizer.reset_budget()` call in the manifold patch endpoint suggests a budget-based approximation exists, but the full homological computation described in the spec is aspirational.

This is honest research-in-progress prototyping. The *concept* is sound and genuinely novel. The *implementation* is a simplified proxy for the full mathematical system. For a production release, either:
1. Implement the full TDA pipeline (requiring `gudhi`) and validate it against benchmarks, or
2. Accurately document what the stability system actually computes (Lipschitz budget + entropy monitoring) and remove the unsupported mathematical claims from public-facing documentation.

---

## 11. Prioritised Remediation Roadmap

### Phase 1: Stop the Bleeding (Week 1) — Critical Bug Fixes

These are zero-effort fixes that prevent runtime crashes:

1. **Add `import time`** to `backend/app.py`.
2. **Replace `memory_manager` with `memory`** in the 4 affected routes.
3. **Replace `analytics.db_engine` with `db_engine`** in the health endpoint.
4. **Add null guard to `sanitize_input`**: `if not scanner: return text`.
5. **Remove duplicate webhook route registrations** (keep `/api/webhook/*` prefix).
6. **Remove unreachable `raise HTTPException`** in Gemini proxy.
7. **Fix `WEBABAUTHN_RP_ID` typo** in WebAuthn challenge generation.
8. **Add missing packages to `requirements.txt`**: `keyring`, `webauthn`, `discord.py`.
9. **Delete `base_bridge.py`** (dead code causing confusion).
10. **Remove `previous_*.tsx` files** from repo root.

### Phase 2: Security Hardening (Week 2–3)

1. **Replace in-memory WebAuthn challenge dict** with Redis-backed store (keyed by session ID).
2. **Sanitise `bridge_id` in OAuth callbacks** — validate against `channel_registry.keys()` before HTML interpolation.
3. **Add input length limit** to `sanitize_input` (max 10,000 chars).
4. **Add alerting metric** when Redis is unavailable and rate limiting is disabled.
5. **Migrate audit ledger** from vault blob to DB table.
6. **Fix `ALLOWED_ORIGINS` validator** to read `APP_ENV` from `info.data` not raw env.
7. **Rotate default PostgreSQL password** out of hardcoded fallback.

### Phase 3: Code Organisation (Week 3–4)

1. **Extract APIRouters** from `app.py`: target ~300-line main file with 8 router submodules.
2. **Remove all `logger.info("DEBUG: ...")` statements** from lifespan.
3. **Split `requirements.txt`** into `requirements-core.txt`, `requirements-tda.txt`, `requirements-dev.txt`.
4. **Update README** to use accurate model identifiers.

### Phase 4: Infrastructure Completion (Month 2)

1. **Create `docker-compose.yml`** with backend, Redis, and PostgreSQL services.
2. **Pin Docker base image** to a digest.
3. **Generate missing Alembic migrations** and add `alembic check` to CI.
4. **Add Redis service** to CI workflow.
5. **Create `scripts/setup_sovereign_stack.sh`** (referenced but missing).
6. **Write `docker-compose.test.yml`** with isolated test DB.

### Phase 5: Feature Completion (Month 2–3)

1. **Wire remaining bridges** into `channel_registry`: Gmail, Google Drive, MS Teams, Facebook, Instagram (or explicitly document them as "coming soon").
2. **Implement agent persistence** — replace hardcoded agent list with DB-backed agent configurations.
3. **Add memory eviction policy** to ChromaDB store (TTL or relevance scoring).
4. **Replace SSE polling** with event-driven push architecture.
5. **Fix audit ledger truncation** — implement proper append-only DB table.
6. **Remove `puppeteer-core`** from frontend dependencies.

### Phase 6: Production Observability (Month 3)

1. **Add structured tracing** (OpenTelemetry) to the DAG executor for per-task latency tracking.
2. **Add coverage reporting** to CI — current test coverage is unknown.
3. **Implement PPN/DPK accurately** or document what the stability system actually computes.
4. **Create the WatchOS companion app** (or provide a mock/simulator for development).

---

## 12. Overall Verdict

**Alluci Sovereign Agent is an impressive, architecturally coherent, and genuinely innovative prototype.** The vision is clear, the technical direction is sound, and several subsystems (the DAG executor, the affective engine, the vault isolation pattern, the exec approval interceptor) are at production quality already.

**The gap to production readiness is real but bridgeable.** The critical bugs are straightforward to fix. The security issues are well-understood problems with known solutions. The incomplete bridges are a scope management challenge, not a technical one.

The most significant non-technical risk is the **documentation-reality gap**: the README and architecture document describe a system that is more complete and mathematically rigorous than the current implementation. For an open-source project, this creates trust issues when contributors or users explore the code. Aligning documentation to the actual implementation would strengthen the project substantially.

**Estimated effort to production-ready (v1.0):** 6–10 engineer-weeks, heavily front-loaded on the Phase 1–2 bug and security fixes.

| Category | Current State | Production-Ready Threshold |
|---|---|---|
| Core Agent Loop (DAG planning + execution) | ✅ Solid | Add retry telemetry |
| Security (Vault, Auth, Guardrails) | 🟡 Good foundation, 3 critical fixes needed | Fix bugs 4.7, 5.6 |
| Communication Bridges | 🟡 9/18 functional | Wire remaining or defer |
| Biometric / ACE Engine | ✅ Implemented | Needs Watch companion app |
| Frontend / UI | ✅ Feature-rich | Code split, bundle size review |
| Database / Persistence | 🟡 Schema incomplete | Regenerate migrations |
| Observability | 🟡 Partial (metrics, logs) | Add tracing, alerting |
| Testing | 🟡 Partial coverage | Add integration tests |
| Infrastructure | 🔴 No docker-compose | Create compose + CI fixes |
| Documentation | 🔴 Overstates implementation | Align to reality |

---

*Audit performed by static analysis of 1,169 source files. No runtime testing was performed.*
