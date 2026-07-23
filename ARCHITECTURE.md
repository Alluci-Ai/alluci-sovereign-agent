# Alluci Sovereign Agent Architecture

This document defines the immutable laws and architectural foundation of the Alluci Sovereign Agent. 

## 1. Core Inference & Compute
- **The LCE Law (Local Compute Engine):** The system relies exclusively on the official Apple MLX Python frameworks (`mlx_lm` and `mlx_vlm`). The Local Compute Engine (LCE) evaluates models natively in Python without relying on brittle C++ kernels.
- **Custom Architectures:** Any custom architectural variations or propriety model definitions MUST be transparently mapped directly to native `mlx_lm` implementations within `backend/inference/mlx_engine.py` using runtime dictionary mappings (e.g., overriding `_get_classes`), avoiding the need for dedicated monkey-patching or `nn.Module` reimplementations.
- **Dynamic KV Cache Strategy:** To prevent memory exhaustion during Deep Research workflows, the LCE dynamically toggles the KV cache format. Short contexts use FP16 for absolute precision, while contexts >8,000 tokens (or edge tiers) automatically switch to Q4 (4-bit quantization) to conserve memory.
- **Multi-Agent Concurrency:** The LCE uses a strict Python `asyncio.Lock` and queue system to manage concurrent requests from multiple agents. C++ mutexes are strictly forbidden.

## 2. Security & Integrity
- **DPK (Discrete Projection Kernel):** A module (`dpk.py`) that monitors "Manifold Tearing" by comparing real-time topology shifts against dynamic thresholds.
- **AVL Gate (Action Verification Loop):** A three-pillar safety mechanism for LLM outputs:
  1. *Sovereign Attribution:* Validates cryptographic/manifold signatures.
  2. *ALCE Gradient Smoothness:* Ensures Lipschitz continuity budget is not exceeded.
  3. *Topological Continuity:* Rejects actions causing Euler characteristic mismatches.
- **Continuous Calibration Manager:** Manages continuous statistical normalization for DPK thresholds based on tool history, skill history, and affective tension (`calibration.py`).

## 3. Autonomy & Proactivity
- **PCL (Proactive Cognition Loop):** The daemon responsible for the agent's autonomy (`backend/pcl.py`). It continuously extracts episodic memories (H-LSM), builds a World Model Snapshot, and generates `PCLOpportunity` records for proactive execution.
- **ACE (Affective Computing Engine):** Python-native modules that simulate artificial emotion, tension, and memory decay, modulating the agent's temperature and stress levels.
- **BTM (Behavioral Topological Mapper):** A biometric/affective tracking kernel (`btm.py`) managing histories like HRV/GSR analogs to map cognitive tension to topological space.

**WARNING:** Any future modifications to action generation or inference pipelines MUST strictly respect these definitions. Violating these principles will compromise the Sovereign constraints and manifold integrity.
