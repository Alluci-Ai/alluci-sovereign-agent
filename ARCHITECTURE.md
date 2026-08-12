# Alluci Sovereign Agent Architecture

This document defines the immutable architectural foundation and system laws governing the Alluci Sovereign Agent application, backend runtime, security protocols, and memory substrate.

---

## 🏛️ Core Architectural Foundations (The 5 Sovereign Pillars)

System design and code execution across Alluci are strictly anchored by five fundamental pillars:

1. **Sovereign Identity (`VerusID`):** Decentralized identity, zero-trust authentication, and Ed25519 cryptographic signing of executive manifests (`verus.py`, `verusid_auth.py`).
2. **HITL Executive Security Governance:** Interlocking hard security guards and interactive user approval modals (`SecurityInterventionModal.tsx`) intercepting all critical action tasks before execution (`backend/routers/gemini.py`).
3. **4-Tier Simplicial H-LSM Memory:** Hierarchical Long-Short Manifold memory architecture (L0 Working, L1 Episodic FTS5, L2 Semantic, L3 KùzuDB Knowledge Graph) preventing context bloat and state degradation (`hlsm_manager.py`).
4. **Bio-Affective Computing (ACE):** Biological attunement coupling live wearable biometrics (Apple Watch HRV, respiratory sync, stress scores) directly into manifold geometry and temperature modulation (`backend/ace/`).
5. **Policy-Driven DAG Orchestration:** Autonomous hierarchical Directed Acyclic Graph decomposition, cron scheduling, and multi-tier model routing (`orchestrator.py`, `cron_engine.py`).

---

## 1. Core Inference & Compute (Local Cognitive Engine - LCE)

- **The LCE Law (Local Compute Engine):** On macOS / Apple Silicon environments, the LCE relies strictly on official Python Apple MLX frameworks (`mlx_lm` and `mlx_vlm`) in `backend/inference/mlx_engine.py` for on-device inference to maximize Unified Memory efficiency. Custom out-of-tree C++ runners for model evaluation are forbidden on Apple Silicon to prevent Metal GPU command buffer panics and VRAM leaks. On Windows, Linux, and NVIDIA CUDA environments, cross-platform inference backends (`llama.cpp` bindings or CUDA PyTorch/vLLM adapters) are supported via `local_bridge.py`.
- **5-Tier System Hardware Profiling Matrix:** Upon initialization, `HardwareProfiler.get_system_profile()` (`profiler.py`) dynamically profiles host System RAM, VRAM, and GPU architecture, mapping the machine to HuggingFace models ([`https://huggingface.co/Alluci`](https://huggingface.co/Alluci)):
  - **`TIER_0_ULTRA` ($\ge 128\text{ GB} - 512\text{ GB}$ Unified RAM / $\ge 96\text{ GB}$ Code Threshold):** Flagship Workstations & Server Nodes running unquantized 31B 16-bit (`BF16`) dense models.
  - **`TIER_1_MAX` ($64\text{ GB} - 96\text{ GB}$ Unified RAM / $\ge 60\text{ GB}$ Code Threshold):** Studio Workstations running high-density 31B 8-bit / 4-bit models.
  - **`TIER_2_PRO` ($32\text{ GB} - 48\text{ GB}$ Unified RAM / $\ge 30\text{ GB}$ Code Threshold):** Pro Laptops running 26B Mixture-of-Experts (MoE) 4-bit models.
  - **`TIER_3_BASE` ($16\text{ GB} - 24\text{ GB}$ Unified RAM / $\ge 15\text{ GB}$ Code Threshold):** Consumer MacBooks & PCs running 12B 4-bit dense models.
  - **`TIER_4_EDGE` ($8\text{ GB} - 12\text{ GB}$ Unified RAM / $< 15\text{ GB}$ Code Threshold):** Mobile Sentinels (iPhone 17 / Base Macs) running lightweight 2B 4-bit models.
- **Local Voice & Conversational Speech Engine (`PPN-030`):** `AlluciVoiceOrchestrator` (`backend/inference/voice_orchestrator.py`) handles real-time speech processing:
  - Ingests streaming 200ms PCM audio fragments over WebSocket RPC (`/ws/voice`).
  - Uses native Apple OS `AVSpeechSynthesizer` (Siri Voice Engine) on Apple Watch (`WATCH_ULTRA`) and paired iPhone (`IPHONE_17_PRO`) for battery-efficient playback.
  - Uses native `kokoro_mlx` (`kokoro_bridge.py`) on Mac Workstations (`MACBOOK_WORKSTATION`) for 24kHz neural PCM voice synthesis.
  - Delegates heavy cognitive reasoning and transcription from Watch/iPhone edge sentinels to host workstations over encrypted WebSocket tunnels.
- **Zero-Restart LoRA Context Moat:** Dynamically hot-swaps per-agent LoRA weights (`models/loras/agent_{id}_lora.safetensors`) into the active MLX model on the fly without restarting engine processes.
- **Speculative Token Drafting & Acceleration:** Pairs a fast, lightweight speculator model (`EDGE_2B_4BIT`) with a dense verifier model (`DENSE_31B_BF16`), achieving 2–3x faster local inference through parallel sequence validation.
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
- **PVT Manifold Health Monitor (`PVTManifoldHealthMonitor` / `health_monitor.py`):** Continuously models the cognitive state space using a thermodynamic triple ($P, V, T$):
  - *Pressure ($P$):* Constraint density vs. admissible volume ratio ($P = \frac{\text{Active Constraints}}{4.0 \cdot V_{\text{agency}} + \epsilon}$).
  - *Volume ($V$):* Admissible polytope hyper-volume ($V = (1 - \text{Budget}_{\text{used}}) \cdot \text{Coherence}$).
  - *Temperature ($T$):* Entropy spike & Betti stability metric ($T = \Delta \beta_{\text{norm}} + D_{\text{KL}}(P_t \parallel P_{t-1})$).
  - *Safe-Halt Protocol:* When Temperature breaches the critical threshold ($T > 0.8$), PVT flags a `CRITICAL` rupture and the `ExecutiveOrchestrator` triggers an emergency safe-halt ($g=0$).
- **DPK (Discrete Projection Kernel / `dpk.py`):** Evaluates sub-microsecond state transition vectors ($\mathbf{x}_{t-1} \to \mathbf{x}_t$) using integer simplicial boundary operators ($\partial_k$) and Euler characteristic invariants ($\chi = V - E + F$). Raises `TearingException` if topological shift breaches dynamic calibrated thresholds ($\Delta \text{Shift} > \theta_{\text{dynamic}}$).
- **AVL Gate (Action Verification Loop / `avl_gate.py`):** Three-pillar zero-trust safety firewall for LLM generation outputs:
  1. *Sovereign Attribution Verification:* Checks signature hashes ($\text{Hash}_{64} \neq 0$).
  2. *ALCE Gradient Smoothness Verification:* Enforces Lipschitz continuity budget limits ($\text{Budget}_{\text{used}} \leq \text{Budget}_{\text{dynamic}}$). If breached across 3 iterations, forces a hard exit to `HUMAN-IN-THE-LOOP REQUIRED` mode.
  3. *Topological Continuity Verification:* Validates Euler characteristic consistency ($|\chi - \beta_{\chi}| \leq \text{Euler}_{\text{tolerance}}$).
  4. *GJK Action Refinement:* Projects near-boundary prompt violations back into admissible Lipschitz bounds via Gilbert-Johnson-Keerthi convex polytope distance algorithms (`project_to_boundary`).
- **Sovereign Biometric Kill Switch Daemon (`BioTelemetryAuth` / `PPN-017`):** Monitors biological telemetry natively from Apple Watch and wearable webhooks (Garmin, Whoop, Oura). Validates on-wrist presence (`is_on_wrist=True`) and heart rate pulse before executing sensitive operations (`banking`, `db_write`, `file_overwrite`, `os_exec`, `crypto_tx`). When `REQUIRE_WATCH_TELEMETRY=True`, missing telemetry instantly aborts execution and encrypts active working memory.
- **Multi-Modal Anti-Spoofing & Deepfake Defense (`PPN-018`):** Analyzes incoming voice streams for acoustic micro-hesitations (jitter, tremor, breath pauses) and cross-references them against live Apple Watch respiratory telemetry to verify human liveness.

---

## 3. Hierarchical Long-Short Manifold (H-LSM) Memory Architecture

The H-LSM memory architecture operates across 4 cognitive storage tiers managed by `HLSMManager` (`backend/memory/hlsm_manager.py`):

- **L0 Working Memory:** Ultra-fast session context (expiring working memory) backed by Redis (Key-Value) with automatic zero-config fallback to SQLite table `hlsm_working`.
- **L1 Episodic Memory:** Chat turn interactions, episodic events, and full conversation history backed by SQLite table `hlsm_episodic` with SQLite FTS5 full-text search index (`hlsm_episodic_fts`).
- **L2 Semantic Memory:** Long-term vector embeddings for RAG and semantic retrieval, backed by Sentence-Transformers (`all-MiniLM-L6-v2`) and KùzuDB graph nodes (`polytope_data.kuzu`). Distilled chat turns are ingested via `ingest_distilled_intent` into L2 semantic nodes (`mem_intent_*`).
- **L3 Knowledge Graph:** Permanent structured entity-relationship graph nodes backed by the KùzuDB embedded graph engine (`polytope_data.kuzu`).
- **Absolute Path Database Resolution (`database.py` & `config.py`):** All relative database URIs (`sqlite:///polytope_data.db` and `./polytope_data.kuzu`) are automatically resolved to absolute file paths anchored directly to the project root directory.

---

## 4. Autonomy, Affective Computing & Proactivity

- **PCL (Proactive Cognition Layer / `backend/pcl.py`):** Continuous background cognitive loop operating across a 5-stage lifecycle (`OBSERVE → MODEL → DETECT → JUDGE → ACT`). Builds stateful `WorldModelSnapshot` records, evaluates opportunities (`StalledGoalDetector`, `HardwareAnomalyDetector`, `AffectiveStressDetector`), and dispatches proactive tasks or WebSocket notifications (`JsonRpcGateway`).
- **Nightly "Dream" Cycle Evolution (`cron_engine.py`):** When hardware load is low, the daemon halts external polling and reallocates 100% of local resources to internal evolution—distilling episodic logs into permanent Semantic Truths and harvesting teacher-student preference pairs for local DPO fine-tuning.
- **ACE (Affective Computing Engine):** Python-native modules (`backend/ace/`) simulating valence, arousal, and emotional tension ($\psi$), dynamically modulating LLM sampling temperature and cognitive stress levels based on live wearable biometrics.
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
