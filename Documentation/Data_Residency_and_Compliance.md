# Alluci Sovereign Agent: Data Residency & EU Compliance

This document outlines the architectural safeguards, configuration flags, and data transfer principles that ensure the Alluci Sovereign Agent complies with international Data Residency laws (including the GDPR and Schrems II rulings) while maintaining maximum cognitive performance.

---

## 1. The Local-First Baseline

The Alluci Sovereign Agent is built on a strict **Local-First** ethos. By default, the system guarantees physical data locality for storage:

- **The Vault:** All API keys, secrets, and connection credentials are encrypted and stored locally via the Verus Vault.
- **The Dream Pool:** All telemetry, memory logs, and historical context used for the "Teacher-Student" fine-tuning cycle (LoRA Forge pipeline) are stored on the host machine.
- **SQLite / Vector Stores:** Knowledge retrieval and session histories exist entirely within local SQLite or local vector databases.

Because data is stored physically on the user's host hardware, **Data Storage Residency is inherently solved.** If the user's physical machine resides within the European Union, the data mathematically remains within the European Union.

---

## 2. The Cloud Egress Dilemma

The primary legal compliance challenge for local-first AI is **Data Transfer** (egress) when routing inference prompts to high-performance, 3rd-party global cloud models (e.g., OpenAI's GPT-4o, Google's Gemini 1.5 Pro). Sending Personally Identifiable Information (PII) to US-based datacenters violates strict interpretations of the GDPR without complex standard contractual clauses.

However, crippling the agent by disabling cloud access starves the **Teacher-Student Dream Cycle**, which relies on high-quality outputs from massive frontier models to fine-tune the local *Gemma 4 Alluci* variant.

---

## 3. The "Defense in Depth" Solution

To solve this, Alluci employs a **"Defense in Depth"** strategy utilizing Pseudonymization, hard-locked Proxy routing, and optional physical endpoint overrides.

### 3.1. The AlluciSecureProxy (Pseudonymization)
The core of the compliance engine is the `AlluciSecureProxy`.
1. **Interception:** Before any data leaves the device to reach a cloud provider, the proxy intercepts the raw prompt.
2. **PII Extraction:** It scans for sensitive data (emails, credit cards, crypto addresses, proper names) and extracts them.
3. **The Ephemeral Vault:** It stores the extracted data locally in volatile RAM within the `secure_ephemeral_vault`.
4. **Abstract Swapping:** It swaps the real data with abstract identifiers (e.g., `[ALLUCI_EMAIL_TOKEN]_1001`) and sends this purely abstract payload to the cloud.
5. **Re-hydration:** When the cloud returns an abstract response, the proxy uses the local vault to deanonymize it before presenting it to the user.

**Legal Justification (GDPR Recital 26):**
Because the abstract payload sent to OpenAI/Gemini is stripped of all real-world markers, and because the decryption keys/vaults *never physically leave the EU host machine*, the payload is legally **Pseudonymized**. It is mathematically impossible for the cloud provider to identify the user or read their personal data.

### 3.2. Configuration & Orchestrator Locks
To strictly enforce this, two configuration flags exist in `backend/config.py`:

```python
DATA_REGION: Literal["US", "EU", "GLOBAL"] = "GLOBAL"
ENFORCE_EU_ENDPOINTS: bool = False
```

#### `DATA_REGION = "EU"`
When the region is configured to EU, the Orchestrator (`router.py`) **hard-locks** the `AlluciSecureProxy`. If any sub-agent, routine, or internal mechanism attempts to invoke a cloud API without first passing through the Proxy to scrub PII, the Orchestrator will raise a `RuntimeError` and terminate the request. This guarantees zero PII egress.

#### `ENFORCE_EU_ENDPOINTS = True`
For ultra-strict enterprise auditors who require physical locality even for pseudonymized abstract data, enabling this flag will force the Orchestrator to rewrite Cloud API targets on the fly:
- **Google Gemini:** Dynamically rewrites the Google Generative AI SDK client options to point to `europe-west3-aiplatform.googleapis.com` (Frankfurt Vertex AI Hub).
- **OpenAI:** Requires the `OPENAI_BASE_URL` to point to an EU-hosted Azure proxy, throwing compliance warnings if a non-EU URL is detected.

---

## 4. Synergy with the LoRA Forge Pipeline

Because the proxy intercepts both the abstract outbound prompt and the abstract inbound response, it logs these *abstract pairs* to the **Dream Pool**. 

This means the Dream Pool dataset is 100% devoid of PII! When the LoRA Forge fine-tunes the local `Gemma 4 Alluci` model, it trains it purely on **logical reasoning pathways**, completely eliminating any risk of the local model accidentally memorizing the user's passwords, Verus identities, or personal communications.

By embracing this architecture, Alluci maintains maximum cognitive performance, fuels its self-improvement pipeline, and adheres to the strictest global data residency standards simultaneously.
