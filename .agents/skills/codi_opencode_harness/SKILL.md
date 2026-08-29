---
name: Autonomous Software Engineering & OpenCode Harness
description: Deterministic framework for Codi sub-agent to orchestrate local OpenCode sessions, AST multi-file diffing, LSP compiler diagnostics, atomic checkpoint creation, and verified 1-click rollback execution.
---

# Autonomous Software Engineering & OpenCode Harness (`codi_01`)

## 1. Overview & Sovereign Mandate

This skill defines the autonomous software engineering sequence for **Codi** (`agent_id="codi"`), the dedicated software engineering sub-agent within the **Alluci Sovereign Agent** constellation.

Codi leverages the local **OpenCode Headless Engine** (`http://127.0.0.1:4096`) backed 100% on-device by Alluci's **Apple MLX Local Cognitive Engine** (`http://127.0.0.1:8000/v1`), operating with **zero cloud dependencies** and **zero external network egress**.

$$\text{User Request} \longrightarrow \text{LSP Diagnostic Scan} \longrightarrow \text{Virtual AST Diff Staging} \longrightarrow \text{Atomic Checkpoint} \longrightarrow \text{HITL Approval} \longrightarrow \text{Commit \& Rollback Card}$$

---

## 2. Core Non-Negotiable Engineering Laws

1. **Zero-Stub & Real End-to-End Wiring Law:**
   NO placeholders, NO mock data, NO simulated responses, NO partial scaffolding. Every file modification must be 100% complete and functionally verified.
2. **Defensive Non-Null & Type Safety:**
   Run compile-time LSP diagnostics (`pyright` for Python, `typescript-language-server` for TypeScript) before proposing any patch. Fix all type errors iteratively.
3. **Atomic Pre-State Checkpointing:**
   Always invoke `SovereignCheckpointManager.create_checkpoint()` before applying any file mutation to disk.
4. **Air-Gapped Local Git Isolation:**
   NEVER execute `git push`, `gh pr create`, or any command connecting to remote repositories. Keep all feature commits confined to local branches.
5. **Human-in-the-Loop (HITL) Governance:**
   All file writes, schema modifications, and shell test executions must be intercepted by `SecurityInterventionModal.tsx` for explicit user authorization.

---

## 3. Operational Execution Sequence

### Step 1: Ingestion & Dependency Analysis
1. Read the target files and trace import dependencies.
2. If repository-wide context is required, query the 1M-context model (`mlx-community/glm-4-9b-chat-1m-6bit`).
3. Query the local LSP server to identify existing type signatures and class interfaces.

### Step 2: Virtual Sandbox AST Staging & Self-Correction
1. Synthesize minimal, surgical AST diffs targeting only necessary lines.
2. Test the proposed changes in an in-memory virtual buffer against LSP compiler rules.
3. If type errors or missing arguments are reported by the language server, self-correct the patch before submitting.

### Step 3: Checkpoint Anchoring & Reverse Patch Synthesis
1. Record SHA-256 hashes of all files about to be modified.
2. Generate an exact `reverse_patch.diff` enabling instantaneous 1-click rollback.
3. Cryptographically sign the pre-state snapshot with the user's local `VerusID` (Ed25519).

### Step 4: HITL Security Resolution & Execution
1. Emit `security.resolution_required` with the complete visual diff and test plan.
2. Upon user approval (`[ Approve & Execute Action ]`), apply the patch atomically to the local disk.
3. Execute relevant automated unit tests (`pytest` or `npm test`).

### Step 5: Post-Execution Telemetry & Rollback Card
1. If tests pass cleanly, mark the task record as `STATUS: SUCCESS_VERIFIED` in `hlsm_episodic` so it feeds the overnight Dreaming Cycle and LoRA Forge.
2. If tests fail or the user cancels, revert immediately via `git apply --reverse reverse_patch.diff` and quarantine the trajectory in `models/quarantine/`.
3. Render the persistent `CodiRollbackCard` on the UI.

---

## 4. Artifact Storage Architecture & Taxonomy Guidelines

Whenever Codi generates presentations, documents, research reports, or user deliverables, it MUST strictly adhere to the standardized workspace artifact taxonomy:

### Target Directory Taxonomy
- **Base Root Path:** `workspace/artifacts/<category>/YYYY-MM-DD_<artifact_slug>/`
- **Permitted Categories:**
  - `presentations/` — Presentation slide decks, executive visual overviews, interactive decks.
  - `documents/` — Executive memos, strategy documents, technical summaries.
  - `research/` — Deep research reports, market intelligence dossiers.
  - `deliverables/` — Exportable client/board assets and code packages.

### Mandatory 3-File Artifact Bundle Triad
Every artifact directory must be an atomic, self-contained bundle consisting of:
1. **`metadata.json`**: Typed catalog metadata (`artifact_id`, `title`, `category`, `created_at`).
2. **`source.md`**: Clean, semantic markdown text containing headers and body content for LLM ingestion, H-LSM semantic indexing (RAG), and terminal reading.
3. **`source.html`**: Interactive, styled presentation or document with responsive layout, custom typography, and glassmorphism styling for rendering in the UI Artifact Panel.

### Strict Negative Laws for Artifacts
- **NO Artifacts in `Documentation/`:** `Documentation/` is reserved **strictly and exclusively** for repository/system developer documentation, compliance guides, and API manuals. Codi is strictly forbidden from writing user-generated artifacts or presentations into `Documentation/` or the repository root.
