# Alluci Sovereign Agent Architecture

This document defines the immutable architectural foundation and system laws governing the Alluci Sovereign Agent application, backend runtime, security protocols, and memory substrate.

---

## 🏛️ Core Architectural Foundations (The 6 Functional Capability Domains)

System design, introspective grounding, and code execution across Alluci are strictly anchored by six dynamic capability domains (`get_system_capabilities()` in `backend/engine/codebase_grounding.py`):

1. **Core Compute & Apple MLX Local Inference:** Native Apple Silicon execution via official MLX frameworks (`mlx_lm`, `mlx_vlm`), **Native Speculative Decoding** (2B Edge draft $\to$ 31B Dense verification), and **Streaming Attention Sinks** (>16k chars) maintaining persistent token 0 system anchoring.
2. **Topological Physics & Mathematical Substrate:** Foundational Topological State Spaces ($W$ continuous world data, $X$ simplicial complexes via Vietoris-Rips filtration `pmet_filtration.py`, $\mathcal{J}$-Space counterfactual sandbox with Simplicial Chain-of-Thought boundary nilpotence $\partial_1 \circ \partial_2 = 0$ in `j_space_simulator.py`, $G$ action affordance convex hull `affordance_envelope.py`, and $N$ central discrete pacing in `barcode_clock.py`), Discrete Projection Kernel grounded in Kepler's Stella Octangula $S_8$ ($\partial_1 \circ \partial_2 = 0$, $F_n^1: \Pi \circ \Pi = \Pi$), and Frenet-Serret trajectory curvature safe-halt ($\kappa \le 5.0$, $T \le 0.8$).
3. **4-Tier Simplicial H-LSM Memory & Tri-Hybrid RRF:** Hierarchical Long-Short Manifold memory architecture (L0 Working, L1 Episodic FTS5, L2 Semantic MiniLM vectors, L3 KùzuDB Knowledge Graph) aggregated in parallel via **Tri-Hybrid Reciprocal Rank Fusion** ($k=60$) and Markov Trace hidden excursion boosting (`hlsm_manager.py`, `markov_trace.py`).
4. **Autonomous Sub-Agents & Deep Research:** Multi-agent constellation (Executive Orchestrator, Codi OpenCode Harness, Rocco Deep Research Harvester with multi-query parallel vector decomposition and 24h SQLite `ResearchDossierCache`, SPE, SWD, SUF, OC, PMET).
5. **Zero-Trust Security & Sovereign Identity:** Self-sovereign identity (`VerusID`), Ed25519 manifest signing (`verus.py`, `verusid_auth.py`), AES-256-GCM Vault Manager (`vault.py`), AVL Gate GJK boundary refinement, Protocol 3 Lipschitz saturation, and HITL Executive Governance (`SecurityInterventionModal.tsx`).
6. **Omni-Channel Bridges & Hardware Integration:** 20+ cryptographically isolated communication bridges (Telegram, Nostr, Signal, iMessage, WhatsApp, Discord, Slack, Instagram, Facebook, WeCom, Email) coupled with live Apple Watch biometrics (ACE HRV, respiratory sync, stress scores).

---

## 1. Core Inference & Compute (Local Cognitive Engine - LCE)

- **The LCE Law (Local Compute Engine):** On macOS / Apple Silicon environments, the LCE relies strictly on official Python Apple MLX frameworks (`mlx_lm` and `mlx_vlm`) in `backend/inference/mlx_engine.py` for on-device inference to maximize Unified Memory efficiency. Custom out-of-tree C++ runners for model evaluation are forbidden on Apple Silicon to prevent Metal GPU command buffer panics and VRAM leaks. On Windows, Linux, and NVIDIA CUDA environments, cross-platform inference backends (`llama.cpp` bindings or CUDA PyTorch/vLLM adapters) are supported via `local_bridge.py`.
- **5-Tier System Hardware Profiling Matrix:** Upon initialization, `HardwareProfiler.get_system_profile()` (`profiler.py`) dynamically profiles host System RAM, VRAM, and GPU architecture, mapping the machine to HuggingFace models ([`https://huggingface.co/Alluci`](https://huggingface.co/Alluci)):
  - **`TIER_0_ULTRA` ($\ge 128\text{ GB} - 512\text{ GB}$ Unified RAM / $\ge 96\text{ GB}$ Code Threshold):** Flagship Workstations & Server Nodes running unquantized 31B 16-bit (`BF16`) dense models (accelerated via 2B speculative draft).
  - **`TIER_1_MAX` ($64\text{ GB} - 96\text{ GB}$ Unified RAM / $\ge 60\text{ GB}$ Code Threshold):** Studio Workstations running high-density 31B 8-bit / 4-bit models.
  - **`TIER_2_PRO` ($32\text{ GB} - 48\text{ GB}$ Unified RAM / $\ge 30\text{ GB}$ Code Threshold):** Pro Laptops running 26B Mixture-of-Experts (MoE) 4-bit models.
  - **`TIER_3_BASE` ($16\text{ GB} - 24\text{ GB}$ Unified RAM / $\ge 15\text{ GB}$ Code Threshold):** Consumer MacBooks & PCs running 12B 4-bit dense models.
  - **`TIER_4_EDGE` ($8\text{ GB} - 12\text{ GB}$ Unified RAM / $< 15\text{ GB}$ Code Threshold):** Mobile Sentinels (iPhone 17 / Base Macs) running lightweight 2B 4-bit models.
- **Native Apple MLX Speculative Decoding (2B ➔ 31B):**
  - Pairs the lightweight edge model (`alluci-polytope-gemma-4-e2b-it-4bit`) as an asynchronous candidate token speculator with the dense verifier model (`alluci-polytope-gemma-4-31b-it-bf16`).
  - Evaluates candidate tokens natively through `mlx_lm.stream_generate(..., draft_model=draft_engine)`, achieving 2.5x–4x faster local inference speeds with zero loss in output mathematical precision.
  - Built-in circuit breaker: automatically falls back to single-model execution if draft model memory limits are reached.
- **Streaming Attention Sinks (>16k Context Management):**
  - When conversational contexts exceed 16,000 characters (>4,000 tokens), `_apply_streaming_attention_sink()` permanently pins initial system directives, grounding laws, and security bounds at token 0 (sink size: 2,000 chars) while sliding the active conversational tail (14,000 chars).
  - Intermediate turns are evicted into H-LSM L1 episodic memory, enabling **infinite multi-turn sessions** without Metal GPU command buffer panics.
- **Local Voice & Conversational Speech Engine (`PPN-030`):** `AlluciVoiceOrchestrator` (`backend/inference/voice_orchestrator.py`) handles real-time speech processing:
  - Ingests streaming 200ms PCM audio fragments over WebSocket RPC (`/ws/voice`).
  - Uses native Apple OS `AVSpeechSynthesizer` (Siri Voice Engine) on Apple Watch (`WATCH_ULTRA`) and paired iPhone (`IPHONE_17_PRO`) for battery-efficient playback.
  - Uses native `kokoro_mlx` (`kokoro_bridge.py`) on Mac Workstations (`MACBOOK_WORKSTATION`) for 24kHz neural PCM voice synthesis.
  - Delegates heavy cognitive reasoning and transcription from Watch/iPhone edge sentinels to host workstations over encrypted WebSocket tunnels.
- **Zero-Restart LoRA Context Moat:** Dynamically hot-swaps per-agent LoRA weights (`models/loras/agent_{id}_lora.safetensors`) into the active MLX model on the fly without restarting engine processes.
- **Dynamic KV Cache Strategy & Purging:** Standard interactions use FP16 KV caching. When context exceeds 8,000 tokens or on `TIER_4_EDGE`, the LCE dynamically toggles to Q4 (4-bit) KV cache quantization. Compulsory `mx.metal.clear_cache()` and Python garbage collection calls execute before and after every generation stream.
- **Multi-Agent Concurrency:** The LCE uses Python `asyncio.Lock` and queue-based concurrency for MLX orchestration across asynchronous agent streams. C++ `std::mutex` is strictly forbidden for MLX task dispatching.

---

## 2. Security, Integrity & Human-in-the-Loop Safeguards

- **Human-in-the-Loop (HITL) Executive Approval Gate:** All critical action tasks—including destructive memory purges, schema modifications, system file overwrites, financial transactions, and configuration changes—MUST be intercepted before execution and gated by explicit sovereign HITL authorization. The agent is STRICTLY FORBIDDEN from autonomously deleting memories or generating simulated deletion confirmations.
- **Three-Tier Hard Security Interceptors (`backend/routers/gemini.py`):**
  1. *Guard 1 (Code Context Bypass):* Bypasses memory wipe logic if technical programming terms (`clear_cache`, `mx.metal`, `code`, `script`, `app`, `css`) are detected in developer contexts.
  2. *Guard 2 (Intent & Critical Task Matcher):* Matches explicit deletion/modification intents across critical action tasks and extracts targeted parameters (E.164 phone numbers, SMS short codes, database keys).
  3. *Guard 3 (Short Pattern & Stop-Word Defense):* Blocks search patterns shorter than 3 characters or matching common stop-words (`"a"`, `"the"`, `"for"`).
- **Security Resolution Protocol (`backend/routers/security.py` & `SecurityInterventionModal.tsx`):**
  - Broadcasts `security.resolution_required` WebSocket events to render the primary **`[ Approve & Execute Action ]`** and **`[ Cancel Task ]`** modal UI.
  - Upon approval, executes multi-tier deletion/action via `hlsm_manager.delete_by_pattern`, broadcasts completion cards, and emits `memory.deleted` WebSocket events for real-time UI state auto-syncing.
- **Sovereign Topological State Spaces $(W, X, G, N)$ & $\mathcal{J}$-Space World Model Engine (`backend/topology/`):**
  - *State Space Tuple $(W, X, \mathcal{J}, G, N)$:*
    1. **$W$ (World Data Space):** Continuous raw multi-modal telemetry, environmental vectors, and unstructured document graphs.
    2. **$X$ (Experience Simplicial Space):** Bounded simplicial complexes and topological Betti invariants ($\beta_0, \beta_1, \beta_2, \beta_3$) constructed via Vietoris-Rips filtration at scale $\epsilon$ (**Perceive Operator** $P: W \times X \to [0,1]$ via `PMETFiltrationEngine`).
    3. **$\mathcal{J}$ ($\mathcal{J}$-Space Counterfactual Sandbox):** Air-gapped mental simulation sandbox (**Simulate Operator** $S: X \times G \times \mathcal{J} \to \mathcal{J}$ via `JSpaceSimulator`). Enforces **Simplicial Chain-of-Thought (S-CoT)** algebraic boundary nilpotence ($\partial_1 \circ \partial_2 = 0$) on reasoning triads and **Kepler $S_8$ Dual-Tetrahedron Socratic Dialectics** reconciling Constructive Proposer ($T_+$) and Adversarial Skeptic ($T_-$) hypotheses into the central intersection kernel ($O_6$).
    4. **$G$ (Action Affordance Envelope):** Convex hull boundary defining permissible action vectors evaluated across a 3D spatial risk coordinate simplex (**Decide Operator** $D: \mathcal{J} \times G \to [0,1]$ via `ActionAffordanceEnvelope`). Enforces sub-agent privilege bounds (Codi, Rocco, Admin) and bio-affective tension thresholds ($\psi \le 0.85$).
    5. **$N$ (Discrete Barcode Clock Count):** Monotonic discrete clock count tracking topological feature births ($b$), deaths ($d$), and persistence intervals across cycles via `TopologicalBarcodeClock` ($N \to N+1$).
- **Topological Heartbeat Daemon & Loop Gating (`backend/heartbeat.py`):**
  - Paced on every tick by `barcode_clock.tick()` ($N \to N+1$).
  - *Sub-Agent Loop Detection Probe (`_probe_subagent_loop`):* Inspects active Betti invariants on the Barcode Clock; if a 1-dimensional topological hole is detected ($\beta_1 > 0$), flags a reasoning loop failure and triggers self-healing.
  - *Topological Drift Probe (`_probe_topological_drift`):* Evaluates consecutive AVL Gate Lipschitz budget saturation strikes; escalates to HITL when strikes breach configured thresholds.
  - *Homeostatic Bio-Affective Relaxation:* Gradually relaxes affective tension ($\psi$) towards baseline on stable ticks.
  - *Quiet-Hours Offline Dreaming:* Runs offline counterfactual perturbation rollouts in `JSpaceSimulator` during quiet hours ($22:00–07:00$), persisting verified recovery triplets to `DPOTripletHarvester`.
- **PVT Manifold Health Monitor (`PVTManifoldHealthMonitor` / `health_monitor.py` & `trajectory.py`):** Continuously models the cognitive state space using a thermodynamic triple ($P, V, T$) and Frenet-Serret state trajectory kinematics:
  - *Pressure ($P$):* Constraint density vs. admissible volume ratio ($P = \frac{\text{Active Constraints}}{4.0 \cdot V_{\text{agency}} + \epsilon}$).
  - *Volume ($V$):* Admissible polytope hyper-volume ($V = (1 - \text{Budget}_{\text{used}}) \cdot \text{Coherence}$).
  - *Temperature ($T$):* Entropy spike, Betti stability, and Frenet-Serret trajectory curvature metric ($T = \Delta \beta_{\text{norm}} + D_{\text{KL}}(P_t \parallel P_{t-1}) + 0.3 \cdot \kappa_{\text{norm}}$).
  - *Polytope Trajectory Continuity Tracker (`trajectory.py`):* Evaluates geodesic velocity $v(t) = \gamma(t) - \gamma(t-1)$, acceleration $a(t) = \gamma(t) - 2\gamma(t-1) + \gamma(t-2)$, and Frenet-Serret curvature $\kappa(t) = \frac{\sqrt{\|v\|^2 \|a\|^2 - (v \cdot a)^2}}{\|v\|^3 + \epsilon}$.
  - *Safe-Halt Protocol:* When Temperature breaches the critical threshold ($T > 0.8$) or curvature snaps ($\kappa > 5.0$), PVT flags a `CRITICAL` rupture and the `ExecutiveOrchestrator` triggers an emergency safe-halt ($g=0$).
- **DPK & Stella Octangula $S_8$ Simplicial Complex (`dpk.py`, `stella_octangula.py`, `dpk_kernel.cpp`):**
  - Evaluates sub-microsecond state transition vectors ($\mathbf{x}_{t-1} \to \mathbf{x}_t$) grounded in Kepler's Stella Octangula compound of dual regular tetrahedra $T_+ \cup T_-$ (8 vertices, 12 edges, 8 faces, central octahedron $O_6$).
  - *Simplicial Boundary Nilpotence:* Computes boundary matrices $B_1 \in \mathbb{R}^{8 \times 12}$ ($\partial_1$) and $B_2 \in \mathbb{R}^{12 \times 8}$ ($\partial_2$), verifying the Fundamental Theorem of Algebraic Topology ($\partial_1 \circ \partial_2 = 0$, exact nilpotence $B_1 B_2 = 0$).
  - *Idempotent Fusion Operator ($F_n^1$):* Enforces idempotent simplex projection $\Pi(\Pi(x)) = \Pi(x)$ and entropic arrow of time monotonicity ($H(X_n \mid X_1) \ge H(X_{n-1} \mid X_1) - \epsilon$).
  - Raises `TearingException` if topological shift breaches dynamic calibrated thresholds ($\Delta \text{Shift} > \theta_{\text{dynamic}}$).
- **AVL Gate (Action Verification Loop / `avl_gate.py`):** Three-pillar zero-trust safety firewall for LLM generation outputs:
  1. *Sovereign Attribution Verification:* Checks signature hashes ($\text{Hash}_{64} \neq 0$).
  2. *ALCE Gradient Smoothness Verification:* Enforces Lipschitz continuity budget limits ($\text{Budget}_{\text{used}} \leq \text{Budget}_{\text{dynamic}}$). If breached across 3 successive iterations (Protocol 3), forces a hard exit to `HUMAN-IN-THE-LOOP REQUIRED` mode.
  3. *Topological Continuity Verification:* Validates Euler characteristic consistency ($|\chi - \beta_{\chi}| \leq \text{Euler}_{\text{tolerance}}$).
  4. *GJK Action & Tool Payload Refinement:* Projects out-of-bounds LLM generations back onto admissible Lipschitz boundaries via Gilbert-Johnson-Keerthi convex polytope distance algorithms (`project_to_boundary`) and clamps structured tool action parameters (`top_k`, `limit`, `timeout`, `depth`, `steps`, `count`, `max_tokens`) dynamically.
- **Sovereign Biometric Kill Switch Daemon (`BioTelemetryAuth` / `PPN-017`):** Monitors biological telemetry natively from Apple Watch and wearable webhooks (Garmin, Whoop, Oura). Validates on-wrist presence (`is_on_wrist=True`) and heart rate pulse before executing sensitive operations (`banking`, `db_write`, `file_overwrite`, `os_exec`, `crypto_tx`). When `REQUIRE_WATCH_TELEMETRY=True`, missing telemetry instantly aborts execution and encrypts active working memory.
- **Multi-Modal Anti-Spoofing & Deepfake Defense (`PPN-018`):** Analyzes incoming voice streams for acoustic micro-hesitations (jitter, tremor, breath pauses) and cross-references them against live Apple Watch respiratory telemetry to verify human liveness.

---

## 3. Hierarchical Long-Short Manifold (H-LSM) Memory Architecture

The H-LSM memory architecture operates across 4 cognitive storage tiers managed by `HLSMManager` (`backend/memory/hlsm_manager.py`) augmented by the **Markov Trace & Spectral Geometry Engine** (`backend/memory/markov_trace.py`) and paced monotonically by the **Topological Barcode Clock** (`backend/topology/barcode_clock.py`):

- **L0 Working Memory:** Ultra-fast session context (expiring working memory) backed by Redis (Key-Value) with automatic zero-config fallback to SQLite table `hlsm_working`.
- **L1 Episodic Memory:** Chat turn interactions, episodic events, and full conversation history backed by SQLite table `hlsm_episodic` with SQLite FTS5 full-text search index (`hlsm_episodic_fts`).
- **L2 Semantic Memory:** Long-term vector embeddings for RAG and semantic retrieval, backed by Sentence-Transformers (`all-MiniLM-L6-v2`) and KùzuDB graph nodes (`polytope_data.kuzu`). Distilled chat turns are ingested via `ingest_distilled_intent` into L2 semantic nodes (`mem_intent_*`).
- **L3 Knowledge Graph:** Permanent structured entity-relationship graph nodes backed by the KùzuDB embedded graph engine (`polytope_data.kuzu`).
- **Tri-Hybrid Reciprocal Rank Fusion (RRF $k=60$):**
  - Executes parallel asynchronous retrieval across L1 SQLite FTS5 (weight $w=1.0$), L2 MiniLM Dense Vectors ($w=1.2$), and L3 KùzuDB Relational Entities ($w=1.4$).
  - Merges disparate score distributions into an authoritative unified ranking:
    $$\text{Score}_{\text{RRF}}(d) = \sum_{t \in \{\text{L1}, \text{L2}, \text{L3}\}} \frac{w_t}{60 + \text{rank}_t(d)}$$
  - Dispatches distilled knowledge graph entities directly into prompt grounding contexts under structured entity headers (`── Knowledge Graph Entities ──`).
- **Markov Trace Multi-Hop Rescoring & Scale-Dependent Spectral Geometry (`markov_trace.py`):**
  - *Schur Complement Trace Operator:* Computes exact Markov Trace reductions $\text{Tr}_A(P) = A + B(I - C + \epsilon I)^{-1} D$, factoring multi-hop hidden excursion paths into visible candidate scores (80% direct relevance + 20% topological excursion boost).
  - *Symmetrized Normalized Laplacian ($L_A$):* Derives real eigenvalues $\lambda_i \ge 0$, Fiedler algebraic connectivity ($\lambda_2$), and heat return probability $P_A(\sigma) = \frac{1}{|A|} \sum e^{-\sigma \lambda_i}$.
  - *Dynamic Spectral Context Depth Scaling:* Computes scale-dependent spectral dimension $d_s^A(\sigma) = 2\sigma \frac{\sum \lambda_i e^{-\sigma \lambda_i}}{\sum e^{-\sigma \lambda_i}}$ to dynamically expand context retrieval depth (`max_per_tier`) when mixing is sparse ($d_s^A > 1.5$).
- **Absolute Path Database Resolution (`database.py` & `config.py`):** All relative database URIs (`sqlite:///polytope_data.db` and `./polytope_data.kuzu`) are automatically resolved to absolute file paths anchored directly to the project root directory.

---

## 4. Autonomy, Affective Computing & Proactivity

- **PCL (Proactive Cognition Layer / `backend/pcl.py`):** Continuous background cognitive loop operating across a 5-stage lifecycle (`OBSERVE → MODEL → DETECT → JUDGE → ACT`). Builds stateful `WorldModelSnapshot` records, evaluates opportunities (`StalledGoalDetector`, `HardwareAnomalyDetector`, `AffectiveStressDetector`), and dispatches proactive tasks or WebSocket notifications (`JsonRpcGateway`).
- **Rocco 2.0 Multi-Query Deep Research Harvester & SQLite Cache (`backend/adapters/web_search.py`):**
  - *Multi-Query Decomposition:* In `expand_and_harvest()`, breaks complex research goals into parallel orthogonal query angles, fetching results concurrently with strict 4.0-second async timeouts and URL deduplication.
  - *24-Hour TTL SQLite Cache:* Persists research results to `backend/data/research_cache.db` (`ResearchDossierCache`), delivering instant 0ms responses on repeat inquiries.
  - *Verified Grounding Links:* Formats real web citations with numbered markdown reference links.
- **DAG Planner Simplicial S-CoT Validation (`backend/engine/planner.py`):**
  - Evaluates multi-step DAG task dependencies through `_detect_cycles_and_scot_nilpotence()`.
  - Verifies that intermediate sub-agent dependencies satisfy boundary nilpotence ($\partial_1 \circ \partial_2 = 0$) and zero topological loops ($\beta_1 = 0$).
- **Nightly "Dream" Cycle Evolution & DPO Preference Harvesting (`cron_engine.py` & `backend/engine/dpo_harvester.py`):**
  - When hardware load is low, the daemon halts external polling and reallocates 100% of local resources to internal evolution.
  - *5-Stage Evolution Pipeline:* 1) Extraction (Episodic memories, PCL world model, ACE baseline, quarantine pool), 2) Offline $\mathcal{J}$-Space Counterfactual Rollouts (`j_space_simulator.py`) simulating boundary recovery, 3) Synthesis (air-gapped local 31B Dense model instruction-response pair synthesis), 4) Cognitive Distillation (distilling episodic logs into permanent Semantic Truths), and 5) Preference Harvesting.
  - *DPO Preference Harvesting:* Structures teacher-student preference triplets $(x, y_w, y_l)$ from H-LSM self-healing resolution deltas (`failed_plan` $\to$ `successful_plan`), quarantined AST anti-patterns (`reverted_code` $\to$ `repaired_code`), and offline $\mathcal{J}$-Space simulation traces with analytical softplus loss $\mathcal{L}_{\text{DPO}} = \ln(1 + \exp(-\text{margin}))$ to generate JSONL preference datasets for local LoRA fine-tuning without mutating foundation model weights.
- **ACE (Affective Computing Engine):** Python-native modules (`backend/ace/`) simulating valence, arousal, and emotional tension ($\psi = \text{tension}/1024.0$), dynamically modulating LLM sampling temperature and cognitive stress levels based on live wearable biometrics.
- **BTM (Behavioral Topological Mapper / `btm_mapper.py`):** Maps biometric histories (HRV, respiratory rate, stress score) to geometric manifold deformation and topological coherence scores ($C \in [0.1, 0.95]$).

---

## 5. Gateway, Verus DREAM & Swarm Architecture

- **Verus Sovereign Identity & DREAM Architecture (`verus.py`, `verus_rpc.py`, `verus_wallet.py`):** Implements the Verus **DREAM (Decentralized Real-time Encrypted Application Model)** paradigm:
  - *VerusID Authentication:* Uses self-sovereign identity handles (`identity@`) and Ed25519 cryptographic signing for zero-trust manifest authorization.
  - *Local Node RPC:* Connects directly to local `verusd` blockchain node RPC for sovereign wallet balance checks, multi-currency transfers (`verus_send_currency`), and decentralized market offers (`verus_make_offer`).
  - *VDXF Namespaces:* Structures application data, skill manifests, and P2P content multimaps (`VDXFStore`) using standardized Verus Data eXchange Format keys (`verus_get_vdxf_id`).
  - *On-Chain Audit Anchoring:* Anchors cryptographic state hashes ($\text{Hash}_{\text{integrity}}$) directly to the Verus blockchain (`verus_txid`), generating immutable audit trails.
- **Federated Swarm Intelligence & Digital Pheromones (`AntNetworkProtocol` / `PPN-016`):** Coordinates multi-agent constellations across distributed devices via `AntNetworkProtocol` (`Alluci_Ant_v1`). Agents broadcast zero-knowledge "Topological Barcodes" (Betti signature pheromones) over the Verus P2P network to share problem-solving paths without exposing raw prompts or private user data.
- **Unified Multi-Bridge Gateway (`backend/channels.py`, `backend/bridges/`):** Integrates Telegram, Nostr, Signal, iMessage, Apple Watch biometrics (`IWatchBridge`), WhatsApp, Discord, Slack, Instagram, Facebook, WeCom, and Email (IMAP/SMTP) inside AES-256-GCM encrypted Simplicial Vaults.
- **Real-Time WebSocket Protocol (`backend/ws_gateway.py`):** Operates streaming JSON-RPC 2.0 gateways on `/ws/admin` and `/ws/voice`, emitting real-time administrative events (`security.resolution_required`, `memory.deleted`, `manifold.pvt`) to synchronize UI components instantly.

---

**WARNING:** Any future modifications to action generation, memory management, or inference pipelines MUST strictly respect these definitions. Violating these principles will compromise sovereign constraints and manifold integrity.
