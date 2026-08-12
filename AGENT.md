# AGENT.md — Enterprise Developer & System Reference Guide
# Last updated: 2026-08-12

## What This Codebase Is
Alluci Sovereign Agent: A self-hosted, biometric-aware AI executive assistant with 4-tier Simplicial H-LSM memory, AES-256-GCM encrypted local vault, VerusID sovereign identity, and multi-bridge messaging gateway.

## Core Architectural Pillars (See ARCHITECTURE.md)
1. **Sovereign Identity (`VerusID`):** Self-sovereign identity (`identity@`) and Ed25519 manifest signing.
2. **HITL Executive Security Governance:** Hard security guards & `SecurityInterventionModal.tsx` intercepting critical action tasks.
3. **4-Tier Simplicial H-LSM Memory:** L0 Working, L1 Episodic (FTS5), L2 Semantic, and L3 KùzuDB Knowledge Graph (`hlsm_manager.py`).
4. **Bio-Affective Computing (ACE):** Apple Watch biometrics (HRV, stress, respiratory sync) modulating LLM sampling temperature (`backend/ace/`).
5. **Policy-Driven DAG Orchestration:** Autonomous task decomposition, recurring background crons, and multi-tier model routing (`orchestrator.py`).

## Golden Operational Laws — NEVER Violate These
1. **Zero-Stub & Real End-to-End Wiring Law:** NO stubs, NO mocks, NO simulated responses, NO incomplete scaffolding, and NO dummy fallbacks. Every feature, API route, database query, security guard, and React component MUST be 100% complete, fully implemented, and wired end-to-end to real backend data providers.
2. **Anti-Monkey-Patch & Engineering Excellence Law:** NO dynamic monkey-patching, NO superficial band-aids, NO `unittest.mock` in production code, and NO ad-hoc hacks. Always fix root-cause architecture in the authoritative source file adhering to principal engineer industry standards.
3. **Empirical Proof & Verification Directive:** NEVER declare a task resolved or feature completed without running real execution commands (`pytest`, `npx tsc --noEmit`, `make quality`) and verifying clean test success.
4. **Strict Cryptographic Vault Storage:** Never store credentials in plaintext—always call `vault.store_connection_secret(bridge_id, account_id, creds)`.
5. **Robust Exception Propagation:** Never `.unwrap()` or swallow exceptions silently—every error must be explicitly handled, logged, or propagated.
6. **Complete Endpoint Registration & Rate Limiting:** Every new API route requires a handler function, registration in `app.py` under `prefix="/api/v1"`, and a `RateLimiter` dependency.
7. **Secure OAuth PKCE & Refresh Loops:** Every OAuth bridge requires Redis PKCE state tracking (`oauth_store`) and a background token refresh loop.
8. **WebSocket Session Authentication:** All WebSocket endpoints must execute `authenticate_ws(websocket, token)` before initiating streaming handlers.
9. **Secure iOS/Watch Token Storage:** Swift session tokens must be saved in Keychain (`SecItemAdd`), never `UserDefaults`.
10. **HITL Security Interception:** Critical action endpoints (memory purges, schema changes, OS operations, financial operations) must implement rate limiting and trigger `SecurityInterventionModal.tsx`.

## 5-Tier Local Cognitive Engine (LCE) Precision Matrix
- **`TIER_0_ULTRA` ($\ge 96\text{ GB}$ VRAM/RAM):** `Alluci/alluci-polytope-gemma-4-31b-it-bf16`
- **`TIER_1_MAX` ($\ge 60\text{ GB}$ VRAM/RAM):** `Alluci/alluci-polytope-gemma-4-31b-it-4bit` (or 8bit)
- **`TIER_2_PRO` ($\ge 30\text{ GB}$ VRAM/RAM):** `Alluci/alluci-polytope-gemma-4-26b-a4b-it-4bit` (MoE)
- **`TIER_3_BASE` ($\ge 15\text{ GB}$ VRAM/RAM):** `Alluci/alluci-polytope-gemma-4-12b-it-4bit`
- **`TIER_4_EDGE` ($< 15\text{ GB}$ VRAM/RAM):** `Alluci/alluci-polytope-gemma-4-e2b-it-4bit`

## Verification Commands (Must Pass After Every Change)
```bash
source .venv/bin/activate
pytest backend/tests/ -v                                 # Full Python test suite
npx tsc --noEmit                                           # TypeScript type check
make quality                                               # Full SRE production quality gate
curl -s http://127.0.0.1:8000/api/v1/health                # Health check
```
