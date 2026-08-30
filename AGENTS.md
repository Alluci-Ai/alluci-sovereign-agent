# AGENTS.md — Enterprise Sovereign Agent Directives & Operational Laws

This document defines the immutable operational directives, zero-trust safety laws, and software engineering standards for all AI agents, sub-agents, and developers working in this repository.

---

## 🏛️ Sovereign Strict Directives

1. **Zero-Stub & Real End-to-End Wiring Law:**
   NO stubs, NO mocks, NO simulated responses, NO incomplete scaffolding, and NO dummy fallbacks. Every feature, API route, database query, security guard, and React component MUST be 100% complete, fully implemented, and wired end-to-end to real backend data providers.

2. **Anti-Monkey-Patch & Engineering Excellence Law:**
   NO dynamic monkey-patching, NO superficial band-aids, NO `unittest.mock` in production code, and NO ad-hoc hacks. Always fix root-cause architecture in the authoritative source file adhering to principal engineer industry standards.

3. **Empirical Proof & Verification Directive:**
   NEVER declare a task resolved or feature completed without running real execution commands (`pytest`, `npx tsc --noEmit`, `make quality`) and verifying clean test success. Editing a file does NOT equal completing a task.

4. **Apple Silicon Native Inference Directive:**
   On macOS / Apple Silicon environments, Local Compute Engine (LCE) model evaluation MUST rely on official Python Apple MLX frameworks (`mlx_lm` and `mlx_vlm`) in `backend/inference/mlx_engine.py`. Custom out-of-tree C++ inference runners for model evaluation are forbidden on Apple Silicon to prevent Metal GPU command buffer panics and VRAM leaks. For Windows, Linux, and NVIDIA CUDA environments, cross-platform inference backends (`llama.cpp` bindings or CUDA PyTorch/vLLM adapters) are supported via `local_bridge.py`.

5. **Human-in-the-Loop (HITL) Executive Governance:**
   All critical action tasks (destructive memory purges, schema changes, file overwrites, OS operations, financial operations) MUST be intercepted before execution and gated by explicit HITL authorization (`SecurityInterventionModal.tsx`). The agent is STRICTLY FORBIDDEN from autonomously executing destructive operations or generating simulated deletion confirmations.

6. **Defensive Type Safety & Non-Null Contracts:**
   Prevent runtime crashes (`AttributeError`, `KeyError`, `NullPointerException`, `TypeError`) by explicitly verifying object initialization and non-null states before property dereferencing. Enforce strict Pydantic v2 schemas and TypeScript interfaces across all data paths.

7. **Zero Technical Debt & Dead Code Cleanliness:**
   Do not leave behind unused imports, commented-out dead code, transient debug prints, or orphaned draft files. Maintain pristine, self-documenting code.

8. **Absolute Secret Isolation:**
   NEVER hardcode secrets, private keys, JWT seeds, or static file paths. All credentials must be dynamically loaded from `.env` or managed via AES-256 `VaultManager` (`backend/security/vault.py`).

9. **No Unsanctioned Service Restarts:**
   STRICTLY FORBIDDEN from automatically running `make restart`, `make stop`, `make start`, `pkill`, or killing processes on ports 8000/3000. Ask for explicit user confirmation before executing service restarts so the user does not lose active Web UI chat sessions.

10. **System Description & Communication Directive:**
    When asking about, describing, or writing documentation for Alluci features or architecture, lead with **Sovereign Identity (`VerusID`), HITL Executive Security Governance, Topological State Spaces $(W, X, G, N)$, $\mathcal{J}$-Space World Model, 4-Tier H-LSM Memory with Tri-Hybrid RRF, Bio-Affective Computing (ACE), Native Apple MLX Speculative Decoding, and Policy-Driven DAG Orchestration**. Enforce the **Broad Scope Law** (synthesizing high-altitude overviews across all 6 functional domains for broad inquiries) and the **Contextual Fidelity Law** (introspectively grounding all subsystem descriptions directly in authoritative disk definitions).

11. **Mandatory Discovery & Architecture Review:**
    Before drafting an implementation plan or modifying code, you MUST use `grep_search` and `view_file` to trace execution paths and read `ARCHITECTURE.md` in its entirety.

12. **XcodeBuildMCP Tool Directive:**
    If using XcodeBuildMCP, use the installed XcodeBuildMCP skill before calling XcodeBuildMCP tools.

13. **Standardized Artifact Storage & Triad Bundle Law:**
    All generated user artifacts (presentations, research dossiers, deliverables, documents) MUST be persisted in `workspace/artifacts/<category>/YYYY-MM-DD_<slug>/` as an atomic triad (`metadata.json`, `source.md`, `source.html`). Generated artifacts must NEVER be stored in `Documentation/` (which is reserved exclusively for developer architecture guides) or the repository root.

---

## 🛠️ System Telemetry & Maintenance Protocols

- **Protocol 1 (KV Cache Lifecycle, Streaming Attention Sinks & Speculative Drafting):** Use FP16 for standard contexts; switch dynamically to Q4 (4-bit) KV caching when context length exceeds 8,000 tokens or on `TIER_4_EDGE`. When prompt length exceeds 16,000 characters, activate **Streaming Attention Sinks** to anchor system invariants and grounding laws at token 0 while rolling the active conversational tail. When running on 31B Dense models, leverage **Native Apple MLX Speculative Decoding** (2B draft $\to$ 31B verifier) with an automated circuit-breaker falling back to single-model evaluation if memory limits are reached. Execute `mx.metal.clear_cache()` between generation iterations.
- **Protocol 2 (Multi-Agent Concurrency):** Manage MLX model concurrency using Python `asyncio.Lock` and queue systems. Never use C++ `std::mutex` for MLX task dispatching.
- **Protocol 3 (Handling Lipschitz Saturation):** If AVLGate flags gradient smoothness violations across 3 successive iterations, force a hard exit to `HUMAN-IN-THE-LOOP REQUIRED` mode.
- **Protocol 4 (Performance Telemetry Matrix):** Monitor `AVL_GATE_REJECTIONS_TOTAL` (< 5/hr), Python MLX generation tokens/sec, and Speculative Token Acceptance Rate (> 25%).
- **Protocol 5 (Simplicial Boundary Nilpotence & Idempotent Fusion):** All geometric state projections must adhere to Kepler Stella Octangula $S_8$ geometry and $(W, X, \mathcal{J}, G, N)$ state space boundaries, ensuring exact boundary operator composition nilpotence ($\partial_1 \circ \partial_2 = 0$, $B_1 B_2 = 0$), Simplicial Chain-of-Thought (S-CoT) face verification, Idempotent Fusion Simplex projection ($F_n^1: \Pi \circ \Pi = \Pi$), and entropic arrow of time monotonicity ($H(X_n \mid X_1) \ge H(X_{n-1} \mid X_1) - \epsilon$).
- **Protocol 6 (Frenet-Serret Trajectory Continuity & Curvature):** All continuous thought trajectories $\gamma(t)$ must be tracked for geodesic velocity, acceleration, and curvature ($\kappa \le 5.0$), triggering emergency safe-halt ($g=0$) upon curvature snap or temperature rupture ($T > 0.8$).
- **Protocol 7 (Markov Trace Operator & Tri-Hybrid RRF Memory Fusion):** Memory retrieval across H-LSM tiers must execute parallel retrieval across L1 SQLite FTS5 ($w=1.0$), L2 MiniLM Dense Vectors ($w=1.2$), and L3 KùzuDB Relational Graph Entities ($w=1.4$) fused via **Tri-Hybrid Reciprocal Rank Fusion**:
  $$\text{Score}_{\text{RRF}}(d) = \sum_{t \in \{\text{L1}, \text{L2}, \text{L3}\}} \frac{w_t}{60 + \text{rank}_t(d)}$$
  augmented by Schur complement hidden excursions ($\text{Tr}_A(P) = A + B(I-C)^{-1}D$) and scale-dependent spectral dimension $d_s^A(\sigma)$ to dynamically modulate context depth.
- **Protocol 8 (DPO Preference Harvesting & Air-Gapped Distillation):** Nightly dreaming cycles must harvest $(x, y_w, y_l)$ triplets from verified self-healing resolutions and quarantined AST anti-patterns without mutating base model weights.
- **Protocol 9 (Discrete Barcode Clock Pacing & 1D Loop Gating):** All cognitive state transitions, sub-agent task lifespans, and memory consolidation cycles must register birth/death intervals with the `TopologicalBarcodeClock` ($N \to N+1$). The Heartbeat Daemon must continuously verify that active 1D topological holes remain acyclic ($\beta_1 = 0$), triggering automated self-healing upon reasoning loop detection ($\beta_1 > 0$).
- **Protocol 10 ($\mathcal{J}$-Space Counterfactual Simulation & Offline Dreaming):** Multi-step planning DAGs and quiet-hours dreaming cycles must execute air-gapped rollouts through `JSpaceSimulator` with Kepler $S_8$ Dual-Tetrahedron Socratic Synthesis ($T_+ \cup T_- \to O_6$), harvesting verified $(x, y_w, y_l)$ preference triplets to `DPOTripletHarvester` before committing actions to the affordance convex hull ($G$).
