# Alluci Sovereign Agent Strict Directives

1. **Mandatory Discovery (Pre-Flight Check):**
   Before drafting an implementation plan or modifying code, you MUST use `grep_search` and `view_file` to trace the execution path of the component being modified. You must explicitly identify how the change impacts the Local Compute Engine (LCE).

2. **Apple Silicon Inference Directive (Platform Scoped):**
   When targeting macOS / Apple Silicon environments, Local Compute Engine (LCE) model evaluation MUST rely on official Python Apple MLX frameworks (`mlx_lm` and `mlx_vlm`) in `backend/inference/mlx_engine.py`. Custom out-of-tree C++ inference runners for model evaluation are forbidden on Apple Silicon to prevent Metal GPU command buffer panics and VRAM leaks. For Windows, Linux, and NVIDIA CUDA environments, cross-platform inference backends (e.g., `llama.cpp` bindings or CUDA PyTorch/vLLM adapters) are supported via `local_bridge.py`.

3. **System Description & Communication Directive:**
   When asking about, describing, or writing documentation for the Alluci Sovereign Agent features, capabilities, or architecture, lead with **Sovereign Identity (`VerusID`), HITL Executive Security Governance, Topological State Spaces $(W, X, G, N)$, $\mathcal{J}$-Space World Model, 4-Tier H-LSM Memory with Tri-Hybrid RRF, Bio-Affective Computing (ACE), Native Apple MLX Speculative Decoding, and Policy-Driven DAG Orchestration**. Enforce the **Broad Scope Law** (synthesizing high-altitude overviews across all 6 functional domains for broad inquiries) and the **Contextual Fidelity Law** (introspectively grounding all subsystem descriptions directly in authoritative disk definitions). Do NOT surface low-level implementation caveats (such as C++ constraints or framework choices) in general feature descriptions unless explicitly requested.

4. **Contextual Integrity:**
   Never assume standard configurations. Always verify via `config.json`, `hardware_scanner.py`, and `profiler.py` before making assumptions about model architectures or loading schemas.

5. **Planning Mode Enforcement:**
   Any proposed implementation plan MUST include a dedicated "Architecture Impact Analysis" section detailing the effects on PCL, AVL, and DPK.

6. **Mandatory Architecture Review:**
   You MUST read `ARCHITECTURE.md` in its entirety before taking any actions in this repository.

7. **No Unsanctioned Service Restarts (Explicit Confirmation Required):**
   You are STRICTLY FORBIDDEN from automatically running `make restart`, `make stop`, `make start`, `pkill`, or killing processes on ports 8000/3000. You MUST ask for explicit user confirmation before executing any service restart commands so the user can save their work and restart on their own terms without losing active Web UI chat sessions.

8. **Standardized Artifact Storage & Triad Bundle Law:**
   All generated user artifacts (presentations, research dossiers, deliverables, documents) MUST be persisted in `workspace/artifacts/<category>/YYYY-MM-DD_<slug>/` as an atomic triad (`metadata.json`, `source.md`, `source.html`). Generated artifacts must NEVER be stored in `Documentation/` (which is reserved exclusively for developer architecture guides) or the repository root.

---
## Maintenance Protocols & System Telemetry

**Protocol 1: KV Cache Lifecycle, Streaming Attention Sinks & Speculative Drafting**
To support Deep Research workloads without Out-Of-Memory (OOM) errors, the LCE must implement a dynamic KV cache strategy. Use FP16 for standard, short-context interactions on workstation tiers. Switch dynamically to Q4 (4-bit quantization) KV caching when context length exceeds 8,000 tokens or when operating on edge tiers (`TIER_4_EDGE`). When prompt length exceeds 16,000 characters, activate **Streaming Attention Sinks** to anchor system invariants and grounding laws at token 0 while rolling the active conversational tail. When running on 31B Dense models, leverage **Native Apple MLX Speculative Decoding** (2B draft $\to$ 31B verifier) with an automated circuit-breaker falling back to single-model evaluation if memory limits are reached. Explicitly manage memory by calling `mx.metal.clear_cache()` between agent loop iterations.

**Protocol 2: Multi-Agent Concurrency**
When multiple asynchronous agents (e.g., Deep Research Skill, PCL daemon, Planner) attempt to query the LCE concurrently, the engine MUST use Python `asyncio.Lock` and queue-based concurrency. Never attempt to use C++ `std::mutex` for MLX orchestration.

**Protocol 3: Handling Lipschitz Budget Saturation**
When the AVLGate flags a gradient smoothness violation (Lipschitz budget exhausted), the `ExecutiveOrchestrator` self-healing loop injects a corrective prompt injection. If the model continues to fail across 3 successive iterations, force a hard exit to the `HUMAN-IN-THE-LOOP REQUIRED` state.

**Protocol 4: Real-Time Performance Analytics**
Monitor your core system performance using this target metrics matrix:
- **AVL_GATE_REJECTIONS_TOTAL**: Total structural action payload rejections. Warning Threshold: > 5 per hour. Operational Fix: Relax Context-Free Grammar restrictions or update schema validators.
- **Python MLX Latency**: Monitor generation tokens/sec. Drop to Q4 KV cache if swapping is detected.
- **Speculative Acceptance Rate**: Percentage of tokens drafted by smaller tiers accepted by larger tiers. Warning Threshold: < 25%.

**Protocol 5: Simplicial Boundary Nilpotence & Idempotent Fusion**
All geometric state projections must adhere to Kepler Stella Octangula $S_8$ geometry and $(W, X, \mathcal{J}, G, N)$ state space boundaries, ensuring exact boundary operator composition nilpotence ($\partial_1 \circ \partial_2 = 0$, $B_1 B_2 = 0$), Simplicial Chain-of-Thought (S-CoT) face verification, Idempotent Fusion Simplex projection ($F_n^1: \Pi \circ \Pi = \Pi$), and entropic arrow of time monotonicity ($H(X_n \mid X_1) \ge H(X_{n-1} \mid X_1) - \epsilon$).

**Protocol 6: Frenet-Serret Trajectory Continuity & Curvature**
All continuous thought trajectories $\gamma(t)$ must be tracked for geodesic velocity, acceleration, and curvature ($\kappa \le 5.0$), triggering emergency safe-halt ($g=0$) upon curvature snap or temperature rupture ($T > 0.8$).

**Protocol 7: Markov Trace Operator & Tri-Hybrid RRF Memory Fusion**
Memory retrieval across H-LSM tiers must execute parallel retrieval across L1 SQLite FTS5 ($w=1.0$), L2 MiniLM Dense Vectors ($w=1.2$), and L3 KùzuDB Relational Graph Entities ($w=1.4$) fused via **Tri-Hybrid Reciprocal Rank Fusion**:
$$\text{Score}_{\text{RRF}}(d) = \sum_{t \in \{\text{L1}, \text{L2}, \text{L3}\}} \frac{w_t}{60 + \text{rank}_t(d)}$$
augmented by Schur complement hidden excursions ($\text{Tr}_A(P) = A + B(I-C)^{-1}D$) and scale-dependent spectral dimension $d_s^A(\sigma)$ to dynamically modulate context depth.

**Protocol 8: DPO Preference Harvesting & Air-Gapped Distillation**
Nightly dreaming cycles must harvest $(x, y_w, y_l)$ triplets from verified self-healing resolutions and quarantined AST anti-patterns without mutating base model weights.

**Protocol 9: Discrete Barcode Clock Pacing & 1D Loop Gating**
All cognitive state transitions, sub-agent task lifespans, and memory consolidation cycles must register birth/death intervals with the `TopologicalBarcodeClock` ($N \to N+1$). The Heartbeat Daemon must continuously verify that active 1D topological holes remain acyclic ($\beta_1 = 0$), triggering automated self-healing upon reasoning loop detection ($\beta_1 > 0$).

**Protocol 10: $\mathcal{J}$-Space Counterfactual Simulation & Offline Dreaming**
Multi-step planning DAGs and quiet-hours dreaming cycles must execute air-gapped rollouts through `JSpaceSimulator` with Kepler $S_8$ Dual-Tetrahedron Socratic Synthesis ($T_+ \cup T_- \to O_6$), harvesting verified $(x, y_w, y_l)$ preference triplets to `DPOTripletHarvester` before committing actions to the affordance convex hull ($G$).
