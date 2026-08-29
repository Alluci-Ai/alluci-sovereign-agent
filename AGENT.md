# AGENT.md — Enterprise Developer & System Reference Guide
# Last updated: 2026-08-29 (Phase 1–5 Verification Complete)

## What This Codebase Is
Alluci Sovereign Agent: A self-hosted, biometric-aware AI executive assistant with 4-tier Simplicial H-LSM memory, AES-256-GCM encrypted local vault, VerusID sovereign identity, Stella Octangula $S_8$ geometric verification, and multi-bridge messaging gateway.

## Core Architectural Pillars (See ARCHITECTURE.md)
1. **Sovereign Identity (`VerusID`):** Self-sovereign identity (`identity@`) and Ed25519 manifest signing (`verus.py`, `verusid_auth.py`).
2. **HITL Executive Security Governance, Topological State Spaces $(W, X, G, N)$ & Geometric Firewall:** Hard security guards, `SecurityInterventionModal.tsx`, Foundational Topological State Spaces ($W$ continuous world data, $X$ simplicial complexes via Vietoris-Rips filtration `pmet_filtration.py`, $\mathcal{J}$-Space counterfactual sandbox with Simplicial Chain-of-Thought boundary nilpotence $\partial_1 \circ \partial_2 = 0$ and Kepler $S_8$ Dual-Tetrahedron Socratic Synthesis $T_+ \cup T_- \to O_6$ in `j_space_simulator.py`, $G$ action affordance convex hull `affordance_envelope.py`, and $N$ central discrete pacing in `barcode_clock.py`), Discrete Projection Kernel grounded in Kepler's Stella Octangula $S_8$ ($\partial_1 \circ \partial_2 = 0$, $F_n^1: \Pi \circ \Pi = \Pi$), AVLGate GJK boundary refinement, Protocol 3 Lipschitz saturation, and Thermodynamic PVT Trajectory Curvature safe-halt ($\kappa \le 5.0$, $T \le 0.8$).
3. **4-Tier Simplicial H-LSM Memory & Discrete Clock Pacing:** L0 Working, L1 Episodic (FTS5), L2 Semantic, and L3 KùzuDB Knowledge Graph (`hlsm_manager.py`) augmented with the **Markov Trace Engine** ($\text{Tr}_A(P) = A + B(I-C)^{-1}D$) and scale-dependent spectral dimension context scaling (`markov_trace.py`), paced monotonically by the thread-safe **Topological Barcode Clock** ($N \to N+1$).
4. **Bio-Affective Computing (ACE):** Apple Watch biometrics (HRV, stress, respiratory sync) modulating LLM sampling temperature and affective tension ($\psi = \text{tension}/1024.0$) (`backend/ace/`).
5. **Policy-Driven DAG Orchestration, Topological Heartbeat & Nightly Evolution:** Autonomous task decomposition, recurring background crons, multi-tier model routing (`orchestrator.py`), **Heartbeat Daemon** with active 1D topological hole detection (`_probe_subagent_loop` via $\beta_1 > 0$) and AVL Lipschitz drift detection (`_probe_topological_drift`), and the 5-stage **Overnight Dreaming Cycle** with offline $\mathcal{J}$-Space counterfactual rollouts and DPO preference harvesting (`dpo_harvester.py`, `cron_engine.py`).

## Golden Operational Laws — NEVER Violate These
1. **Zero-Stub & Real End-to-End Wiring Law:** NO stubs, NO mocks, NO simulated responses, NO incomplete scaffolding, and NO dummy fallbacks. Every feature, API route, database query, security guard, and React component MUST be 100% complete, fully implemented, and wired end-to-end to real backend data providers.
2. **Anti-Monkey-Patch & Engineering Excellence Law:** NO dynamic monkey-patching, NO superficial band-aids, NO `unittest.mock` in production code, and NO ad-hoc hacks. Always fix root-cause architecture in the authoritative source file adhering to principal engineer industry standards.
3. **Empirical Proof & Verification Directive:** NEVER declare a task resolved or feature completed without running real execution commands (`pytest`, `npx tsc --noEmit`, `make quality`) and verifying clean test success.
4. **Strict Cryptographic Vault Storage:** Never store credentials in plaintext—always call `vault.store_connection_secret(bridge_id, account_id, creds)`.
5. **Robust Exception Propagation:** Never `.unwrap()` or swallow exceptions silently—every error must be explicitly handled, logged, or propagated.
6. **Complete Endpoint Registration & Rate Limiting:** Every new API route requires a handler function, registration in `app.py` under `prefix="/api/v1"`, and a `RateLimiter` dependency.
7. **Secure OAuth PKCE & Refresh Loops:** Every OAuth bridge requires Redis PKCE state tracking (`oauth_store`) and a background token refresh loop.
8. **WebSocket Session Authentication & Real-Time Sync:** All WebSocket endpoints must execute `authenticate_ws(websocket, token)` and synchronize live administrative events (`manifold.pvt`, `security.resolution_required`, `memory.deleted`).
9. **Secure iOS/Watch Token Storage:** Swift session tokens must be saved in Keychain (`SecItemAdd`), never `UserDefaults`.
10. **HITL Security Interception & Protocol 3 Escalation:** Critical action endpoints (memory purges, schema changes, OS operations, financial operations) and Protocol 3 Lipschitz saturated violations ($\ge 3$ strikes) must trigger `SecurityInterventionModal.tsx` for explicit sovereign authorization.
11. **Standardized Artifact Storage & Triad Bundle Law:** All generated user artifacts (presentations, documents, research reports, deliverables) MUST be written to `workspace/artifacts/<category>/YYYY-MM-DD_<artifact_slug>/` as an atomic 3-file bundle (`metadata.json`, `source.md`, `source.html`). NEVER write generated user deliverables or presentations into `Documentation/` (reserved exclusively for system documentation) or the workspace root.

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

