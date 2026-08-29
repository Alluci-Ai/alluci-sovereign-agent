# Alluci Sovereign Agent Strict Directives

1. **Mandatory Discovery (Pre-Flight Check):**
   Before drafting an implementation plan or modifying code, you MUST use `grep_search` and `view_file` to trace the execution path of the component being modified. You must explicitly identify how the change impacts the Local Compute Engine (LCE).

2. **Apple Silicon Inference Directive (Platform Scoped):**
   When targeting macOS / Apple Silicon environments, Local Compute Engine (LCE) model evaluation MUST rely on official Python Apple MLX frameworks (`mlx_lm` and `mlx_vlm`) in `backend/inference/mlx_engine.py`. Custom out-of-tree C++ inference runners for model evaluation are forbidden on Apple Silicon to prevent Metal GPU command buffer panics and VRAM leaks. For Windows, Linux, and NVIDIA CUDA environments, cross-platform inference backends (e.g., `llama.cpp` bindings or CUDA PyTorch/vLLM adapters) are supported via `local_bridge.py`.

3. **System Description & Communication Directive:**
   When asking about, describing, or writing documentation for the Alluci Sovereign Agent features, capabilities, or architecture, lead with **Sovereign Identity (`VerusID`), HITL Executive Security Governance, 4-Tier H-LSM Memory, Bio-Affective Computing (ACE), and Policy-Driven DAG Orchestration**. Do NOT surface low-level implementation caveats (such as C++ constraints or framework choices) in general feature descriptions unless explicitly requested.

4. **Contextual Integrity:**
   Never assume standard configurations. Always verify via `config.json`, `hardware_scanner.py`, and `profiler.py` before making assumptions about model architectures or loading schemas.

5. **Planning Mode Enforcement:**
   Any proposed implementation plan MUST include a dedicated "Architecture Impact Analysis" section detailing the effects on PCL, AVL, and DPK.

6. **Mandatory Architecture Review:**
   You MUST read `ARCHITECTURE.md` in its entirety before taking any actions in this repository.

7. **No Unsanctioned Service Restarts (Explicit Confirmation Required):**
   You are STRICTLY FORBIDDEN from automatically running `make restart`, `make stop`, `make start`, `pkill`, or killing processes on ports 8000/3000. You MUST ask for explicit user confirmation before executing any service restart commands so the user can save their work and restart on their own terms without losing active Web UI chat sessions.

---
## Maintenance Protocols & System Telemetry

**Protocol 1: KV Cache Lifecycle & Quantization**
To support Deep Research workloads without Out-Of-Memory (OOM) errors, the LCE must implement a dynamic KV cache strategy. Use FP16 for standard, short-context interactions on workstation tiers. Switch dynamically to Q4 (4-bit quantization) KV caching when context length exceeds 8,000 tokens or when operating on edge tiers (`TIER_4_EDGE`). Explicitly manage memory by calling `mx.metal.clear_cache()` between agent loop iterations.

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
All geometric state projections must adhere to Kepler Stella Octangula $S_8$ geometry, ensuring exact boundary operator composition nilpotence ($\partial_1 \circ \partial_2 = 0$, $B_1 B_2 = 0$), Idempotent Fusion Simplex projection ($F_n^1: \Pi \circ \Pi = \Pi$), and entropic arrow of time monotonicity ($H(X_n \mid X_1) \ge H(X_{n-1} \mid X_1) - \epsilon$).

**Protocol 6: Frenet-Serret Trajectory Continuity & Curvature**
All continuous thought trajectories $\gamma(t)$ must be tracked for geodesic velocity, acceleration, and curvature ($\kappa \le 5.0$), triggering emergency safe-halt ($g=0$) upon curvature snap or temperature rupture ($T > 0.8$).

**Protocol 7: Markov Trace Operator & Spectral Dimension**
Memory retrieval across H-LSM tiers must evaluate Schur complement hidden excursions ($\text{Tr}_A(P) = A + B(I-C)^{-1}D$) and scale-dependent spectral dimension $d_s^A(\sigma)$ to dynamically modulate context depth.

**Protocol 8: DPO Preference Harvesting & Air-Gapped Distillation**
Nightly dreaming cycles must harvest $(x, y_w, y_l)$ triplets from verified self-healing resolutions and quarantined AST anti-patterns without mutating base model weights.
