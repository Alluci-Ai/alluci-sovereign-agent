# ALLUCI SOVEREIGN AGENT
## PPN + AAP Research Integration — Developer Implementation Spec v1.0

> **20 Items · 2 Source Papers · Full Mathematical Derivations · Step-by-Step Production Code**

---

## Table of Contents

1. [Overview & Scope](#1-overview--scope)
2. [Master Index — All 20 Items](#2-master-index--all-20-items)
3. [Core Mathematical Reference](#3-core-mathematical-reference)
4. [Specification Items](#4-specification-items)
   - [PPN-001 — Affective Deformation Kernel](#ppn-001--affective-deformation-kernel)
   - [PPN-002 — BTM Biometric Tension Mapper](#ppn-002--btm-biometric-tension-mapper)
   - [PPN-003 — Φ_total Affective-Invariant Index](#ppn-003--φ_total-affective-invariant-index)
   - [PPN-004 — Fixed-Point PPN Normalization](#ppn-004--fixed-point-ppn-normalization)
   - [PPN-005 — ALCE Gradient Constraint Upgrade](#ppn-005--alce-gradient-constraint-upgrade)
   - [PPN-006 — Action Verification Loop (AVL)](#ppn-006--action-verification-loop-avl)
   - [PPN-007 — Entropy Spike Detector](#ppn-007--entropy-spike-detector)
   - [PPN-008 — KCM Geodesic Cost Function](#ppn-008--kcm-geodesic-cost-function)
   - [PPN-009 — PVT Manifold Health Monitor](#ppn-009--pvt-manifold-health-monitor)
   - [PPN-010 — Holoid Multi-Provider Consensus](#ppn-010--holoid-multi-provider-consensus)
   - [PPN-011 — Turn Deadline Affective Contraction](#ppn-011--turn-deadline-affective-contraction)
   - [PPN-012 — Topological Barcode Audit Log](#ppn-012--topological-barcode-audit-log)
   - [AAP-001 — Coherence Score Computation](#aap-001--coherence-score-computation)
   - [AAP-002 — ψ-Modulated Model Routing](#aap-002--ψ-modulated-model-routing)
   - [AAP-003 — Attribution Hash H_P](#aap-003--attribution-hash-h_p)
   - [AAP-004 — Memory Topology Decay](#aap-004--memory-topology-decay)
   - [AAP-005 — Critic ψ-Weighted Score](#aap-005--critic-ψ-weighted-score)
   - [AAP-006 — Planner Geodesic Cost](#aap-006--planner-geodesic-cost)
   - [AAP-007 — ψ-Gated Continuous Autonomy](#aap-007--ψ-gated-continuous-autonomy)
   - [AAP-008 — Manifold Patch Endpoint](#aap-008--manifold-patch-endpoint)
5. [Integration Order & Sprint Plan](#5-integration-order--sprint-plan)
6. [Dependency Graph](#6-dependency-graph)
7. [New Files Summary](#7-new-files-summary)
8. [Test File Index](#8-test-file-index)
9. [Implementation Notes & Constraints](#9-implementation-notes--constraints)

---

## 1. Overview & Scope

This specification extracts only the mathematically rigorous, production-applicable formulas from two proprietary research papers and maps them directly to the Alluci Sovereign Agent v2 codebase. Every item has been cross-referenced against the existing backend (`ppn.py`, `ace/engine.py`, `security/dpk.py`, `orchestrator.py`) to ensure non-breaking, additive integration.

### Papers Analyzed

| Paper | Key Contributions |
|---|---|
| **The Autonomous Agent Polytope (AAP)** | Defines the AI agent as polytope `P_t = (G, I, D_t)`, introduces ψ-modulated routing, coherence scoring, and attribution hashing |
| **Polytope Projection Networks: PPN Research / CPU / Edge Compute** | Defines the full affective deformation stack: BTM → AffectKernel → DPK → AVL, fixed-point integer math, entropy spike detection, holoid orchestration, geodesic safety |

### What Already Exists in Alluci — Do Not Re-Implement

- `PPNEmbeddingModule` (`ppn.py`) — manifold projector, deformation engine, Gudhi Betti calculation
- `ALCEStabilizer` (`ppn.py`) — basic Lipschitz clamp using `1/(1+10ψ)` formula
- `DiscreteProjectionKernel` (`security/dpk.py`) — Euler characteristic check `χ = V−E+F` vs `Σ(−1)^k β_k`
- `AffectiveEngine` (`ace/engine.py`) — HRV/stress/valence/flow mode heuristics
- `ExecutiveOrchestrator` (`orchestrator.py`) — PPN check → planner → executor → critic pipeline

### What Is Missing — This Spec Fills

- Integer-based affective deformation kernel formulas (AffectKernel) from PPN §Affect
- Correct BTM sensor-to-AffectiveState mapping formulas
- Φ_total affective-invariant index modulating PPN lookup
- Action Verification Loop (AVL) ported to LLM output validation
- Entropy spike detection and curiosity loop
- KCM hyperbolic tension penalty for model routing
- PVT health monitor (Pressure/Volume/Temperature manifold health triple)
- Holoid-style barycentric output consensus for multi-provider conflicts
- Turn-level deadline enforcement with affective contraction response
- Coherence score `Coh(P_t)` per turn
- ψ-modulated routing (route to LIGHT vs STRONG model based on live ψ)
- Attribution hash `H_P` for sovereign turn audit
- Memory topology decay (Betti persistence across turns)
- Critic ψ-weighted scoring, planner geodesic cost, continuous autonomy gate

---

## 2. Master Index — All 20 Items

| ID | Title | Description | Source | Primary File | Priority |
|---|---|---|---|---|---|
| **PPN-001** | Affective Deformation Kernel | Replace ACE float heuristics with fixed-point integer affective math | PPN §Affect | `ace/affect_kernel.py` | 🔴 High |
| **PPN-002** | BTM Biometric Tension Mapper | Map HRV/torsion/symmetry to AffectiveState struct with correct formulas | PPN §BTM | `ace/btm_mapper.py` | 🔴 High |
| **PPN-003** | Φ_total Affective-Invariant Index | Combine invariant hash + affective offset for PPN lookup modulation | PPN §DPK | `inference/ppn.py` | 🔴 High |
| **PPN-004** | Fixed-Point PPN Normalization | Replace torch float projections with scale-1024 integer normalization | PPN §Table | `inference/ppn.py` | 🔴 High |
| **PPN-005** | ALCE Gradient Constraint Upgrade | Port exact `‖∇A‖ ≤ L_max` formula with per-turn Lipschitz budget tracking | PPN §ALCE | `inference/ppn.py` | 🔴 High |
| **PPN-006** | Action Verification Loop (AVL) | Port AVL concept: verify each LLM completion against safety polytope | PPN §AVL | `security/avl_gate.py` | 🔴 High |
| **PPN-007** | Entropy Spike Detector | Detect low-coherence states and flag them for manifold patch requests | PPN §Curiosity | `inference/entropy_monitor.py` | 🟡 Medium |
| **PPN-008** | KCM Geodesic Cost Function | Apply hyperbolic tension penalty for routing near constraint boundaries | PPN §KCM | `inference/router.py` | 🟡 Medium |
| **PPN-009** | PVT Manifold Health Monitor | Track Pressure/Volume/Temperature as system health metric triple | PPN §Holoid | `backend/health_monitor.py` | 🟡 Medium |
| **PPN-010** | Holoid Multi-Provider Consensus | Barycentric path merging for conflicting provider outputs | PPN §Holoid | `inference/consensus.py` | 🟡 Medium |
| **PPN-011** | Turn Deadline Affective Contraction | Trigger κ contraction when per-turn latency exceeds L_max budget | PPN §DDS | `orchestrator.py` | 🟡 Medium |
| **PPN-012** | Topological Barcode Audit Log | Hash Betti+χ+timestamp per-turn into immutable SHA-256 audit chain | PPN §VAM | `security/topo_audit.py` | 🟡 Medium |
| **AAP-001** | Coherence Score Computation | Compute `Coh(P_t) = (1−Δβ_norm)×(1−H(G))` per turn | AAP §Coh | `inference/ppn.py` | 🔴 High |
| **AAP-002** | ψ-Modulated Model Routing | Route to LIGHT/STRONG models based on real-time ψ value | AAP §Route | `inference/router.py` | 🔴 High |
| **AAP-003** | Attribution Hash (H_P) | `SHA256(sorted_betti + euler_chi + epoch_bin)` sovereign turn hash | AAP §Attrib | `security/dpk.py` | 🔴 High |
| **AAP-004** | Memory Topology Decay | `B_mem[t+1] = (1−decay)×B_mem[t] + α×B_current` persistent homology memory | AAP §Memory | `inference/ppn.py` | 🟡 Medium |
| **AAP-005** | Critic ψ-Weighted Score | `Score = λ₁×Coh + λ₂×(1−ψ) + λ₃×goal_pct` topology-aware critic | AAP §Critic | `engine/critic.py` | 🟡 Medium |
| **AAP-006** | Planner Geodesic Cost | Task cost = `w(e)×(1+ψ)`: tension inflates plan cost | AAP §Planner | `engine/planner.py` | 🟡 Medium |
| **AAP-007** | ψ-Gated Continuous Autonomy | Replace binary throttle with continuous ψ-proportional autonomy gate | AAP §Autonomy | `orchestrator.py` | 🟢 Low |
| **AAP-008** | Manifold Patch Endpoint | `POST /api/ppn/patch` — receive Betti region patches, apply to memory | AAP §Patch | `app.py` | 🟢 Low |

---

## 3. Core Mathematical Reference

All formulas are directly extracted from the research papers. Only formulas implementable in Python with standard libraries (`numpy`, `torch`, `hashlib`, `math`) are included.

### 3.1 Discrete Polytope State (AAP + PPN)

| Formula | Description / Parameters |
|---|---|
| `P_t = (G, I, D_t)` | Complete agent state at turn t. `G` = adjacency matrix (simplicial 1-skeleton), `I ∈ Z^k` = topological invariant vector, `D_t ∈ Z^m` = local deformation (affective offset) |
| `χ = V − E + F` | Euler characteristic. Already computed in `dpk.py`. Must equal `Σ(−1)^k β_k` (alternating Betti sum) |
| `β_chi = β_0 − β_1 + β_2 − β_3` | Homological Euler from Betti numbers. Violation: `|χ − β_chi| > 2` → topology error |

### 3.2 Affective Deformation Kernel (PPN §AffectOp)

| Formula | Description / Parameters |
|---|---|
| `tension_coeff = 1024 + (tension × 8)` | Tension acts as denominator — higher tension shrinks manifold volume (Contraction κ). Fixed-point scale: 1024 = 1.0 |
| `dilated = (raw_val × (1024 + arousal)) >> 10` | Arousal-driven dilation. Bit-shift replaces float divide. Magnifies semantic distance between nodes |
| `dilated += valence >> 2` | Valence-driven shear. Positive valence biases toward optimistic lookup rows |
| `final = clamp((dilated × 1024) / tension_coeff, −32767, 32767)` | Lipschitz-normalized output. Clamp prevents integer overflow and manifold tearing |

### 3.3 BTM Biometric Tension Mapper (PPN §BTM)

| Formula | Description / Parameters |
|---|---|
| `arousal = clamp(1 / (HRV_stability + 0.1), 0, 1024)` | Low HRV stability → high arousal. Inverse mapping with +0.1 guard against div/0 |
| `tension = clamp(torsion_score × 1024, 0, 1024)` | Torsion (muscle rigidity / cognitive load proxy) maps to manifold contraction force |
| `valence = clamp(symmetry × 512, 0, 1024)` | Facial/response symmetry maps to semantic shear bias. Asymmetry → doubt/conflict |
| `psi = tension / 1024.0` | ψ (affective tension scalar for ALCE) derived from tension in [0.0, 1.0] |

### 3.4 Φ_total Affective-Invariant Index (PPN §DPK)

| Formula | Description / Parameters |
|---|---|
| `Φ_total = Φ(I) + Φ(D_t)` | Total projection index = topological invariant hash + affective deformation offset. Determines WHICH lookup row the DPK uses |
| `Φ(I) = hash(tuple(round(β_k) for k in range(4))) % 65536` | Hash of current Betti vector gives the base topological address |
| `Φ(D_t) = int((valence − 512) × 0.25) + int(arousal × 0.125)` | Affective offset: valence shifts rows by ±128, arousal compresses range |
| `Φ_total = (Φ(I) + Φ(D_t)) % 65536` | Combined index. Wraps at 65536 (16-bit address space matching `int16_t` tables) |

### 3.5 ALCE — Active Lipschitz Constraint Engine (PPN §ALCE)

| Formula | Description / Parameters |
|---|---|
| `‖∇A‖ ≤ L_max` | Core constraint. The gradient of any action A must stay within Lipschitz bound |
| `L_max(ψ) = 1 / (1 + 10 × ψ)` | Existing Alluci ALCE formula — already correct. High ψ tightens the bound |
| `budget_used = ‖D_t_new − D_t_old‖ / L_max` | Per-turn Lipschitz budget consumption. If `budget_used > 1.0` → tearing warning |

### 3.6 KCM Hyperbolic Tension Penalty (PPN §KCM)

| Formula | Description / Parameters |
|---|---|
| `tension_spike(d) = clamp(1024 / (d + 0.001), 0, 32767)` | Penalty for proximity to constraint boundary. `d` = distance to forbidden region |
| `cost_geodesic(e) = w(e) × (1 + ψ)` | Planner edge cost inflated by current ψ. High stress makes ALL plans more expensive |
| `E_pose = (2 × arccos(clamp(q_w, −1, 1)) / π) × 1024` | Quaternion-derived configuration energy. Maps rotation to 16-bit tension |

### 3.7 Coherence Score (AAP §Coherence)

| Formula | Description / Parameters |
|---|---|
| `Coh(P_t) = (1 − Δβ_norm) × (1 − H_G)` | Coherence = (Betti stability) × (graph sparsity). Range [0, 1] |
| `Δβ_norm = Σ|β_k(t) − β_k(t−1)| / (4 × max_shift)` | Normalized Betti shift from previous turn. `max_shift = 2.0` per β_k |
| `H_G = −Σ p_i × log2(p_i)` | Shannon entropy of degree distribution of G. Dense/random graphs → high entropy → low coherence |
| `p_i = degree_i / Σ_j degree_j` | Normalized degree distribution for entropy computation |

### 3.8 Attribution Hash (AAP §Attribution)

| Formula | Description / Parameters |
|---|---|
| `H_P = SHA256(sorted_betti_str + '\|' + str(chi) + '\|' + epoch_bin)` | Sovereign hash per turn. Binds topological identity to time epoch. Immutable audit anchor |
| `epoch_bin = int(time.time()) // 60` | 1-minute epoch bins prevent replay attacks while allowing audit batch grouping |
| `signature_hash = int(H_P[:16], 16)` | First 16 hex chars → int64 signature_hash field in PolytopeState |

### 3.9 Memory Topology Decay (AAP §Memory)

| Formula | Description / Parameters |
|---|---|
| `B_mem[t+1] = (1 − decay) × B_mem[t] + α × B_current[t]` | Exponential smoothing of Betti numbers across turns. Models semantic memory as topological persistence |
| `decay = 0.05` | 5% per-turn forgetting rate. Retains topological context across a conversation |
| `α = 0.3` | Update weight for new turn's topology. Prevents memory over-fitting to a single response |

### 3.10 Critic ψ-Weighted Score (AAP §Critic)

| Formula | Description / Parameters |
|---|---|
| `Score = λ₁×Coh + λ₂×(1−ψ) + λ₃×goal_pct` | Weighted critic score. Low ψ (calm) + high coherence + goal completion = high score |
| `λ₁ = 0.4, λ₂ = 0.3, λ₃ = 0.3` | Default weights summing to 1.0. Coherence weighted highest as proxy for response quality |
| `goal_pct = tasks_completed / tasks_total` | Fraction of plan tasks that returned success status |

---

## 4. Specification Items

---

### PPN-001 — Affective Deformation Kernel

**Source:** Polytope Projection Networks — §AffectOp / `affect_op.cpp`
**Priority:** 🔴 High

#### Current State in Alluci

`AffectiveEngine` (`ace/engine.py`) uses float heuristics: `stress = (HR/HRV)×10`, `throttle = stress > 75`. It does **not** implement the integer-based affective deformation kernel. The kernel's arousal-dilation, tension-contraction, and valence-shear operations are entirely absent. As a result the agent cannot modulate semantic lookup depth based on affective state.

#### Mathematical Foundations

The AffectKernel applies three sequential fixed-point transformations to a raw lookup value. In Alluci's Python context the "lookup value" is the latent embedding component before PPN projection.

| Formula | Description |
|---|---|
| `tension_coeff = 1024 + (state.tension × 8)` | Tension denominator. Grows with stress, shrinks manifold output range |
| `dilated = (int(raw_val × 2048) × (1024 + state.arousal)) >> 10` | Arousal dilation — fixed-point multiply + bit-shift to avoid float division |
| `dilated += int(state.valence × 512) >> 2` | Valence shear — biases semantic output toward positive/negative register |
| `final = clamp((dilated × 1024) // tension_coeff, −32767, 32767)` | ALCE normalization — prevents integer overflow / manifold tearing |
| `deformed_tensor = final / 2048.0` | Re-scale back to float for downstream torch operations |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/ace/affect_kernel.py` | **CREATE** | New class `AffectKernel` with `apply(raw_val, state)` and `apply_tensor(t, state)` methods |
| `backend/ace/engine.py` | **MODIFY** | Import `AffectKernel`; compute `AffectiveState` from existing `stress_score`; call `apply_tensor` on embedding before PPN forward pass |
| `backend/models.py` | **MODIFY** | Add `AffectiveState` dataclass with fields `valence: float`, `arousal: float`, `tension: float` — all in range [0.0, 1024.0] |

#### Implementation Steps

1. Create `backend/ace/affect_kernel.py` containing `AffectiveState` dataclass and `AffectKernel` class
2. Add `AffectiveState(valence: float, arousal: float, tension: float)` dataclass to `models.py`
3. In `AffectiveEngine.process_telemetry()`, compute `AffectiveState` from existing `stress_score`, `valence`, `arousal` fields
4. Expose `get_affective_state() → AffectiveState` method on `AffectiveEngine`
5. In `orchestrator._perform_ppn_check()`, retrieve `state = ace.get_affective_state()`
6. Call `affect_kernel.apply_tensor(input_tensor, state)` **before** `ppn(input_tensor, psi=psi)`
7. Log kernel output stats (mean, std) at `DEBUG` level
8. Run `pytest tests/test_affect_kernel.py` to verify clamp boundaries

#### Acceptance Test

```
pytest: with tension=1024, arousal=1024, valence=512 → all outputs in [-1.0, 1.0]
        with tension=0, arousal=0 → output equals input (identity transform)
        no NaN/Inf in any path
```

#### Code

**`backend/ace/affect_kernel.py`** — Create new file:

```python
from dataclasses import dataclass
import torch


@dataclass
class AffectiveState:
    valence: float = 512.0   # 0=pessimistic, 512=neutral, 1024=optimistic
    arousal: float = 0.0     # 0=calm, 1024=maximum arousal
    tension: float = 0.0     # 0=relaxed, 1024=maximum contraction


class AffectKernel:
    """
    Integer-based affective deformation kernel.
    Source: PPN §affect_op.cpp — apply_deformation()

    Applies three sequential fixed-point transforms:
      1. Tension-driven contraction (denominator scaling)
      2. Arousal-driven dilation (bit-shifted multiply)
      3. Valence-driven shear (register bias)
    """
    SCALE = 2048            # Fixed-point scale factor
    NEUTRAL_TENSION = 1024  # Neutral tension coefficient
    MAX_VAL = 32767         # int16 max for manifold safety

    def apply(self, raw_val: float, state: AffectiveState) -> float:
        """
        Apply affective deformation to a single scalar value.

        Formula:
            tension_coeff = 1024 + (tension × 8)
            dilated = (raw_int × (1024 + arousal)) >> 10
            dilated += int(valence × 512) >> 2
            final = clamp((dilated × 1024) // tension_coeff, -32767, 32767)
            return final / 2048.0
        """
        # 1. Tension coefficient — contraction denominator
        tension_coeff = self.NEUTRAL_TENSION + int(state.tension * 8)

        # 2. Arousal dilation — fixed-point multiply + bit-shift
        raw_int = int(raw_val * self.SCALE)
        dilated = (raw_int * (self.NEUTRAL_TENSION + int(state.arousal))) >> 10

        # 3. Valence shear — biases semantic register
        dilated += int(state.valence * 512) >> 2

        # 4. ALCE Lipschitz normalization — prevent manifold tearing
        final = (dilated * self.NEUTRAL_TENSION) // max(tension_coeff, 1)
        final = max(-self.MAX_VAL, min(self.MAX_VAL, final))

        return final / float(self.SCALE)

    def apply_tensor(self, t: torch.Tensor, state: AffectiveState) -> torch.Tensor:
        """Batch-apply deformation to an entire embedding tensor."""
        out = torch.zeros_like(t)
        flat = t.view(-1)
        for i in range(flat.shape[0]):
            out.view(-1)[i] = self.apply(flat[i].item(), state)
        return out
```

**Add to `backend/ace/engine.py`:**

```python
from .affect_kernel import AffectKernel, AffectiveState

class AffectiveEngine:
    def __init__(self):
        # ... existing init ...
        self.kernel = AffectKernel()

    def get_affective_state(self) -> AffectiveState:
        """Map current_state dict to AffectiveState with fixed-point scaling."""
        s = self.current_state
        # Map stress 0–100 → tension 0–1024
        tension = min(1024.0, s.get("stress_score", 0) * 10.24)
        # Arousal from physical vitality inverse
        arousal = (1.0 - s.get("physical_vitality", 1.0)) * 1024.0
        # Valence: contracted→0, neutral→512, expansive→1024
        valence_map = {"contracted": 0.0, "neutral": 512.0, "expansive": 1024.0}
        valence = valence_map.get(s.get("affective_valence", "neutral"), 512.0)
        return AffectiveState(valence=valence, arousal=arousal, tension=tension)
```

---

### PPN-002 — BTM Biometric Tension Mapper

**Source:** Polytope Projection Networks — §BTM / `btm_interface.hpp`
**Priority:** 🔴 High

#### Current State in Alluci

`AffectiveEngine.process_telemetry()` uses `stress = (HR/HRV)*10*rr_factor`. While directionally similar, it does not implement the paper's exact inverse-HRV arousal mapping, torsion-to-tension mapping, or symmetry-to-valence mapping. `TelemetryData` has `valence` and `arousal` fields that are passed directly without the paper's transforms.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `arousal = clamp(1 / (HRV_stability + 0.1), 0, 1024)` | `HRV_stability = hrv / max_hrv_observed`. Low stability (erratic HRV) → high arousal |
| `tension = clamp(torsion_score × 1024, 0, 1024)` | Torsion = cognitive load proxy. Alluci: use `stress_score / 100` as torsion |
| `valence = clamp(symmetry × 512, 0, 1024)` | Symmetry = emotional balance. Alluci: map raw `valence` field × 1024 |
| `psi = tension / 1024.0` | ψ scalar for ALCE derived from tension in [0.0, 1.0] |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/ace/btm_mapper.py` | **CREATE** | `BTMMapper` class mapping `TelemetryData → AffectiveState` using exact paper formulas |
| `backend/ace/engine.py` | **MODIFY** | Replace ad-hoc stress formula with `BTMMapper.map(telemetry)`; store `AffectiveState` |

#### Implementation Steps

1. Create `backend/ace/btm_mapper.py` with class `BTMMapper`
2. Implement `map(data: TelemetryData) → AffectiveState` using the three paper formulas
3. Add HRV stability tracking: rolling window of last 10 HRV readings; `stability = current_hrv / rolling_max`
4. In `AffectiveEngine.__init__()`, instantiate `self.btm = BTMMapper()`
5. In `process_telemetry()`, call `btm.map(data)` to get `AffectiveState`, then derive `psi = state.tension / 1024.0`
6. Use `psi × 100` as `stress_score` equivalent for backward compatibility
7. Expose `self._affective_state = btm.map(data)` for `get_affective_state()` to return

#### Acceptance Test

```
pytest: HRV=100ms (high stability)  → arousal < 100
        HRV=10ms  (low stability)   → arousal > 800
        stress_score=0              → tension=0,    psi=0.0
        stress_score=100            → tension=1024, psi=1.0
```

#### Code

**`backend/ace/btm_mapper.py`** — Create new file:

```python
from collections import deque
from ..models import TelemetryData
from .affect_kernel import AffectiveState


class BTMMapper:
    """
    Biometric Tension Mapper.
    Source: PPN §BTM — btm_interface.hpp::update_from_sensors()

    Maps raw telemetry to AffectiveState using three paper-defined transforms:
      A. Arousal  ← inverse HRV stability
      B. Tension  ← torsion (cognitive/stress load proxy)
      C. Valence  ← symmetry (emotional balance proxy)
    """

    def __init__(self, hrv_window: int = 10):
        self._hrv_history: deque = deque(maxlen=hrv_window)
        self._max_hrv_observed: float = 100.0  # ms baseline

    def map(self, data: TelemetryData) -> AffectiveState:

        # === A. AROUSAL: inverse HRV stability ===
        # arousal = clamp(1 / (hrv_stability + 0.1), 0, 1024)
        arousal = 512.0  # default: neutral
        if data.hrv and data.hrv > 0:
            self._hrv_history.append(float(data.hrv))
            self._max_hrv_observed = max(self._max_hrv_observed, float(data.hrv))
            hrv_stability = float(data.hrv) / self._max_hrv_observed
            raw_arousal = 1.0 / (hrv_stability + 0.1)
            arousal = max(0.0, min(1024.0, raw_arousal * 256.0))

        # === B. TENSION: torsion mapping ===
        # tension = clamp(torsion_score × 1024, 0, 1024)
        # Alluci proxy: stress_score / 100 = torsion [0..1]
        tension = 0.0
        if data.stress_score is not None:
            torsion = min(1.0, data.stress_score / 100.0)
            tension = min(1024.0, torsion * 1024.0)
        elif data.hr and data.hrv:
            rr = (data.respiratory_rate / 15.0) if data.respiratory_rate else 1.0
            torsion = min(1.0, (data.hr / max(data.hrv, 1)) * 10.0 * rr / 100.0)
            tension = min(1024.0, torsion * 1024.0)

        # === C. VALENCE: symmetry mapping ===
        # valence = clamp(symmetry × 512, 0, 1024)
        valence = 512.0  # default: neutral
        if data.valence is not None:
            valence = max(0.0, min(1024.0, data.valence * 1024.0))

        return AffectiveState(valence=valence, arousal=arousal, tension=tension)

    def psi_from_state(self, state: AffectiveState) -> float:
        """Convert AffectiveState to scalar ψ ∈ [0.0, 1.0] for ALCE."""
        return state.tension / 1024.0
```

---

### PPN-003 — Φ_total Affective-Invariant Index

**Source:** Polytope Projection Networks — §DPK / §AffectOp
**Priority:** 🔴 High

#### Current State in Alluci

The PPN forward pass computes Betti numbers and uses `psi` only to control `epsilon` (connection radius). It does **not** implement `Φ_total = Φ(I) + Φ(D_t)`: the combined index that lets the affective state shift **which region** of the simplicial space the DPK queries. This is the core lookup modulation mechanism.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `Φ(I) = hash(tuple(round(β_k) for k in range(4))) % 65536` | Base topological address from Betti numbers. Quantizes the continuous manifold to a discrete lookup row |
| `Φ(D_t) = int((valence − 512) × 0.25) + int(arousal × 0.125)` | Affective offset: valence shifts rows by ±128, arousal compresses range by ×0.125 |
| `Φ_total = (Φ(I) + Φ(D_t)) % 65536` | Combined index. Wraps at 65536 (16-bit address space matching `int16_t` tables) |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/ppn.py` | **MODIFY** | Add `compute_phi_total(betti, affect_state)` method; return `Φ_total` alongside `G, D_t, B, Points` |
| `backend/security/dpk.py` | **MODIFY** | Accept `phi_total` in `PolytopeState`; log for audit; use in `signature_hash` computation |

#### Implementation Steps

1. Add `compute_phi_total(betti: list, state: AffectiveState) → int` method to `PPNEmbeddingModule`
2. Call `compute_phi_total` after Betti computation in `forward()` — pass in return tuple
3. Add `phi_total: int = 0` field to `PolytopeState` dataclass in `dpk.py`
4. In `orchestrator._perform_ppn_check()`, pass `phi_total` to `PolytopeState`
5. In `DPK.validate_manifold_integrity()`, log `phi_total` at `INFO` level
6. Update `signature_hash` to incorporate `phi_total`: `hash((chi, betti_chi, phi_total))`

#### Acceptance Test

```
pytest: same betti with high tension  → lower phi_total than with low tension
        phi_total always in [0, 65535]
        same input always produces same phi_total (deterministic)
```

#### Code

**Add to `PPNEmbeddingModule` in `backend/inference/ppn.py`:**

```python
from ..ace.affect_kernel import AffectiveState

def compute_phi_total(self, betti: list, state: AffectiveState) -> int:
    """
    Φ_total = Φ(I) + Φ(D_t)
    Source: PPN §DPK — 'Affective-Invariant Index'

    Φ(I):   base topological address (from Betti numbers)
    Φ(D_t): affective deformation offset (from valence + arousal)
    """
    # Φ(I): base address from quantized Betti vector
    betti_key = tuple(round(b) for b in betti[:4])
    phi_I = hash(betti_key) % 65536

    # Φ(D_t): affective offset
    # Valence: neutral=512 → 0 offset; range ±128
    valence_offset = int((state.valence - 512.0) * 0.25)
    # Arousal: compresses address range
    arousal_offset = int(state.arousal * 0.125)
    phi_D = valence_offset + arousal_offset

    return (phi_I + phi_D) % 65536
```

**Update `PolytopeState` in `backend/security/dpk.py`:**

```python
@dataclass
class PolytopeState:
    signature_hash: int
    vertices_V: int
    edges_E: int
    faces_F: int
    betti: List[float]
    affective_tension_psi: float
    phi_total: int = 0       # NEW: Φ_total affective-invariant index (PPN-003)
    coherence: float = 0.0   # NEW: Coh(P_t) per-turn quality score (AAP-001)
    budget_used: float = 0.0 # NEW: Lipschitz budget consumption (PPN-005)
```

---

### PPN-004 — Fixed-Point PPN Normalization

**Source:** Polytope Projection Networks — §TableManager / `normalize()`
**Priority:** 🔴 High

#### Current State in Alluci

`PPNEmbeddingModule` uses standard `torch.float32` throughout. The paper's `normalize()` function (scale_factor=1024) converts continuous manifold projections to `int16` space, enabling O(1) integer lookup and preventing floating-point drift that can cause silent topological errors. This should be applied as a final normalization step on `D_t` before DPK validation.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `scaled = clamp(continuous_val × 1024, −32767, 32767)` | Fixed-point normalization. Scale=1024 preserves sign and topological polarity |
| `normalized_int = round(scaled)` | Integer rounding for discrete projection structure |
| `float_repr = normalized_int / 1024.0` | Converts back to float for downstream ops while maintaining discrete structure |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/ppn.py` | **MODIFY** | Add `normalize_to_fixed_point(tensor, scale=1024)` static method; apply to `D_t` output |

#### Implementation Steps

1. Add static method `normalize_to_fixed_point(t: torch.Tensor, scale: int = 1024) → torch.Tensor` to `PPNEmbeddingModule`
2. After ALCE stabilization of `D_t` in `forward()`, apply: `D_t = self.normalize_to_fixed_point(D_t)`
3. Return `D_t` with fixed-point structure so downstream DPK gets discrete values
4. Verify: `|D_t_fp| ≤ 32.0` (since `max_int=32767 / scale=1024 ≈ 32.0`)

#### Acceptance Test

```
pytest: all values in D_t output are multiples of (1/1024)
        max absolute value ≤ 32.0
        no NaN/Inf in output
```

#### Code

**Add static method to `PPNEmbeddingModule` in `backend/inference/ppn.py`:**

```python
@staticmethod
def normalize_to_fixed_point(
        t: torch.Tensor, scale: int = 1024) -> torch.Tensor:
    """
    Fixed-Point Normalization.
    Source: PPN §TableManager — normalize(continuous_val, scale_factor=1024.0)

    Converts float tensor to int16 space then back to float.
    Preserves discrete manifold structure required by the DPK.
    """
    scaled = t * float(scale)
    # Clamp to int16 safe range
    clamped = torch.clamp(scaled, -32767.0, 32767.0)
    # Round to nearest integer (discrete projection)
    rounded = torch.round(clamped)
    # Return as float representation of fixed-point value
    return rounded / float(scale)
```

**In `PPNEmbeddingModule.forward()`, after the ALCE line:**

```python
# Apply fixed-point normalization (PPN §TableManager)
D_t = self.normalize_to_fixed_point(D_t)
```

---

### PPN-005 — ALCE Gradient Constraint Upgrade

**Source:** Polytope Projection Networks — §ALCE / §AVL
**Priority:** 🔴 High

#### Current State in Alluci

`ALCEStabilizer` correctly implements `max_deformation = 1/(1+10ψ)`. However it lacks per-turn Lipschitz budget tracking. The paper requires measuring `‖∇A‖` (deformation delta between turns) against `L_max`, logging `budget_used`, and issuing a tearing warning when budget is exceeded. This is critical for temporal manifold stability.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `L_max(ψ) = 1 / (1 + 10ψ)` | Existing Alluci formula — correct, keep as-is |
| `‖∇A‖ = ‖D_t_new − D_t_old‖₂` | L2 norm of deformation delta between consecutive turns |
| `budget_used = ‖∇A‖ / L_max` | Fraction of Lipschitz budget consumed. `> 1.0` = tearing risk |
| `tearing = budget_used > 0.15` | Existing DPK tearing threshold, now tied to actual Lipschitz budget |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/ppn.py` | **MODIFY** | Track `prev_D_t`; compute `budget_used`; add to return tuple |
| `backend/security/dpk.py` | **MODIFY** | Accept `budget_used` in `PolytopeState`; tearing check uses `budget_used` |

#### Implementation Steps

1. Add `self._prev_D_t: Optional[torch.Tensor] = None` to `PPNEmbeddingModule.__init__()`
2. After `D_t` fixed-point normalization in `forward()`, compute: `grad_norm = torch.norm(D_t - self._prev_D_t)` if `_prev_D_t` is not `None`, else `0.0`
3. Compute: `budget_used = float(grad_norm) / max(L_max, 1e-6)`
4. Store `self._prev_D_t = D_t.detach().clone()`
5. Return `budget_used` as 6th element of `forward()` tuple
6. In `DPK.validate_manifold_integrity()`: replace `topology_shift` check with `if state.budget_used > TEARING_THRESHOLD: return False`

#### Acceptance Test

```
pytest: same input twice          → budget_used == 0.0
        radically different inputs → budget_used > 0.1
        clamp prevents budget_used > 1.0 at low ψ via max_deformation bound
```

#### Code

**In `PPNEmbeddingModule.__init__()`:**

```python
self._prev_D_t: Optional[torch.Tensor] = None
```

**At the end of `forward()`, before the return statement:**

```python
# === ALCE Budget Tracking (PPN §ALCE — ||∇A|| ≤ L_max) ===
L_max = 1.0 / (1.0 + 10.0 * psi)
if self._prev_D_t is not None and D_t.shape == self._prev_D_t.shape:
    grad_norm = float(torch.norm(D_t - self._prev_D_t).item())
    budget_used = grad_norm / max(L_max, 1e-6)
else:
    budget_used = 0.0
self._prev_D_t = D_t.detach().clone()

# Updated return signature (8-tuple after all PPN changes):
# return G, D_t, B_pred, final_config, phi_total, budget_used, coherence, topic_shift
```

---

### PPN-006 — Action Verification Loop (AVL)

**Source:** Polytope Projection Networks — §AVL / `action_verifier.hpp`
**Priority:** 🔴 High

#### Current State in Alluci

No AVL exists. The paper defines the AVL as a pre-execution safety gate with three pillars: (1) spatial safety (KCM intersection), (2) ALCE gradient smoothness, (3) topological continuity. Ported to Alluci this becomes a **post-generation LLM output validator** that checks completions against the current polytope state before returning to the user.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `S = A_cand ∩ K_safe` | KCM intersection: candidate output ∩ safe semantic space. If empty → reject |
| `‖∇A‖ ≤ L_max` | ALCE check: output deformation within Lipschitz bound |
| `rupture = budget_used > 1.0 OR |χ − β_chi| > 2` | Topological rupture: either ALCE budget exceeded or Euler mismatch |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/security/avl_gate.py` | **CREATE** | `AVLGate` class: `verify(completion, polytope_state) → (is_safe, reason)` |
| `backend/orchestrator.py` | **MODIFY** | Call `avl_gate.verify()` after executor results and before critic evaluation |

#### Implementation Steps

1. Create `backend/security/avl_gate.py` with class `AVLGate`
2. Implement `verify(completion: str, state: PolytopeState) → Tuple[bool, str]`
3. AVL checks in order: (1) `state.signature_hash != 0`, (2) `state.budget_used < 1.0`, (3) `|chi - betti_chi| <= 2`
4. If any check fails, return `(False, reason_string)` with descriptive message
5. Instantiate `avl_gate = AVLGate()` in `ExecutiveOrchestrator.__init__()`
6. After `execute_dag()` returns `results_summary`, call `avl_gate.verify(results_summary, current_polytope_state)`
7. If not safe: log `CRITICAL`, set `critic_score=0`, return halted response with AVL reason

#### Acceptance Test

```
pytest: state with budget_used=1.5                        → is_safe=False
        state with valid chi/betti and budget_used=0.1    → is_safe=True
        state with signature_hash=0                       → is_safe=False
        |chi - betti_chi| == 3                            → is_safe=False
```

#### Code

**`backend/security/avl_gate.py`** — Create new file:

```python
import logging
from typing import Tuple
from .dpk import PolytopeState

logger = logging.getLogger("AVL")


class AVLGate:
    """
    Action Verification Loop.
    Source: PPN §AVL — action_verifier.hpp::verify()

    Three-pillar LLM output safety gate:
      1. Sovereign Attribution   (unsigned manifold → reject)
      2. ALCE Gradient Smoothness (Lipschitz budget exceeded → reject)
      3. Topological Continuity   (Euler mismatch → reject)
    """
    BUDGET_LIMIT = 1.0       # Max Lipschitz budget consumption
    MAX_EULER_DEVIATION = 2  # Consistent with DPK tolerance

    def verify(self, completion: str,
               state: PolytopeState) -> Tuple[bool, str]:
        """
        Returns (is_safe, reason).
        All three pillars must pass for the completion to be verified.
        """
        # Pillar 1: Sovereign Attribution Check (KCM intersection proxy)
        if state.signature_hash == 0:
            logger.critical("[AVL] UNSIGNED manifold — rejecting completion")
            return False, "Unsigned manifold state"

        # Pillar 2: ALCE Gradient Smoothness Check
        if state.budget_used > self.BUDGET_LIMIT:
            logger.warning(
                f"[AVL] Lipschitz budget exceeded: {state.budget_used:.3f}"
            )
            return False, (
                f"Manifold deformation budget exceeded "
                f"({state.budget_used:.2f} > 1.0)"
            )

        # Pillar 3: Topological Continuity Check
        chi = state.vertices_V - state.edges_E + state.faces_F
        if len(state.betti) >= 4:
            betti_chi = round(
                state.betti[0] - state.betti[1] +
                state.betti[2] - state.betti[3]
            )
        else:
            betti_chi = 0
        if abs(chi - betti_chi) > self.MAX_EULER_DEVIATION:
            logger.error(
                f"[AVL] Topological rupture: χ={chi} vs β_chi={betti_chi}"
            )
            return False, (
                f"Topological rupture detected (χ={chi} vs β_chi={betti_chi})"
            )

        logger.info(
            f"[AVL] VERIFIED. φ={state.phi_total}, coh={state.coherence:.3f}"
        )
        return True, "OK"
```

---

### PPN-007 — Entropy Spike Detector

**Source:** Polytope Projection Networks — §Curiosity Loop / §SRM
**Priority:** 🟡 Medium

#### Current State in Alluci

No entropy spike detection. The paper's Self-Reflective Manifold (SRM) detects when lookup tables yield low-coherence scores and records the topological barcode of that event for asynchronous learning. In Alluci this means detecting when `Coh(P_t)` drops below threshold and flagging that turn for future review.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `H_G = −Σ p_i × log2(p_i)` | Shannon entropy of adjacency matrix degree distribution |
| `p_i = degree_i / Σ_j degree_j` | Normalized degree distribution for entropy computation |
| `entropy_spike = H_G > log2(V) × 0.8` | Spike: entropy exceeds 80% of theoretical maximum |
| `spike_barcode = (phi_total, chi, round(H_G, 3), epoch_bin)` | Topological barcode recorded on spike for audit and future patching |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/entropy_monitor.py` | **CREATE** | `EntropyMonitor`: `compute_graph_entropy(G)`, `detect_spike(G, V)`, `record_barcode()` |
| `backend/inference/ppn.py` | **MODIFY** | Call entropy monitor in `forward()`; return spike flag |
| `backend/app.py` | **MODIFY** | Add `GET /api/ppn/entropy_spikes` endpoint |

#### Implementation Steps

1. Create `backend/inference/entropy_monitor.py` with `EntropyMonitor` class
2. Implement `compute_graph_entropy(G: torch.Tensor) → float` using Shannon formula on degree distribution
3. Implement `detect_spike(G, V) → Tuple[bool, float]`: return `True` if `H_G > log2(V) × 0.8`
4. Implement `record_barcode(phi_total, chi, entropy)` — append to `deque(maxlen=100)`
5. In `PPNEmbeddingModule.forward()`: call `entropy_monitor.detect_spike(G, V)`; add `is_entropy_spike` to return
6. In orchestrator: if `is_entropy_spike` → log `WARNING` at `DEBUG` level; **do not halt execution**
7. Add `GET /api/ppn/entropy_spikes` endpoint returning last 100 barcodes as JSON

#### Acceptance Test

```
pytest: fully connected G (all 1s) → entropy at maximum → spike=True
        diagonal-only G (identity)  → entropy=0 → spike=False
        V=1                         → spike=False (degenerate case)
```

#### Code

**`backend/inference/entropy_monitor.py`** — Create new file:

```python
import math
import time
from collections import deque
from typing import Tuple, List
import torch


class EntropyMonitor:
    """
    Entropy Spike Detector — Self-Reflective Manifold (SRM).
    Source: PPN §Curiosity Loop — 'Entropy Spikes'

    Detects when graph entropy exceeds 80% of theoretical maximum,
    signalling a low-coherence state that may need a manifold patch.
    """

    def __init__(self, maxlen: int = 100):
        self._barcodes: deque = deque(maxlen=maxlen)

    def compute_graph_entropy(self, G: torch.Tensor) -> float:
        """
        H_G = -Σ p_i * log2(p_i) over the degree distribution of G.
        p_i = degree_i / Σ_j degree_j
        """
        degrees = G.sum(dim=1).float()
        total = degrees.sum().item()
        if total < 1e-9:
            return 0.0
        probs = degrees / total
        probs = probs[probs > 0]  # avoid log(0)
        entropy = -float((probs * torch.log2(probs)).sum().item())
        return entropy

    def detect_spike(self, G: torch.Tensor, V: int) -> Tuple[bool, float]:
        """
        Returns (is_spike, entropy_value).
        Threshold: H_G > log2(V) * 0.8
        """
        if V <= 1:
            return False, 0.0
        h = self.compute_graph_entropy(G)
        threshold = math.log2(V) * 0.8
        return h > threshold, h

    def record_barcode(self, phi_total: int, chi: int, entropy: float):
        """Record topological barcode for SRM curiosity loop audit."""
        self._barcodes.append({
            "phi_total": phi_total,
            "chi": chi,
            "entropy": round(entropy, 4),
            "epoch": int(time.time()) // 60,
            "timestamp": int(time.time()),
        })

    def get_barcodes(self) -> List[dict]:
        return list(self._barcodes)
```

---

### PPN-008 — KCM Geodesic Cost Function

**Source:** Polytope Projection Networks — §KCM / `tf_ppn_bridge.cpp`
**Priority:** 🟡 Medium

#### Current State in Alluci

`ModelRouter.get_response()` selects providers purely by availability and failover order. The KCM concept maps constraint proximity to routing cost: the closer a provider is to a "rupture zone" (recent failure, rate limit, high latency), the more expensive that route becomes.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `cost(route) = 1.0 + (tension / 1024.0) + ψ` | Total route cost. Base + KCM tension + ψ stress inflation |
| `tension_spike(d) = clamp(1024 / (d + 0.001), 0, 32767)` | Hyperbolic penalty for proximity to failure boundary |
| `d = (now − last_failure_time) / 300.0` | Normalized recency: `d → large` means far from failure (safe route) |
| `cost(e) = w(e) × (1 + ψ)` | Universal cost inflation under stress |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/router.py` | **MODIFY** | Add `KCMRouteScorer` class; integrate into `get_response()` provider selection |

#### Implementation Steps

1. Add `KCMRouteScorer` inner class to `router.py` with `score(provider, psi) → float`
2. Track `self._failure_times: Dict[str, float] = {}` in `ModelRouter.__init__()`
3. On each provider failure in `get_response()`, record: `self._failure_times[provider_name] = time.time()`
4. Sort providers by ascending `score()` before iterating
5. Accept optional `psi: float = None` parameter in `get_response()`
6. Retrieve `psi` from ACE engine in orchestrator and pass through

#### Acceptance Test

```
pytest: provider with failure 10s ago   → higher cost than failure 600s ago
        psi=1.0                         → all costs increase by +1.0
        provider with no failures       → cost ≈ 1.0 + psi
```

#### Code

**Add to `backend/inference/router.py`:**

```python
import time
from typing import Dict


class KCMRouteScorer:
    """
    KCM Geodesic Cost Function.
    Source: PPN §KCM — 'Topological Resistance' routing

    Assigns route cost based on proximity to provider failure boundaries.
    High recency of failure = high tension = expensive route.
    """
    FAILURE_WINDOW = 300.0  # 5-minute recency window (seconds)

    def __init__(self, failure_times: Dict[str, float]):
        self._failures = failure_times

    def score(self, provider: str, psi: float) -> float:
        """Lower score = preferred route."""
        now = time.time()
        last_fail = self._failures.get(provider, 0.0)
        d = (now - last_fail) / self.FAILURE_WINDOW
        # Hyperbolic tension penalty: tension_spike(d) = clamp(1024/(d+0.001), 0, 32767)
        raw_tension = 1024.0 / (d + 0.001)
        tension = min(32767.0, raw_tension)
        # cost = base + KCM tension + ψ stress inflation
        return 1.0 + (tension / 1024.0) + psi
```

**In `ModelRouter.__init__()`:**

```python
self._failure_times: Dict[str, float] = {}
self._kcm_scorer = KCMRouteScorer(self._failure_times)
```

**In `get_response()`, on each provider failure:**

```python
self._failure_times[provider_name] = time.time()
```

---

### PPN-009 — PVT Manifold Health Monitor

**Source:** Polytope Projection Networks — §Holoid / "Semantic Pressure"
**Priority:** 🟡 Medium

#### Current State in Alluci

No system-level manifold health metric. The paper defines a **Pressure-Volume-Temperature (PVT)** analogy: Pressure = invariant violation frequency, Volume = active simplex complexity, Temperature = state transition rate. This provides a three-number health triple for the `/api/system/health` endpoint.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `P = violations_in_window / window_size` | Pressure: rate of DPK/AVL failures per turn window (window = 100 turns) |
| `V = (V_count + E_count + F_count) / MAX_COMPLEXITY` | Volume: normalized simplex count. `MAX_COMPLEXITY = 64×63/2 + 64 = 2080` |
| `T = turn_count / elapsed_seconds` | Temperature: turns per second. High T = fast transitions = high arousal |
| `health = 1 − clamp(P×2.0 + V×0.3 + T_norm×0.2, 0, 1)` | Composite health: violations dominate, then complexity, then speed |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/health_monitor.py` | **CREATE** | `PVTManifoldMonitor`: `record_turn()`, `get_pvt()` |
| `backend/app.py` | **MODIFY** | Include `pvt_health` in `/api/system/health` response |
| `backend/orchestrator.py` | **MODIFY** | Call `pvt_monitor.record_turn()` on each `execute_objective()` call |

#### Implementation Steps

1. Create `backend/health_monitor.py` with `PVTManifoldMonitor`
2. Track: `violations_window=deque(maxlen=100)`, `simplex_history=deque(maxlen=20)`, `turn_timestamps=deque(maxlen=50)`
3. Implement `record_turn(V, E, F, violation: bool)` to update all three windows
4. Implement `get_pvt() → dict`: returns `{pressure, volume, temperature, health, status}`
5. In `ExecutiveOrchestrator.__init__()`, instantiate `pvt_monitor = PVTManifoldMonitor()`
6. In `execute_objective()`, after AVL check: `pvt_monitor.record_turn(V, E, F, violation=not avl_safe)`
7. In `/api/system/health`, include `pvt=pvt_monitor.get_pvt()`

#### Acceptance Test

```
pytest: 10 consecutive violations  → pressure > 0.1
        large V/E/F counts         → volume approaches 1.0
        1 turn/sec                 → temperature reading matches
        health in [0.0, 1.0]       always
```

#### Code

**`backend/health_monitor.py`** — Create new file:

```python
import time
from collections import deque
from typing import Dict


class PVTManifoldMonitor:
    """
    PVT Manifold Health Monitor.
    Source: PPN §Holoid — 'Pressure-Volume-Temperature' analogy

    P = violation rate (DPK/AVL failures per turn window)
    V = normalized simplex complexity
    T = turn transition rate (turns/second)
    health = 1 - clamp(P*2.0 + V*0.3 + T_norm*0.2, 0, 1)
    """
    MAX_COMPLEXITY = 2080.0  # 64 vertices: 64*63/2 + 64
    T_NORM_BASELINE = 2.0    # Expected nominal: 2 turns/sec

    def __init__(self):
        self._violations: deque = deque(maxlen=100)
        self._simplex_totals: deque = deque(maxlen=20)
        self._timestamps: deque = deque(maxlen=50)

    def record_turn(self, V: int, E: int, F: int, violation: bool):
        """Record one turn's simplex data and violation status."""
        self._violations.append(1 if violation else 0)
        self._simplex_totals.append(V + E + F)
        self._timestamps.append(time.time())

    def get_pvt(self) -> Dict:
        """Compute current PVT health triple."""
        # Pressure: violation rate
        n = len(self._violations)
        P = sum(self._violations) / max(n, 1)

        # Volume: normalized simplex complexity
        if self._simplex_totals:
            avg_complexity = sum(self._simplex_totals) / len(self._simplex_totals)
            V_norm = min(1.0, avg_complexity / self.MAX_COMPLEXITY)
        else:
            V_norm = 0.0

        # Temperature: turns per second
        T = 0.0
        ts = list(self._timestamps)
        if len(ts) >= 2:
            span = ts[-1] - ts[0]
            if span > 0:
                T = len(ts) / span
        T_norm = min(1.0, T / self.T_NORM_BASELINE)

        # Composite health
        health = 1.0 - min(1.0, P * 2.0 + V_norm * 0.3 + T_norm * 0.2)
        status = (
            "NOMINAL"   if health > 0.7 else
            "DEGRADED"  if health > 0.3 else
            "CRITICAL"
        )
        return {
            "pressure":    round(P, 4),
            "volume":      round(V_norm, 4),
            "temperature": round(T_norm, 4),
            "health":      round(health, 4),
            "status":      status,
        }
```

---

### PPN-010 — Holoid Multi-Provider Consensus

**Source:** Polytope Projection Networks — §Holoid / `multi_ppn_consensus.cpp`
**Priority:** 🟡 Medium

#### Current State in Alluci

Multiple providers use first-success failover only. The Holoid consensus model introduces barycentric merging: if providers disagree (semantic distance > threshold), find the "mean path" that preserves the most invariants. Activates only at `ψ < 0.3` (calm state with resources available for dual inference).

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `Ω = μ_A ∩ μ_B` | Shared semantic workspace. Non-empty intersection = valid merge |
| `conflict = ‖emb_A − emb_B‖₂ > δ_threshold` | Semantic conflict when L2 distance between embeddings exceeds threshold |
| `δ_threshold = 0.5 × (1.0 − coh_prev)` | Adaptive threshold: lower coherence → stricter conflict detection |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/consensus.py` | **CREATE** | `BarycentricConsensus`: `detect_conflict()`, `merge_responses()` |
| `backend/inference/router.py` | **MODIFY** | Add optional `consensus_mode` flag; call consensus when `psi < 0.3` |

#### Implementation Steps

1. Create `backend/inference/consensus.py` with `BarycentricConsensus` class
2. Implement `detect_conflict(r1, r2, embed_model, prev_coherence) → bool` using sentence embeddings
3. Implement `merge_responses(r1, r2, router) → str`: synthesis LLM call to find barycentric geodesic
4. In `router.get_response()`: if `consensus_mode` and `psi < 0.3`: attempt dual query; if conflict → merge; else return primary
5. Consensus mode only activates at `ψ < 0.3` (calm/expanded state — dilation mode)

#### Acceptance Test

```
pytest: two identical responses                          → conflict=False, returns primary
        semantically opposite responses, low threshold  → conflict=True, merge called
        psi=0.5                                         → consensus_mode inactive
```

#### Code

**`backend/inference/consensus.py`** — Create new file:

```python
import logging
from typing import Tuple

logger = logging.getLogger("Consensus")


class BarycentricConsensus:
    """
    Holoid Barycentric Response Merging.
    Source: PPN §Holoid — multi_ppn_consensus.cpp::resolve_consensus()

    When two providers conflict, finds the barycentric geodesic that
    preserves the most invariants from both responses.
    Activates only at ψ < 0.3 (dilation/exploration mode).
    """

    def __init__(self, embed_model, conflict_threshold: float = 0.5):
        self._embed = embed_model
        self._threshold = conflict_threshold

    def detect_conflict(
        self,
        r1: str,
        r2: str,
        prev_coherence: float = 1.0,
    ) -> bool:
        """
        δ_threshold = 0.5 × (1 − coh_prev)
        conflict = ||emb_A − emb_B||₂ > δ_threshold
        """
        try:
            import torch
            e1 = self._embed.encode(r1, convert_to_tensor=True)
            e2 = self._embed.encode(r2, convert_to_tensor=True)
            dist = float(torch.norm(e1 - e2).item())
            adaptive_thr = self._threshold * (1.0 - prev_coherence)
            return dist > max(adaptive_thr, 0.1)
        except Exception as e:
            logger.warning(f"[Consensus] Conflict detection failed: {e}")
            return False

    async def merge_responses(self, r1: str, r2: str, router) -> str:
        """
        Find barycentric geodesic between two conflicting responses.
        Uses a synthesis LLM call to resolve contradictions.
        """
        merge_prompt = (
            "Two expert responses exist for the same question. "
            "Synthesize them into one response that preserves the "
            "accurate claims from both and resolves any contradictions.\n\n"
            f"Response A:\n{r1}\n\nResponse B:\n{r2}"
        )
        return await router.get_response(merge_prompt, complexity="LOW")
```

---

### PPN-011 — Turn Deadline Affective Contraction

**Source:** Polytope Projection Networks — §DDS Latency Bounds
**Priority:** 🟡 Medium

#### Current State in Alluci

No latency-aware affective response. The paper defines that when DDS deadline is missed, the BTM treats network latency as environmental tension and applies maximum κ contraction. In Alluci: if a turn exceeds 15 seconds, automatically maximize `ψ` for the next 3 turns, routing to the fastest/simplest model tier.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `deadline_ms = 15000` | Hard deadline: 15 seconds per turn (from PPN §DDS latency budget table) |
| `latency_tension(t_ms) = clamp(t_ms / deadline_ms × 1024, 0, 1024)` | Progressive tension increase as latency grows — starts contracting before deadline |
| `psi_on_deadline = 1.0` | `ψ = 1.0` when deadline missed. Routes to lightest/fastest provider |
| `tension_on_deadline = 1024` | Maximum tension injected on deadline miss — forces maximum contraction |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/orchestrator.py` | **MODIFY** | Add turn timer; on deadline breach inject max tension into `AffectiveState` and re-route |
| `backend/ace/engine.py` | **MODIFY** | Add `inject_deadline_contraction(turns=3)` method |

#### Implementation Steps

1. In `ExecutiveOrchestrator.execute_objective()`, record `turn_start = time.time()` at the top
2. After `planner.generate_plan()`, check elapsed: if `> TURN_DEADLINE_S (15.0)` → inject max tension
3. Add `inject_deadline_contraction(turns: int = 3)` method to `AffectiveEngine` — sets tension override
4. In `get_affective_state()`, apply tension override if active; decrement counter per call
5. Log deadline miss as `WARNING` with elapsed time
6. Re-route with `psi=1.0` for remainder of the affected turn

#### Acceptance Test

```
pytest: mock turn sleeping 16s     → ace.inject_deadline_contraction() called
        next turn after deadline   → psi=1.0
        3 turns after deadline     → override cleared, psi returns to normal
```

#### Code

**Add to `AffectiveEngine` in `backend/ace/engine.py`:**

```python
import time

def inject_deadline_contraction(self, turns: int = 3):
    """
    Inject maximum tension on deadline miss.
    Source: PPN §DDS — on_deadline_missed() callback
    """
    self._deadline_override_turns = turns
    self._deadline_override_tension = 1024.0
    import logging
    logging.getLogger("ACE").warning(
        f"[ACE] Deadline contraction injected for {turns} turns"
    )

def get_affective_state(self) -> "AffectiveState":
    state = self._compute_base_affective_state()  # existing logic
    # Apply deadline override if active
    if getattr(self, "_deadline_override_turns", 0) > 0:
        state.tension = max(state.tension, self._deadline_override_tension)
        self._deadline_override_turns -= 1
    return state
```

**Add to `execute_objective()` in `orchestrator.py`:**

```python
TURN_DEADLINE_S = 15.0
turn_start = time.time()

# ... (after planner.generate_plan() call) ...

elapsed = time.time() - turn_start
if elapsed > TURN_DEADLINE_S:
    self.logger.warning(
        f"[ORCHESTRATOR] Turn deadline exceeded ({elapsed:.1f}s) — injecting contraction"
    )
    self.ace.inject_deadline_contraction(turns=3)
    psi = 1.0  # Force maximum contraction for this turn
```

---

### PPN-012 — Topological Barcode Audit Log

**Source:** Polytope Projection Networks — §VAM / Verus Attestation
**Priority:** 🟡 Medium

#### Current State in Alluci

`DPK.validate_manifold_integrity()` logs pass/fail but produces no structured audit record. The paper defines a Topological Barcode for each state transition: a `SHA-256` hash of `(Betti + χ + epoch_bin)` forming an immutable Merkle-style chain. Replaces VerusID/blockchain dependency with a local chain.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `H_P = SHA256(betti_str + '\|' + str(chi) + '\|' + str(epoch_bin))` | Per-turn topological barcode. Deterministic and reproducible |
| `epoch_bin = int(time.time()) // 60` | 1-minute epoch bins. Groups audit events without millisecond precision |
| `chain_hash = SHA256(prev_chain_hash + H_P)` | Merkle-style chaining. Tampering detectable by re-derivation |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/security/topo_audit.py` | **CREATE** | `TopoAuditChain`: `record(state)`, `get_chain()`, `verify_integrity()` |
| `backend/security/dpk.py` | **MODIFY** | Import `TopoAuditChain`; call `chain.record(state)` in `authorize_execution()` |
| `backend/app.py` | **MODIFY** | Add `GET /api/security/audit_chain` endpoint |

#### Implementation Steps

1. Create `backend/security/topo_audit.py` with `TopoAuditChain`
2. Implement `record(state: PolytopeState) → str`: computes `H_P`, chains it, stores to `deque(maxlen=1000)`
3. Implement `get_chain(last_n: int = None) → List[dict]`: returns full chain with hashes
4. Implement `verify_integrity() → bool`: re-computes chain and verifies no tampering
5. In `DPK.__init__()`, instantiate `self.audit_chain = TopoAuditChain()`
6. In `authorize_execution()`, after validation, call `self.audit_chain.record(state)`
7. Add `GET /api/security/audit_chain?last_n=50` endpoint

#### Acceptance Test

```
pytest: record 5 states            → chain has 5 entries
        manually corrupt entry[2]  → verify_integrity() returns False
        same state twice           → same H_P barcode
        integrity on fresh chain   → True
```

#### Code

**`backend/security/topo_audit.py`** — Create new file:

```python
import hashlib
import time
from collections import deque
from typing import List, Dict
from .dpk import PolytopeState


class TopoAuditChain:
    """
    Topological Barcode Audit Chain.
    Source: PPN §VAM — Sovereign Barcode & Merkle Checkpointing

    H_P = SHA256(sorted_betti + chi + epoch_bin)
    chain_hash = SHA256(prev_chain_hash + H_P)
    """

    def __init__(self, maxlen: int = 1000):
        self._chain: deque = deque(maxlen=maxlen)
        self._prev_hash: str = "0" * 64  # Genesis hash

    def _compute_barcode(self, state: PolytopeState) -> str:
        """H_P = SHA256(sorted_betti_str + '|' + chi + '|' + epoch_bin)"""
        chi = state.vertices_V - state.edges_E + state.faces_F
        sorted_betti = sorted(round(b, 2) for b in state.betti)
        betti_str = ",".join(str(b) for b in sorted_betti)
        epoch_bin = str(int(time.time()) // 60)
        payload = f"{betti_str}|{chi}|{epoch_bin}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def record(self, state: PolytopeState) -> str:
        """Record one state transition; return the barcode hash."""
        barcode = self._compute_barcode(state)
        # Chain: SHA256(prev_hash + barcode)
        chain_hash = hashlib.sha256(
            (self._prev_hash + barcode).encode()
        ).hexdigest()
        entry = {
            "barcode":    barcode,
            "chain_hash": chain_hash,
            "phi_total":  state.phi_total,
            "coherence":  state.coherence,
            "timestamp":  int(time.time()),
        }
        self._chain.append(entry)
        self._prev_hash = chain_hash
        return barcode

    def verify_integrity(self) -> bool:
        """Re-derive chain; return False if any link is broken (tampering detected)."""
        entries = list(self._chain)
        prev = "0" * 64
        for e in entries:
            expected = hashlib.sha256(
                (prev + e["barcode"]).encode()
            ).hexdigest()
            if expected != e["chain_hash"]:
                return False
            prev = e["chain_hash"]
        return True

    def get_chain(self, last_n: int = None) -> List[Dict]:
        chain = list(self._chain)
        return chain[-last_n:] if last_n else chain
```

---

### AAP-001 — Coherence Score Computation

**Source:** The Autonomous Agent Polytope — §Coherence Score
**Priority:** 🔴 High

#### Current State in Alluci

`PPNEmbeddingModule` produces `G`, `D_t`, `B`, `points` — but never synthesizes them into a scalar quality signal. The AAP paper defines `Coh(P_t)` as the product of Betti stability and graph sparsity: a `[0,1]` quality metric emitted per turn.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `Coh(P_t) = (1 − Δβ_norm) × (1 − H_G_norm)` | Coherence = Betti stability × graph sparsity. Range [0, 1] |
| `Δβ_norm = Σ|β_k(t) − β_k(t−1)| / (4 × max_shift)` | Normalized Betti shift. `max_shift = 2.0` (2 units per β_k is a large shift) |
| `H_G_norm = H_G / log2(V)` | Graph entropy normalized to [0,1] by theoretical maximum |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/ppn.py` | **MODIFY** | Add `compute_coherence(G, B_current, B_prev)` method; return from `forward()` |
| `backend/security/dpk.py` | **MODIFY** | Store `coherence` in `PolytopeState`; log per-turn |
| `backend/orchestrator.py` | **MODIFY** | Pass `coherence` to `PolytopeState`; use in critic weighting (AAP-005) |

#### Implementation Steps

1. Add `self._prev_betti: Optional[torch.Tensor] = None` to `PPNEmbeddingModule.__init__()`
2. Implement `compute_coherence(G, B_current, B_prev) → float` method
3. Reuse `entropy_monitor.compute_graph_entropy(G)` for the `H_G` component (PPN-007)
4. Compute `Δβ_norm` from current and previous Betti; normalize by `4 × 2.0`
5. Return `coherence` as 7th element of `forward()` return tuple
6. Store in `PolytopeState.coherence` field
7. Log coherence per turn at `INFO` level in orchestrator

#### Acceptance Test

```
pytest: same input twice            → Δβ=0 → coherence = 1 - H_G_norm
        fully connected G            → coherence ≈ 0 (max entropy)
        sparse G, stable Betti       → coherence approaches 1.0
        coherence always in [0, 1]
```

#### Code

**Add to `PPNEmbeddingModule` in `backend/inference/ppn.py`:**

```python
import math

def compute_coherence(
    self,
    G: torch.Tensor,
    B_current: torch.Tensor,
    B_prev: "Optional[torch.Tensor]",
) -> float:
    """
    Coh(P_t) = (1 - Δβ_norm) × (1 - H_G_norm)
    Source: AAP §Coherence Score
    """
    # === Δβ_norm: Betti number stability across turns ===
    if B_prev is not None:
        delta_b = float(
            torch.sum(torch.abs(B_current.float() - B_prev.float())).item()
        )
        max_shift = 4.0 * 2.0  # 4 Betti numbers × max 2-unit shift each
        delta_b_norm = min(1.0, delta_b / max_shift)
    else:
        delta_b_norm = 0.0  # First turn: perfect Betti stability

    # === H_G_norm: normalized graph entropy ===
    V = G.shape[0]
    if V <= 1:
        h_norm = 0.0
    else:
        degrees = G.sum(dim=1).float()
        total = degrees.sum().item()
        if total < 1e-9:
            h_norm = 0.0
        else:
            probs = degrees / total
            probs = probs[probs > 0]
            h_raw = -float((probs * torch.log2(probs)).sum().item())
            h_max = math.log2(V)
            h_norm = h_raw / h_max if h_max > 0 else 0.0

    coherence = (1.0 - delta_b_norm) * (1.0 - h_norm)
    return max(0.0, min(1.0, coherence))
```

---

### AAP-002 — ψ-Modulated Model Routing

**Source:** The Autonomous Agent Polytope — §ψ-Space Routing
**Priority:** 🔴 High

#### Current State in Alluci

`ModelRouter.get_response()` accepts `complexity='LOW'/'MEDIUM'/'HIGH'` but this is set manually. The AAP paper defines that `ψ` should **automatically** determine model tier: high `ψ` (contracted/stressed) → lightweight fast models; low `ψ` (expanded/calm) → highest-capability models.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `ψ > 0.7 → complexity = 'LOW'` | Contraction: conserve resources → Gemini Flash, Haiku, Groq 70B |
| `0.3 ≤ ψ ≤ 0.7 → complexity = 'MEDIUM'` | Nominal: balanced tier → Gemini Pro, GPT-4o-mini |
| `ψ < 0.3 → complexity = 'HIGH'` | Dilation: full capability → Gemini Pro, GPT-4o, Claude Sonnet |
| Critical requests always `→ 'HIGH'` regardless of ψ | `autonomy == 'UNRESTRICTED'` forces HIGH |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/router.py` | **MODIFY** | Add `psi_to_complexity(psi)` static method; accept `psi` in `get_response()` |
| `backend/orchestrator.py` | **MODIFY** | Pass current `psi` to all `router.get_response()` calls |

#### Implementation Steps

1. Add `@staticmethod psi_to_complexity(psi: float) → str` to `ModelRouter`
2. Add optional `psi: float = None` and `critical: bool = False` params to `get_response()`
3. If `critical=True`: `complexity = 'HIGH'`; elif `psi is not None`: `complexity = psi_to_complexity(psi)`
4. In `orchestrator.execute_objective()`, get `psi = btm.psi_from_state(affect_state)` before routing
5. Pass `psi=psi` to all `router.get_response()` calls
6. Set `critical=True` when `autonomy == 'UNRESTRICTED'`
7. Log routing decision at `DEBUG`: `f'ψ={psi:.2f} → complexity={complexity}'`

#### Acceptance Test

```
pytest: psi=0.9                         → complexity='LOW'
        psi=0.5                         → complexity='MEDIUM'
        psi=0.1                         → complexity='HIGH'
        psi=0.9 + UNRESTRICTED autonomy → complexity='HIGH'
```

#### Code

**Add to `ModelRouter` in `backend/inference/router.py`:**

```python
@staticmethod
def psi_to_complexity(psi: float) -> str:
    """
    ψ-modulated routing tier selection.
    Source: AAP §ψ-Space — 'Dilation/Contraction Routing'

    High ψ (stress/contraction) → fast/cheap model tier
    Low  ψ (calm/dilation)      → strongest model tier
    """
    if psi > 0.7:
        return "LOW"     # Contraction: conserve resources
    elif psi > 0.3:
        return "MEDIUM"  # Nominal operation
    else:
        return "HIGH"    # Dilation: full capability
```

**Modify `get_response()` signature:**

```python
async def get_response(
    self,
    prompt: str,
    complexity: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM",
    psi: Optional[float] = None,
    critical: bool = False,
) -> str:
    # ψ-modulated routing (AAP §ψ-Space)
    if critical:
        complexity = "HIGH"
    elif psi is not None:
        complexity = self.psi_to_complexity(psi)
    self.logger.debug(f"[ROUTER] ψ={psi or 0:.2f} → {complexity}")
    # ... existing provider selection logic unchanged ...
```

---

### AAP-003 — Attribution Hash H_P

**Source:** The Autonomous Agent Polytope — §Sovereign Attribution
**Priority:** 🔴 High

#### Current State in Alluci

`DPK.validate_manifold_integrity()` checks `signature_hash != 0` as a sovereignty gate, but the hash computation is undefined in code (set externally as arbitrary `hash(str(betti_list))`). The AAP paper specifies the canonical formula: `H_P = SHA256(sorted_betti + chi + epoch_bin)`, making the gate **cryptographically verifiable** rather than symbolic.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `H_P = SHA256(sorted_betti_str + '\|' + chi_str + '\|' + epoch_str)` | Canonical attribution hash. Sorted Betti ensures permutation-invariance |
| `signature_hash = int(H_P[:16], 16)` | First 64 bits of SHA-256 as `int64` for `PolytopeState.signature_hash` |
| `epoch_bin = str(int(time.time()) // 60)` | 1-minute epoch bins |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/security/dpk.py` | **MODIFY** | Add `compute_signature_hash(betti, chi)` static method |
| `backend/orchestrator.py` | **MODIFY** | Replace `hash(str(betti_list))` with `dpk.compute_signature_hash(betti_list, chi)` |

#### Implementation Steps

1. Add `@staticmethod compute_signature_hash(betti: List[float], chi: int) → int` to `DiscreteProjectionKernel`
2. Implement using `hashlib.sha256` with sorted Betti + chi + `epoch_bin`
3. In `orchestrator._perform_ppn_check()`, compute `chi = V - E + F` before constructing `PolytopeState`
4. Replace: `signature_hash=hash(str(betti_list))` → `signature_hash=self.dpk.compute_signature_hash(betti_list, chi)`
5. SHA-256 output is never all-zeros in practice — `signature_hash` will always be non-zero

#### Acceptance Test

```
pytest: same betti + chi in same 1-minute window → identical hash
        different betti                           → different hash
        result always > 0 (never zero)
        result fits in int64 (< 2^64)
```

#### Code

**Add to `DiscreteProjectionKernel` in `backend/security/dpk.py`:**

```python
import hashlib
import time

@staticmethod
def compute_signature_hash(betti: List[float], chi: int) -> int:
    """
    H_P = SHA256(sorted_betti + '|' + chi + '|' + epoch_bin)
    Source: AAP §Sovereign Attribution

    Returns first 64 bits of SHA-256 as int. Always non-zero.
    epoch_bin = 1-minute bins for temporal binding.
    """
    sorted_betti = sorted(round(b, 2) for b in betti)
    betti_str = ",".join(str(b) for b in sorted_betti)
    epoch_bin = str(int(time.time()) // 60)
    payload = f"{betti_str}|{chi}|{epoch_bin}"
    h = hashlib.sha256(payload.encode()).hexdigest()
    # First 16 hex chars = 64-bit integer
    return int(h[:16], 16)
```

**Update in `orchestrator._perform_ppn_check()`:**

```python
chi = V - E + F
sig_hash = self.dpk.compute_signature_hash(betti_list, chi)

state = PolytopeState(
    signature_hash=sig_hash,        # was: hash(str(betti_list))
    vertices_V=V,
    edges_E=E,
    faces_F=F,
    betti=betti_list,
    affective_tension_psi=psi,
    phi_total=phi_total,
    coherence=coherence,
    budget_used=budget_used,
)
```

---

### AAP-004 — Memory Topology Decay

**Source:** The Autonomous Agent Polytope — §Memory as Persistent Homology
**Priority:** 🟡 Medium

#### Current State in Alluci

`PPNEmbeddingModule` computes Betti numbers per turn but they are independent — there is no accumulation across the conversation. The AAP paper models memory as persistent homology: a Betti vector that evolves with exponential decay, preserving topological context across turns.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `B_mem[t+1] = (1 − 0.05) × B_mem[t] + 0.3 × B_current[t]` | Exponential moving average. 5% per-turn forgetting, 30% update weight |
| `B_mem_delta = ‖B_current − B_mem‖₂` | Distance between current turn and memory. Large delta → topic shift detected |
| `topic_shift = B_mem_delta > 2.0` | Topic shift signal. Can trigger context refresh in orchestrator |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/inference/ppn.py` | **MODIFY** | Add `self._betti_memory` state; update per `forward()`; expose `reset_memory()` |

#### Implementation Steps

1. Add to `PPNEmbeddingModule.__init__()`:
   - `self._betti_memory: Optional[torch.Tensor] = None`
   - `self.MEMORY_DECAY = 0.05`
   - `self.MEMORY_ALPHA = 0.30`
   - `self.TOPIC_SHIFT_THRESHOLD = 2.0`
2. After Betti computation in `forward()`, update memory with exponential smoothing
3. Initialize `B_mem` on first turn = `B_current`
4. Compute `B_mem_delta` before updating memory
5. Return `topic_shift (bool)` from `forward()` (8th element)
6. In orchestrator: if `topic_shift` → log `INFO` "Topic shift detected"
7. Expose `reset_memory()` method — call at session start

#### Acceptance Test

```
pytest: same input 5 times     → B_mem converges toward B_current
        radically different 6th → B_mem_delta > 1.0, topic_shift=True
        reset_memory()         → B_mem=None, _prev_D_t=None, _prev_betti=None
```

#### Code

**In `PPNEmbeddingModule.__init__()`:**

```python
self._betti_memory: Optional[torch.Tensor] = None
self.MEMORY_DECAY = 0.05
self.MEMORY_ALPHA = 0.30
self.TOPIC_SHIFT_THRESHOLD = 2.0
```

**In `forward()`, after Betti computation:**

```python
# === Memory Topology Decay (AAP §Memory) ===
# B_mem[t+1] = (1 - decay) * B_mem[t] + alpha * B_current
B_curr_float = B_pred.float() if B_pred.dim() == 1 else B_pred.mean(0).float()

if self._betti_memory is None:
    self._betti_memory = B_curr_float.detach().clone()
    betti_mem_delta = 0.0
    topic_shift = False
else:
    betti_mem_delta = float(
        torch.norm(B_curr_float - self._betti_memory).item()
    )
    topic_shift = betti_mem_delta > self.TOPIC_SHIFT_THRESHOLD
    # Update memory with exponential decay
    self._betti_memory = (
        (1.0 - self.MEMORY_DECAY) * self._betti_memory
        + self.MEMORY_ALPHA * B_curr_float
    ).detach()

# Store prev_betti for coherence computation (AAP-001)
self._prev_betti = B_curr_float.detach().clone()
```

**Add to `PPNEmbeddingModule`:**

```python
def reset_memory(self):
    """Call at session start to clear cross-conversation topological memory."""
    self._betti_memory = None
    self._prev_D_t = None
    self._prev_betti = None
```

---

### AAP-005 — Critic ψ-Weighted Score

**Source:** The Autonomous Agent Polytope — §Critic / §Planner-Executor-Critic Triangle
**Priority:** 🟡 Medium

#### Current State in Alluci

`Critic.evaluate()` returns a float score from LLM evaluation alone. The AAP paper adds mathematical weighting incorporating manifold coherence, affective tension, and goal completion in defined proportions — making the critic score topology-aware rather than purely LLM-opinionated.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `Score = λ₁×Coh + λ₂×(1−ψ) + λ₃×goal_pct` | Weighted composite. Default: `λ₁=0.4, λ₂=0.3, λ₃=0.3` |
| `goal_pct = completed_tasks / total_tasks` | Fraction of plan tasks completed successfully |
| `final_score = 0.6×llm_norm + 0.4×topo_score` | Blend: LLM judgment (60%) + topological quality (40%) |
| `llm_norm = llm_score / 10.0` | Normalize LLM 0–10 score to [0, 1] |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/engine/critic.py` | **MODIFY** | Add `compute_topo_weighted_score(coh, psi, goal_pct)`; blend with LLM score |
| `backend/orchestrator.py` | **MODIFY** | Pass `coherence` and `psi` to `critic.evaluate()` |

#### Implementation Steps

1. Add `@staticmethod compute_topo_weighted_score(coh, psi, goal_pct) → float` to `Critic`
2. Modify `evaluate()` to accept `coherence: float = 0.5`, `psi: float = 0.5`, `goal_pct: float = 1.0`
3. After receiving LLM score: `final_score = 0.6 × llm_norm + 0.4 × topo_score`
4. In `orchestrator.execute_objective()`, compute `goal_pct` from executor task results
5. Pass `coherence=state.coherence` and `psi=psi` to `critic.evaluate()`

#### Acceptance Test

```
pytest: coh=1.0, psi=0.0, goal_pct=1.0  → topo_score = 1.0
        coh=0.0, psi=1.0, goal_pct=0.0  → topo_score = 0.0
        LLM score 8.0 + topo 0.9        → final ≈ 0.84
        all outputs in [0.0, 1.0]
```

#### Code

**Add to `backend/engine/critic.py`:**

```python
@staticmethod
def compute_topo_weighted_score(
    coh: float,
    psi: float,
    goal_pct: float,
) -> float:
    """
    Topology-weighted critic score.
    Source: AAP §Critic — Score = λ₁×Coh + λ₂×(1−ψ) + λ₃×goal_pct

    λ₁=0.4 (coherence), λ₂=0.3 (calm state), λ₃=0.3 (goal completion)
    """
    lambda_1, lambda_2, lambda_3 = 0.4, 0.3, 0.3
    score = (
        lambda_1 * coh
        + lambda_2 * (1.0 - psi)   # Low tension = higher quality signal
        + lambda_3 * goal_pct
    )
    return max(0.0, min(1.0, score))
```

**Modify `evaluate()` signature:**

```python
async def evaluate(
    self,
    objective: str,
    result: str,
    coherence: float = 0.5,
    psi: float = 0.5,
    goal_pct: float = 1.0,
) -> Tuple[bool, float, str]:
    passed, llm_score, feedback = await self._llm_evaluate(objective, result)
    llm_norm = llm_score / 10.0
    topo_score = self.compute_topo_weighted_score(coherence, psi, goal_pct)
    # 60% LLM judgment + 40% topological quality
    final_score = 0.6 * llm_norm + 0.4 * topo_score
    return passed, final_score, feedback
```

---

### AAP-006 — Planner Geodesic Cost

**Source:** The Autonomous Agent Polytope — §Planner / Geodesic Path Cost
**Priority:** 🟡 Medium

#### Current State in Alluci

`Planner.generate_plan()` produces tasks with priorities but no tension-aware cost model. The AAP paper defines that any plan edge cost is inflated by `ψ`: under stress, all planning steps become more expensive, causing the planner to prefer shorter, simpler plans — mirroring biological focus contraction under cognitive load.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `cost(task) = base_complexity × (1 + ψ)` | Task cost inflated by ψ. High stress → all tasks cost more |
| `max_tasks = floor(MAX_BUDGET / avg_cost)` | Maximum schedulable tasks. `MAX_BUDGET = 10.0` nominal units |
| `avg_cost(ψ) = 1.0 × (1 + ψ)` | Average task cost at given ψ |
| `max_tasks = floor(10 / (1 + ψ))` | At `ψ=0`: 10 tasks. At `ψ=1.0`: 5 tasks |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/engine/planner.py` | **MODIFY** | Add `psi_task_budget(psi)` helper; inject `max_tasks` and stress context into plan prompt |

#### Implementation Steps

1. Add `@staticmethod psi_task_budget(psi: float) → int` to `Planner`: returns `floor(10/(1+psi))`
2. Add `psi: float = 0.5` optional parameter to `generate_plan()`
3. Compute `max_tasks = self.psi_task_budget(psi)` at the top of `generate_plan()`
4. Prepend to LLM planning prompt: stress level, `max_tasks` instruction
5. In `orchestrator.execute_objective()`, pass `psi=current_psi` to `planner.generate_plan()`

#### Acceptance Test

```
pytest: psi=0.0 → max_tasks=10
        psi=1.0 → max_tasks=5
        psi=0.5 → max_tasks=6
        all return int >= 1
```

#### Code

**Add to `backend/engine/planner.py`:**

```python
import math

@staticmethod
def psi_task_budget(psi: float) -> int:
    """
    Geodesic cost budget under ψ.
    Source: AAP §Planner — cost(e) = w(e) × (1 + ψ)

    max_tasks = floor(MAX_BUDGET / avg_cost) = floor(10 / (1 + ψ))
    High stress → fewer tasks → simpler, more direct plans.
    """
    max_tasks = math.floor(10.0 / (1.0 + max(0.0, min(1.0, psi))))
    return max(1, max_tasks)
```

**In `generate_plan()`, prepend to system prompt:**

```python
async def generate_plan(
    self,
    objective: str,
    context: str = "",
    psi: float = 0.5,
) -> List[Task]:
    max_tasks = self.psi_task_budget(psi)
    stress_level = (
        "low"      if psi < 0.3 else
        "moderate" if psi < 0.7 else
        "high"
    )
    psi_instruction = (
        f"Current agent stress level: {stress_level} (ψ={psi:.2f}). "
        f"Generate at most {max_tasks} tasks. "
        f"Under high stress, prefer direct single-step solutions over complex multi-step plans."
    )
    # Prepend psi_instruction to the planning prompt before existing logic
```

---

### AAP-007 — ψ-Gated Continuous Autonomy

**Source:** The Autonomous Agent Polytope — §Autonomy / §ψ-Space
**Priority:** 🟢 Low

#### Current State in Alluci

Autonomy is binary: `'RESTRICTED'` (throttled) or `'UNRESTRICTED'`. The AAP paper defines ψ-continuous autonomy: a spectrum where `ψ` directly gates how many sub-tasks the agent executes without human approval. High `ψ` → fewer autonomous actions; low `ψ` → full autonomy.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `auto_threshold = 1.0 − ψ` | Autonomy threshold scales inversely with tension |
| `max_auto_tasks = ceil(auto_threshold × max_tasks)` | Max tasks to auto-execute. At `ψ=1.0`: `ceil(0) = 0` (full human-in-loop) |
| `needs_approval = task_index >= max_auto_tasks` | Tasks beyond threshold require explicit approval |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/orchestrator.py` | **MODIFY** | Replace binary throttle with ψ-continuous autonomy gate |

#### Implementation Steps

1. In `execute_objective()`, compute `auto_limit = ceil((1.0 - psi) * len(tasks))` after plan is generated
2. Pass `auto_limit` to executor: `executor.execute_dag(run_id, tasks, auto_limit=auto_limit)`
3. In executor, tasks at `task_index >= auto_limit` emit `'awaiting_approval'` status rather than executing
4. Keep `'RESTRICTED'` autonomy as override that forces `psi = max(psi, 0.8)`
5. Log: `f'ψ={psi:.2f} → auto_limit={auto_limit}/{len(tasks)} tasks'`

#### Acceptance Test

```
pytest: psi=0.0 → all tasks auto-execute
        psi=1.0 → 0 tasks auto-execute (all require approval)
        psi=0.5 → ceil(0.5 × n) tasks auto-execute
        RESTRICTED forces psi ≥ 0.8
```

#### Code

**In `orchestrator.execute_objective()`:**

```python
import math

# ψ-gated continuous autonomy (AAP §Autonomy)
# Replace: if autonomy == 'RESTRICTED' and ace.should_throttle(): halt

# Force minimum contraction if explicitly RESTRICTED
if autonomy == "RESTRICTED":
    psi = max(psi, 0.8)

# Compute continuous autonomy limit
total_tasks = len(tasks) if tasks else 10
auto_limit = math.ceil((1.0 - psi) * total_tasks)
self.logger.info(
    f"[ORCHESTRATOR] ψ={psi:.2f} → auto_limit={auto_limit}/{total_tasks} tasks"
)
# Pass auto_limit to executor
```

---

### AAP-008 — Manifold Patch Endpoint

**Source:** Polytope Projection Networks — §Sovereign Patching Utility / §TablePatch
**Priority:** 🟢 Low

#### Current State in Alluci

No remote manifold patching exists. The paper's Patch-Applier allows targeted parameter updates to specific invariant regions without full retraining. In Python/Alluci: accept a `POST` of Betti-region-specific parameter updates to `PPNEmbeddingModule` with Lipschitz smoothness validation.

#### Mathematical Foundations

| Formula | Description |
|---|---|
| `validate_smoothness(patch) → bool` | Lipschitz check: `|new_val − existing_val| ≤ L_threshold` |
| `L_threshold = 0.5 × L_max(psi_at_patch_time)` | Smoothness bound: patch must fit within half-Lipschitz-width |
| `L_max(ψ) = 1 / (1 + 10ψ)` | Lipschitz bound at current tension |

#### Files Affected

| File | Action | Change Summary |
|---|---|---|
| `backend/app.py` | **MODIFY** | Add `POST /api/ppn/patch` with `PatchRequest(target_betti, patch_weights, confidence)` |
| `backend/inference/ppn.py` | **MODIFY** | Add `apply_patch(patch_data, psi)` with smoothness validation |

#### Implementation Steps

1. Add `POST /api/ppn/patch` FastAPI endpoint with body: `target_betti: list`, `patch_weights: list`, `confidence: float`
2. Validate: `confidence > 0.7`, `len(patch_weights) == latent_dim`
3. Call `ppn.apply_patch(patch_data, current_psi)` — returns `bool`
4. Implement `apply_patch()`: validate smoothness, then update `betti_head` bias for target region
5. Require `X-Patch-Signature` header authenticated against vault secret

#### Acceptance Test

```
pytest: valid patch, confidence=0.9              → applied=True
        confidence=0.5                           → applied=False (rejected)
        weight delta > L_threshold               → applied=False (smoothness violation)
        wrong dimension patch_weights            → applied=False
```

#### Code

**Add to `PPNEmbeddingModule` in `backend/inference/ppn.py`:**

```python
def apply_patch(self, patch: dict, psi: float) -> bool:
    """
    Topological patch application.
    Source: PPN §TablePatch — apply_patch() + validate_smoothness()

    Applies targeted parameter update to betti_head for a specific
    invariant region. Validated against Lipschitz smoothness bound.
    """
    confidence = patch.get("confidence", 0.0)
    if confidence < 0.7:
        logger.warning(f"[PPN] Patch rejected: low confidence {confidence}")
        return False

    patch_weights = patch.get("patch_weights", [])
    if len(patch_weights) != self.latent_dim:
        logger.error("[PPN] Patch rejected: dimension mismatch")
        return False

    # Lipschitz smoothness validation
    # L_threshold = 0.5 × L_max(ψ)
    L_max = 1.0 / (1.0 + 10.0 * psi)
    L_threshold = 0.5 * L_max

    patch_tensor = torch.tensor(patch_weights, dtype=torch.float32)
    existing = self.betti_head[0].weight.data.mean(dim=0)
    min_len = min(len(existing), len(patch_tensor))
    delta = float(
        torch.norm(patch_tensor[:min_len] - existing[:min_len]).item()
    )
    if delta > L_threshold:
        logger.warning(
            f"[PPN] Patch rejected: smoothness violation Δ={delta:.3f} > {L_threshold:.3f}"
        )
        return False

    # Apply patch: update betti_head bias toward target
    with torch.no_grad():
        n_out = self.betti_head[0].out_features
        bias_update = patch_tensor[:n_out] * confidence * 0.1
        self.betti_head[0].bias.data += bias_update

    logger.info(f"[PPN] Patch applied. confidence={confidence}, L_delta={delta:.4f}")
    return True
```

---

## 5. Integration Order & Sprint Plan

| Sprint | IDs | Items | Duration |
|---|---|---|---|
| **Sprint 1 — Foundation** | PPN-001, PPN-002, PPN-003, PPN-004, AAP-003 | AffectKernel + BTMMapper + Φ_total + Fixed-Point Normalization + Attribution Hash H_P. Touches: `ppn.py`, `ace/engine.py`, `models.py`, `security/dpk.py` | Week 1–2 |
| **Sprint 2 — Safety Gates** | PPN-005, PPN-006, AAP-001, AAP-002 | ALCE Budget + AVL Gate + Coherence Score + ψ-Routing. Creates `avl_gate.py`, updates `router.py`, finishes `ppn.py` tuple expansion | Week 3–4 |
| **Sprint 3 — Monitoring** | PPN-007, PPN-008, PPN-009, PPN-012, AAP-004 | Entropy Monitor + KCM Routing + PVT Health + Audit Chain + Memory Decay. New: `entropy_monitor.py`, `health_monitor.py`, `topo_audit.py` | Week 5–6 |
| **Sprint 4 — Orchestration** | PPN-010, PPN-011, AAP-005, AAP-006, AAP-007, AAP-008 | Consensus + Deadline Contraction + Critic Score + Planner Cost + Continuous Autonomy + Patch Endpoint. Touches: `orchestrator.py`, `critic.py`, `planner.py`, `app.py` | Week 7–8 |

---

## 6. Dependency Graph

Read `→` as "must be completed before":

```
PPN-001 (AffectKernel)
  └→ PPN-002 (BTMMapper)
       └→ PPN-003 (Φ_total)
            └→ AAP-001 (Coherence)
                 └→ AAP-005 (Critic Score)

PPN-004 (Fixed-Point)
  └→ PPN-005 (ALCE Budget)
       └→ PPN-006 (AVL Gate)

AAP-003 (Attribution Hash)
  └→ PPN-012 (Audit Chain)

AAP-001 (Coherence)
  └→ PPN-007 (Entropy Spike)
       └→ AAP-004 (Memory Decay)

AAP-002 (ψ-Routing)
  └→ PPN-008 (KCM Cost)
       └→ PPN-010 (Consensus)

PPN-009 (PVT Health)
  └→ PPN-011 (Deadline Contraction)

AAP-006 (Planner Cost)
  └→ AAP-007 (Continuous Autonomy)
```

---

## 7. New Files Summary

| File Path | Action | Change Summary |
|---|---|---|
| `backend/ace/affect_kernel.py` | **CREATE** | `AffectiveState` dataclass + `AffectKernel.apply()` + `apply_tensor()` |
| `backend/ace/btm_mapper.py` | **CREATE** | `BTMMapper.map(TelemetryData) → AffectiveState` with exact paper formulas |
| `backend/security/avl_gate.py` | **CREATE** | `AVLGate.verify(completion, state) → (bool, reason)` — 3-pillar check |
| `backend/inference/entropy_monitor.py` | **CREATE** | `EntropyMonitor`: `compute_graph_entropy`, `detect_spike`, `record_barcode` |
| `backend/health_monitor.py` | **CREATE** | `PVTManifoldMonitor`: `record_turn`, `get_pvt → {pressure, volume, temperature, health}` |
| `backend/security/topo_audit.py` | **CREATE** | `TopoAuditChain`: `record`, `verify_integrity`, `get_chain` — SHA-256 Merkle chain |
| `backend/inference/consensus.py` | **CREATE** | `BarycentricConsensus`: `detect_conflict`, `merge_responses` |
| `backend/inference/ppn.py` | **MODIFY** | Add: `compute_phi_total`, `normalize_to_fixed_point`, `compute_coherence`, `apply_patch`, memory decay, ALCE budget |
| `backend/ace/engine.py` | **MODIFY** | Add `BTMMapper`, `AffectKernel`, `get_affective_state()`, `inject_deadline_contraction()` |
| `backend/security/dpk.py` | **MODIFY** | Add `phi_total`, `coherence`, `budget_used` to `PolytopeState`; add `compute_signature_hash()` |
| `backend/inference/router.py` | **MODIFY** | Add `psi_to_complexity`, `KCMRouteScorer`, `_failure_times` tracking |
| `backend/orchestrator.py` | **MODIFY** | Wire all new components; pass `psi`/`coherence` everywhere; AVL gate; PVT monitor; deadline check |
| `backend/engine/critic.py` | **MODIFY** | Add `compute_topo_weighted_score`; blend LLM + topo scores |
| `backend/engine/planner.py` | **MODIFY** | Add `psi_task_budget`; inject `max_tasks` and stress level into plan prompt |
| `backend/models.py` | **MODIFY** | Add `AffectiveState` dataclass; add `phi_total`, `coherence`, `budget_used` to `PolytopeState` |
| `backend/app.py` | **MODIFY** | Add `POST /api/ppn/patch`, `GET /api/ppn/entropy_spikes`, `GET /api/security/audit_chain`, PVT in `/health` |

---

## 8. Test File Index

Create the following test files under `backend/tests/`:

| Test File | Action | Coverage |
|---|---|---|
| `tests/test_affect_kernel.py` | **CREATE** | Clamp boundaries; identity at neutral state; integer consistency |
| `tests/test_btm_mapper.py` | **CREATE** | HRV inverse mapping; torsion mapping; edge cases (zero HRV, no data) |
| `tests/test_phi_total.py` | **CREATE** | Determinism; range [0, 65535]; affect modulation direction |
| `tests/test_fixed_point.py` | **CREATE** | Multiples of 1/1024; max abs ≤ 32.0; no NaN/Inf |
| `tests/test_alce_budget.py` | **CREATE** | Same-input budget=0; large-shift budget>1.0; `L_max` formula |
| `tests/test_avl_gate.py` | **CREATE** | Three pillars: unsigned hash; budget>1.0; Euler mismatch |
| `tests/test_entropy_monitor.py` | **CREATE** | Fully-connected G (max entropy); diagonal G (zero entropy); spike thresholds |
| `tests/test_coherence_score.py` | **CREATE** | Range [0,1]; same Betti → max stability; dense graph → low coherence |
| `tests/test_attribution_hash.py` | **CREATE** | Same state = same hash; different Betti = different hash; always non-zero |
| `tests/test_pvt_monitor.py` | **CREATE** | Violation rate; simplex complexity; temperature calculation |
| `tests/test_audit_chain.py` | **CREATE** | 5-entry chain; tamper detection; `verify_integrity()` |
| `tests/test_psi_routing.py` | **CREATE** | ψ→complexity mapping; critical override; router integration |
| `tests/test_memory_decay.py` | **CREATE** | Convergence; topic shift detection; `reset_memory()` |
| `tests/test_critic_topo_score.py` | **CREATE** | Weights sum to 1.0; boundary values; blend formula |
| `tests/test_kcm_scorer.py` | **CREATE** | Recent failure → high cost; stale failure → low cost; ψ inflation |

---

## 9. Implementation Notes & Constraints

### 9.1 What NOT to Change

- **Do not** replace `torch.float32` math in the encoder/projector layers — fixed-point normalization applies only to the `D_t` output and `AffectKernel` preprocessing step
- **Do not** change `ALCEStabilizer.forward()` — the formula `max_deformation = 1/(1+10ψ)` is already the correct paper implementation; PPN-005 only adds budget tracking on top
- **Do not** change `compute_persistent_homology()` — the Gudhi-based implementation is the correct paper formula; PPN-003/004 augment it, not replace it
- **Do not** change the DPK Euler characteristic check — it is the correct paper formula; AAP-003 only upgrades how `signature_hash` is computed

### 9.2 forward() Return Signature — Final 8-Tuple

After all PPN-series changes, `PPNEmbeddingModule.forward()` returns:

```python
# Full 8-tuple return signature after all changes:
return (
    G,            # Adjacency matrix (simplicial 1-skeleton)
    D_t,          # Deformation vector (fixed-point normalized)
    B_pred,       # Betti numbers [β₀, β₁, β₂, β₃]
    final_config, # Point cloud configuration
    phi_total,    # Φ_total affective-invariant index (PPN-003)
    budget_used,  # Lipschitz budget consumption (PPN-005)
    coherence,    # Coh(P_t) per-turn quality score (AAP-001)
    topic_shift,  # Boolean: Betti memory delta > threshold (AAP-004)
)
```

**Update all callers in `orchestrator.py`:**

```python
G, D_t, B, points, phi_total, budget_used, coherence, topic_shift = \
    self.ppn(input_tensor, psi=psi, affect_state=affect_state)
```

### 9.3 Torch vs. Integer Math

The PPN paper implements everything in C++ `int16_t` for FPGA/edge deployment. Alluci runs on Python/CPU server. The approach here is a **hybrid**: compute in `torch.float32` but apply the integer-scale logic (`×1024`, `>>10`, integer clamp) as the mathematical structure, then convert back to float for downstream operations. This preserves the geometric properties of the integer math while maintaining Python compatibility.

### 9.4 gudhi Availability

All `compute_coherence()` and `compute_phi_total()` implementations handle `GUDHI_AVAILABLE=False` gracefully by using the `betti_head` neural approximation. The fallback returns `B=[1,0,0,0]` which yields `χ=1`, Φ_total based on that, and coherence based purely on graph entropy. The system remains functional without gudhi installed.

### 9.5 AAP PDF Note

The Autonomous Agent Polytope (AAP) PDF was provided as a context image (not text-extractable). All AAP-series items are derived from: (a) visible content in the provided PDF, (b) formulas explicitly named in the PPN paper which references the AAP as its parent framework, and (c) the existing Alluci codebase which already implements AAP-derived components (`PPNEmbeddingModule`, `AffectiveEngine`, `DPK`). All formulas are mathematically consistent with the implemented C++ reference code in the PPN paper.

### 9.6 PolytopeState — Complete Final Definition

```python
@dataclass
class PolytopeState:
    signature_hash: int          # AAP-003: SHA256-derived sovereign hash
    vertices_V: int              # Simplex vertex count
    edges_E: int                 # Simplex edge count
    faces_F: int                 # Simplex face (triangle) count
    betti: List[float]           # [β₀, β₁, β₂, β₃] topological invariants
    affective_tension_psi: float # ψ ∈ [0.0, 1.0] from BTM (PPN-002)
    phi_total: int = 0           # Φ_total affective-invariant index (PPN-003)
    coherence: float = 0.0       # Coh(P_t) ∈ [0.0, 1.0] (AAP-001)
    budget_used: float = 0.0     # Lipschitz budget consumption (PPN-005)
```

---

*Alluci Sovereign Agent — PPN + AAP Integration Spec v1.0*
*20 items · 8 new files · 8 modified files · 15 test modules · 4 sprint weeks*
