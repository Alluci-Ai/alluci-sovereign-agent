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
