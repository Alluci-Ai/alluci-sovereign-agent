# Alluci Sovereign Agent Strict Directives

1. **Mandatory Discovery (Pre-Flight Check):**
   Before drafting an implementation plan or modifying code, you MUST use `grep_search` and `view_file` to trace the execution path of the component being modified. You must explicitly identify how the change impacts the C++ Kernels (DPK, ACE, BTM) and the Local Compute Engine (LCE).

2. **No Destructive Replacements:**
   You are STRICTLY FORBIDDEN from replacing custom Sovereign components (e.g., `alluci_core`, PyBind11 modules, Custom AWPQ quantization loaders) with standard libraries (e.g., `mlx_lm`, `transformers`) to resolve isolated errors. If a native component fails, debug the native component.

3. **Contextual Integrity:**
   Never assume standard configurations. Always verify via `config.json`, `hardware_scanner.py`, and `profiler.py` before making assumptions about model architectures or loading schemas.

4. **Planning Mode Enforcement:**
   Any proposed implementation plan MUST include a dedicated "Architecture Impact Analysis" section detailing the effects on PCL, AVL, and DPK.

5. **Mandatory Architecture Review:**
   You MUST read `ARCHITECTURE.md` in its entirety before taking any actions in this repository.

---
## Maintenance Protocols & System Telemetry

**Protocol 1: KV Cache Lifetime Recalibration**
When the `alluci_core` engine experiences a memory state flush via `alluci_core.flush_global_kv_pipeline_registry()`, the Python host wrapper must synchronize its internal state indices. If a background loop calls the C++ compiler to wipe the physical cache banks but the Python tracking wrappers fail to reset their active generation index strings back to position zero, your subsequent speculative stride loops will experience shape errors and instantly crash the engine process.

**Protocol 2: Handling Lipschitz Budget Saturation**
When the AVLGate flags a gradient smoothness violation (Lipschitz budget exhausted), the `ExecutiveOrchestrator` self-healing loop injects a corrective prompt injection. If the model continues to fail across 3 successive iterations, do not let the system continue to consume resources. Force a hard exit to the `HUMAN-IN-THE-LOOP REQUIRED` state. This step dumps a text serialization of the entire model registry array directly to the system logs for architectural review.

**Protocol 3: Real-Time Performance Analytics**
Monitor your core system performance using this target metrics matrix:
- **AVL_GATE_REJECTIONS_TOTAL**: Total structural action payload rejections. Warning Threshold: > 5 per hour. Operational Fix: Relax Context-Free Grammar restrictions or update model fine-tune parameters.
- **C++ Hidden State Variance**: Stability of vector channels entering final layer. Warning Threshold: Outside [0.5, 50.0]. Operational Fix: Re-verify model.layers.layer_scalar weight application layers inside C++ loops.
- **Speculative Acceptance Rate**: Percentage of tokens drafted by 12B accepted by 31B. Warning Threshold: < 25%. Operational Fix: Sync the grammar restriction masks across both weight registries simultaneously.

