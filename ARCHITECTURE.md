# Alluci Sovereign Agent Architecture

This document defines the immutable laws and architectural foundation of the Alluci Sovereign Agent.

---

## 1. Core Inference & Compute (Local Compute Engine - LCE)

- **The LCE Law (Local Compute Engine):** The system relies strictly on official Apple MLX Python frameworks (`mlx_lm` and `mlx_vlm`) for local inference. The Local Compute Engine (LCE) evaluates models natively in Python without relying on brittle C++ inference kernels.
- **Agent-First Hybrid Model Routing:** Specialized sub-agents (e.g., Deep Research / Rocco) MAY specify designated Cloud Token Router models (e.g., Kimi 3 / `moonshotai/kimi-k3-free`). When an explicit `agent_id` is supplied, `router.py` MUST resolve the agent's assigned model override directly to offload high-density synthesis to the cloud API with 0 MB local VRAM allocation. If offline or airgapped, local LCE execution MUST enforce 4-bit (Q4) quantized model weights (~16 GB VRAM) to prevent Metal memory exhaustion.
- **Custom Architectures & Runtime Mappings:** Any custom architectural variations or proprietary model definitions MUST be transparently mapped directly to native `mlx_lm` implementations within `backend/inference/mlx_engine.py` using runtime dictionary mappings (e.g., overriding `_get_classes`), avoiding the need for dedicated monkey-patching or `nn.Module` reimplementations.
- **Dynamic KV Cache Strategy & Purging:** To support Deep Research workloads without Out-Of-Memory (OOM) errors, the LCE dynamically toggles the KV cache format (switching to Q4 quantization for contexts >8,000 tokens) and mandates compulsory `mx.metal.clear_cache()` purges before and after synthesis loops.
- **Multi-Agent Concurrency:** The LCE uses a strict Python `asyncio.Lock` and queue system to manage concurrent requests from multiple agents. C++ mutexes are strictly forbidden.

---

## 2. Security, Integrity & Human-in-the-Loop Safeguards

- **Human-in-the-Loop (HITL) Executive Approval Gate:** All destructive memory purges or sensitive system operations MUST be intercepted before execution and gated by explicit sovereign HITL approval. The agent is STRICTLY FORBIDDEN from autonomously deleting memories or generating simulated LLM deletion confirmations.
- **3 Hard Security Guards (`backend/routers/gemini.py`):**
  1. *Guard 1 (Code Context Bypass):* Bypasses memory wipe logic if technical programming terms (`clear_cache`, `mx.metal`, `code`, `script`, `app`, `css`) are present.
  2. *Guard 2 (Intent & Pattern Matcher):* Matches explicit deletion intents (`"delete memory"`, `"purge memories"`, `"delete imessage"`, `"clear memories"`) and extracts targeted target strings (E.164 phone numbers like `+13108047867` or 5-6 digit SMS short codes like `21093`).
  3. *Guard 3 (Short Pattern & Stop-Word Defense):* Blocks patterns shorter than 3 characters or matching common stop-words (`"a"`, `"the"`, `"for"`).
- **Security Resolution Protocol (`backend/routers/security.py` & `SecurityInterventionModal.tsx`):**
  - Broadcasts `security.resolution_required` WebSocket events to render the primary **`[ Approve & Execute Memory Purge ]`** and **`[ Cancel Task ]`** modal UI.
  - Upon approval, executes multi-tier deletion via `hlsm_manager.delete_by_pattern`, broadcasts completion cards, and emits `memory.deleted` WebSocket events for real-time React UI state auto-syncing.
- **DPK (Discrete Projection Kernel):** A module (`dpk.py`) that monitors "Manifold Tearing" by comparing real-time topology shifts against dynamic thresholds.
- **AVL Gate (Action Verification Loop):** A three-pillar safety mechanism for LLM outputs:
  1. *Sovereign Attribution:* Validates cryptographic and manifold signatures.
  2. *ALCE Gradient Smoothness:* Ensures Lipschitz continuity budget is not exceeded.
  3. *Topological Continuity:* Rejects actions causing Euler characteristic mismatches.
- **Continuous Calibration Manager:** Manages continuous statistical normalization for DPK thresholds based on tool history, skill history, and affective tension (`calibration.py`).

---

## 3. Hierarchical Long-Short Manifold (H-LSM) Memory Architecture

The H-LSM memory architecture operates across 4 cognitive storage tiers managed by `HLSMManager` (`backend/memory/hlsm_manager.py`):

- **L0 Working Memory:** Ultra-fast session context (expiring working memory) backed by Redis (Key-Value) with automatic fallback to SQLite table `hlsm_working`.
- **L1 Episodic Memory:** Chat turn interactions, episodic events, and full conversation history backed by SQLite table `hlsm_episodic` with SQLite FTS5 full-text search index (`hlsm_episodic_fts`).
- **L2 Semantic Memory:** Long-term vector embeddings for RAG and semantic retrieval, backed by Sentence-Transformers (`all-MiniLM-L6-v2`) and KùzuDB graph nodes (`polytope_data.kuzu`).
- **L3 Knowledge Graph:** Permanent structured graph nodes and entity relationships backed by the KùzuDB graph engine (`polytope_data.kuzu`).
- **Absolute Path Database Resolution (`backend/database.py` & `backend/config.py`):**
  - All relative database URIs (`sqlite:///polytope_data.db` and `./polytope_data.kuzu`) are automatically resolved to absolute file paths anchored directly to the project root directory (`/Users/alluci/Downloads/alluci-sovereign-agent-main/polytope_data.db`).
  - Ensures all backend services, REST endpoints, background tasks, and worker processes query and mutate the exact same unified database instance regardless of process working directory.

---

## 4. Autonomy, Affective Computing & Proactivity

- **PCL (Proactive Cognition Loop):** The daemon responsible for autonomous execution (`backend/pcl.py`). It continuously extracts episodic memories from H-LSM, builds a unified `WorldModelSnapshot`, and generates `PCLOpportunity` records for proactive execution.
- **ACE (Affective Computing Engine):** Python-native modules (`backend/ace/`) simulating valence, arousal, and emotional tension, modulating LLM temperature and cognitive stress levels.
- **BTM (Behavioral Topological Mapper):** A biometric and affective tracking kernel (`btm.py`) managing histories (e.g. HRV/GSR analogs) to map cognitive tension to topological space.

---

## 5. Gateway & Multi-Bridge Communication Architecture

- **Unified Multi-Bridge Gateway (`backend/channels.py`, `backend/bridges/`):** Integrates Telegram, Nostr, Signal, iMessage, Apple Watch biometrics, WhatsApp, Discord, Slack, Instagram, Facebook, WeChat/WeCom, and Email (IMAP/SMTP).
- **Unix Domain Socket Signal Daemon:** The Signal bridge operates via a local Java JSON-RPC daemon communicating over Unix domain socket `/tmp/signal-cli.sock`.
- **Real-Time WebSocket Protocol (`backend/ws_gateway.py`):**
  - Operates JSON-RPC 2.0 streaming gateways on `/ws/admin` (Port 3000 -> 8000 proxy).
  - Emits real-time administrative events (`security.resolution_required`, `memory.deleted`, `chat.message.received`) to keep client UI components synchronized in real-time.

---

**WARNING:** Any future modifications to action generation, memory management, or inference pipelines MUST strictly respect these definitions. Violating these principles will compromise sovereign constraints and manifold integrity.
