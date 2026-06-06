# Polytope Autonomous Executive (A2UI) v4.3 — ARCHITECTURE & TOPOLOGY

## 1. Overview
The Polytope Sovereign Agent is built on the [A2UI] (Autonomous-to-User Interface) protocol. It prioritizes **Simplicial Sovereignty**, ensuring that sensitive cryptographic material and PII never leave the local hardware (Apple Silicon or X86_64_Metal).

## 2. The Simplicial Manifold (PPN & DPK)
To ensure execution integrity, the system utilizes a **Polytopological Persistence Network (PPN)** combined with a **Discrete Projection Kernel (DPK)**.

#### Mathematical Foundation
For every objective $O$, we define a persistence manifold $M_O$ as a filtration of simplicial complexes $K_i$. 
The PPN embeds the objective into a high-dimensional latent space:
$$ \mathcal{P}(O, \psi) = \bigoplus_{i=0}^n H_i(K, \mathbb{Z}_2) $$
Where $\psi$ is the affective tension (biometric stress) of the system.

The **Betti Numbers** ($\beta_0, \beta_1, \beta_2$) quantify the connectivity of the manifold. 
If the Betti numbers fluctuate beyond the threshold $\tau$, a **Topological Rupture** is detected, and execution is halted via the DPK:
$$ \text{Authorize}(K) = \mathbb{1} \left[ \chi(K) = \sum_{j=0}^{d} (-1)^j \text{rank}(C_j) \right] $$
This ensures that the agent's plan is topologically sound and respects the user's defined "Identity Constraints."

## 3. Sovereign Security Layers
| Layer | Name | Technology | Responsibility |
|---|---|---|---|
| **Tier 1** | Passkey (L1) | WebAuthn / FIDO2 | Cryptographic biometric handshake (hardware-bound). |
| **Tier 2** | Vault (L2) | PolytopeSecretManager | AES-256-GCM encryption of bridge API keys. |
| **Tier 3** | Ledger (L3) | VerusID (VDXF) | Decentralized, immutable audit of all agent actions. |

## 4. Bridge Orchestration
The `BridgeManager` provides a unified interface for disparate communication protocols:
- **iMessage (Apple Script + Python Bridge Engine)**
- **Gmail / Google Workspace (OIDC + VerusID Synchronization)**
- **Meta/Social Manifold (Signal, WhatsApp, Telegram, X)**

## 5. Inference Manifold (The Model Router)
The `ModelRouter` manages a fleet of LLM providers. It uses **Fail-Safe Cognitive Switching**:
1. **Primary**: Locally hosted Gemma 4 MLX (Sovereign Local).
2. **Harmonic**: Gemini-1.5-Pro (Cloud High-Reasoning).
3. **Emergency**: Groq/DeepSeek (Low-Latency burst).

---

## 6. Sovereign Agent Standing Orders (Heartbeat Daemon)

This file is read by the `HeartbeatDaemon` every 15 minutes.
Checked items (`- [x]`) are active. Unchecked items (`- [ ]`) are ignored.

NETWORK CONSENT: Orders that make external HTTP requests must include `[NETWORK_OK]`.
Orders WITHOUT this marker that attempt network access will be blocked.

### 6.1 Project Hygiene
- [ ] Monitor `tasks.md` for changes and suggest prioritization updates.
- [ ] Scan `/logs` for critical error bursts and summarize.

### 6.2 External Awareness
- [ ] Monitor `https://news.ycombinator.com` for "AI Agent" keywords. (Requires Web Tool)
- [ ] Check `inbox/` directory for new data dumps.

### 6.3 Autonomy
- [ ] If `tasks.md` has overdue items, draft a proactive Slack message asking for status.

## 7. Security Operations Guide

### 7.1 Secret Management

The Alluci Sovereign Agent uses a tiered secret retrieval strategy to ensure maximum security and sovereignty.

#### Secret Priority Chain
1. **Environment Variables**: Highest priority. Overrides everything.
2. **OS Keychain (keyring)**: Recommended for local sovereign deployments. Uses the system's native secure storage (macOS Keychain, GNOME Keyring, Windows Credential Manager).
3. **Defaults**: Lowest priority.

#### Configuration
- `SECRETS_PROVIDER`: Set to `keyring` (default) to use the OS keychain.
- `KEYRING_SERVICE`: The name of the service in the keychain (default: `alluci-sovereign`).

#### Purge Incident Response (v6.3)
Committed TLS private material (`certs/privkey.pem`) was identified and purged from the repository.
**Action Required**:
1. All instances must rotate their TLS certificates immediately.
2. Ensure `certs/` and `*.pem` are ignored via `.gitignore` (implemented).
3. Do not commit `.env` or keychain export files.

### 7.2 Certificate Rotation
To rotate certificates in a production environment:
1. Generate new keys locally or via Let's Encrypt.
2. Mount the new `certs/` directory into the NGINX container.
3. Reload NGINX: `docker exec alluci-nginx nginx -s reload`.

## 8. Sovereign Voice Architecture (STRICT MANDATE)
**DO NOT DEVIATE:** The Alluci Sovereign Agent strictly utilizes local, on-device models for all voice processing. Cloud TTS/STT APIs (e.g., ElevenLabs) are considered legacy mock configurations and MUST NOT be used in the core pipeline.
- **Speech-to-Text (STT):** Powered exclusively by `mlx-whisper` on Apple Silicon, with a graceful fallback to `whisper.cpp` (`WHISPER_METAL=1`).
- **Text-to-Speech (TTS):** Powered exclusively by `Kokoro-82M` (via `kokoro-mlx`) generating raw PCM buffers locally.
- **Dynamic Tiering:** The `VoiceOrchestrator` must dynamically tier the whisper models (`tiny-4bit`, `base-8bit`, `large-v3-turbo`) based on the connected client's hardware identifier.
- **Anti-Spoofing:** All incoming audio payloads must be cross-referenced for micro-hesitations (via Whisper) against live biological respiratory data (via Apple Watch/HealthKit) to defeat deepfakes.

---
*Created by Alluci-Ai Sovereign Agent Framework v4.3*

