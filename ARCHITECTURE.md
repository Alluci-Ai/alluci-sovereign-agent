# Alluci Sovereign Agent Architecture

This document defines the immutable laws and architectural foundation of the Alluci Sovereign Agent. 

## 1. Core Inference & Compute
- **The LCE Law (Local Compute Engine):** The system relies on a custom C++ PyBind11 kernel (`alluci_core` / `topology_kernel.cpp`) injected into `mlx_engine.py`. This engine loads custom Polytope Gemma 4 variants utilizing AWPQ quantization tensors (`input_max`, `input_min`) and custom MoE architectures (`per_layer_input_gate`). 
- **Standard Library Incompatibility:** Standard `mlx_lm` and `mlx_vlm` physically cannot parse these custom structures. DO NOT attempt to use standard HuggingFace pipeline fallbacks or replace the `alluci_core` dependency.
- **PPN (Polytope Projection Network):** Translates tensor activations into geometric representations (Betti numbers) using `gudhi` for continuous topological mapping of cognitive processes.

## 2. Security & Integrity
- **DPK (Discrete Projection Kernel):** A C++ kernel (`dpk_kernel.cpp` / `dpk.py`) that monitors "Manifold Tearing" by comparing real-time topology shifts against dynamic thresholds.
- **AVL Gate (Action Verification Loop):** A three-pillar safety mechanism for LLM outputs:
  1. *Sovereign Attribution:* Validates cryptographic/manifold signatures.
  2. *ALCE Gradient Smoothness:* Ensures Lipschitz continuity budget is not exceeded.
  3. *Topological Continuity:* Rejects actions causing Euler characteristic mismatches.
- **Continuous Calibration Manager:** Manages continuous statistical normalization for DPK thresholds based on tool history, skill history, and affective tension (`calibration.py`).

## 3. Autonomy & Proactivity
- **PCL (Proactive Cognition Loop):** The daemon responsible for the agent's autonomy (`backend/pcl.py`). It continuously extracts episodic memories (H-LSM), builds a World Model Snapshot, and generates `PCLOpportunity` records for proactive execution.
- **ACE (Affective Computing Engine):** C++ modules (`affect_kernel.cpp`, `harmonic_kernel.cpp`, `entropy_kernel.cpp`) that simulate artificial emotion, tension, and memory decay, modulating the agent's temperature and stress levels.
- **BTM (Behavioral Topological Mapper):** A biometric/affective tracking kernel (`btm_kernel.cpp`) managing histories like HRV/GSR analogs to map cognitive tension to topological space.

**WARNING:** Any future modifications to action generation or inference pipelines MUST strictly respect these definitions. Violating these principles will compromise the Sovereign constraints and manifold integrity.
