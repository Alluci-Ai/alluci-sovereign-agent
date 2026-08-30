# AGENT.md — Enterprise Developer & System Reference Guide
# Last updated: 2026-08-30 (Full-Spectrum Grounding & Stages 1–3 Complete)

## What This Codebase Is
Alluci Sovereign Agent: A self-hosted, biometric-aware AI executive assistant with 4-tier Simplicial H-LSM memory, Tri-Hybrid Reciprocal Rank Fusion (RRF $k=60$), AES-256-GCM encrypted local vault, VerusID sovereign identity, Stella Octangula $S_8$ geometric verification, Streaming Attention Sinks, Native Apple MLX Speculative Decoding (2B $\to$ 31B), and multi-bridge messaging gateway.

## Core Architectural & Functional Domains (See ARCHITECTURE.md)
1. **Core Compute & Apple MLX Inference:** Official Apple MLX (`mlx_lm`, `mlx_vlm`) local inference on Apple Silicon, **Native Speculative Decoding** (2B Edge draft $\to$ 31B Dense verification) with automated fallback, and **Streaming Attention Sinks** (>16k characters) pinning system rules at token 0.
2. **Topological Physics & Mathematical Substrate:** Foundational Topological State Spaces ($W$ world data, $X$ simplicial complexes via Vietoris-Rips filtration `pmet_filtration.py`, $\mathcal{J}$-Space counterfactual sandbox with Simplicial Chain-of-Thought boundary nilpotence $\partial_1 \circ \partial_2 = 0$ and Kepler $S_8$ Dual-Tetrahedron Socratic Synthesis $T_+ \cup T_- \to O_6$ in `j_space_simulator.py`, $G$ action affordance convex hull `affordance_envelope.py`, and $N$ central discrete pacing in `barcode_clock.py`), Discrete Projection Kernel grounded in Kepler's Stella Octangula $S_8$ ($\partial_1 \circ \partial_2 = 0$, $F_n^1: \Pi \circ \Pi = \Pi$), and Frenet-Serret curvature safe-halt ($\kappa \le 5.0$, $T \le 0.8$).
3. **4-Tier Simplicial H-LSM Memory & Tri-Hybrid RRF:** L0 Working, L1 Episodic (FTS5), L2 Semantic (MiniLM vectors), and L3 KùzuDB Knowledge Graph (`hlsm_manager.py`) aggregated in parallel via **Tri-Hybrid Reciprocal Rank Fusion** ($\text{Score}_{\text{RRF}}(d) = \sum \frac{w_t}{60 + \text{rank}_t(d)}$) and augmented by the **Markov Trace Engine** ($\text{Tr}_A(P) = A + B(I-C)^{-1}D$).
4. **Autonomous Sub-Agents & Deep Research:** Multi-agent constellation (Executive Orchestrator, Codi OpenCode Harness, Rocco Deep Research Harvester with parallel multi-query decomposition and 24h SQLite `ResearchDossierCache`, SPE, SWD, SUF, OC, PMET).
5. **Zero-Trust Security & Sovereign Identity:** Self-sovereign identity (`VerusID`), Ed25519 manifest signing (`verus.py`), AES-256-GCM Vault Manager (`vault.py`), AVL Gate GJK boundary refinement, Protocol 3 Lipschitz saturation, and HITL Executive Governance (`SecurityInterventionModal.tsx`).
6. **Omni-Channel Bridges & Hardware Integration:** 20+ cryptographically isolated communication bridges (Telegram, Nostr, Signal, iMessage, WhatsApp, Discord, Slack, Instagram, Facebook, WeCom, Email) coupled with real-time Apple Watch biometrics (ACE HRV, respiratory sync, stress scores).

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
12. **Broad Scope Law:** For broad, multi-faceted, or systemic questions, synthesize a complete, high-altitude architectural breakdown across all relevant functional domains before diving into granular specifics.
13. **Contextual Fidelity Law & Introspective Grounding:** All descriptions of subsystem capabilities (DPK, PPN, Codi, Rocco, SPE, SWD, SUF, OC, Vault, KùzuDB) must be grounded directly in authoritative source definitions and docstrings on disk. Never simulate or invent capabilities.

## 5-Tier Local Cognitive Engine (LCE) Precision Matrix
- **`TIER_0_ULTRA` ($\ge 96\text{ GB}$ VRAM/RAM):** `Alluci/alluci-polytope-gemma-4-31b-it-bf16` (Accelerated via 2B Speculative Draft)
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


