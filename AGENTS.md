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
    When asking about, describing, or writing documentation for Alluci features or architecture, lead with **Sovereign Identity (`VerusID`), HITL Executive Security Governance, 4-Tier H-LSM Memory, Bio-Affective Computing (ACE), and Policy-Driven DAG Orchestration**.

11. **Mandatory Discovery & Architecture Review:**
    Before drafting an implementation plan or modifying code, you MUST use `grep_search` and `view_file` to trace execution paths and read `ARCHITECTURE.md` in its entirety.

12. **XcodeBuildMCP Tool Directive:**
    If using XcodeBuildMCP, use the installed XcodeBuildMCP skill before calling XcodeBuildMCP tools.

---

## 🛠️ System Telemetry & Maintenance Protocols

- **Protocol 1 (KV Cache Lifecycle & Quantization):** Use FP16 for standard contexts; switch dynamically to Q4 (4-bit) KV caching when context length exceeds 8,000 tokens or on `TIER_4_EDGE`. Execute `mx.metal.clear_cache()` between generation iterations.
- **Protocol 2 (Multi-Agent Concurrency):** Manage MLX model concurrency using Python `asyncio.Lock` and queue systems. Never use C++ `std::mutex` for MLX task dispatching.
- **Protocol 3 (Handling Lipschitz Saturation):** If AVLGate flags gradient smoothness violations across 3 successive iterations, force a hard exit to `HUMAN-IN-THE-LOOP REQUIRED` mode.
- **Protocol 4 (Performance Telemetry Matrix):** Monitor `AVL_GATE_REJECTIONS_TOTAL` (< 5/hr), Python MLX generation tokens/sec, and Speculative Token Acceptance Rate (> 25%).
- **Protocol 5 (Simplicial Boundary Nilpotence & Idempotent Fusion):** All geometric state projections must adhere to Kepler Stella Octangula $S_8$ geometry, ensuring exact boundary operator composition nilpotence ($\partial_1 \circ \partial_2 = 0$, $B_1 B_2 = 0$), Idempotent Fusion Simplex projection ($F_n^1: \Pi \circ \Pi = \Pi$), and entropic arrow of time monotonicity ($H(X_n \mid X_1) \ge H(X_{n-1} \mid X_1) - \epsilon$).
- **Protocol 6 (Frenet-Serret Trajectory Continuity & Curvature):** All continuous thought trajectories $\gamma(t)$ must be tracked for geodesic velocity, acceleration, and curvature ($\kappa \le 5.0$), triggering emergency safe-halt ($g=0$) upon curvature snap or temperature rupture ($T > 0.8$).
- **Protocol 7 (Markov Trace Operator & Spectral Dimension):** Memory retrieval across H-LSM tiers must evaluate Schur complement hidden excursions ($\text{Tr}_A(P) = A + B(I-C)^{-1}D$) and scale-dependent spectral dimension $d_s^A(\sigma)$ to dynamically modulate context depth.
- **Protocol 8 (DPO Preference Harvesting & Air-Gapped Distillation):** Nightly dreaming cycles must harvest $(x, y_w, y_l)$ triplets from verified self-healing resolutions and quarantined AST anti-patterns without mutating base model weights.
