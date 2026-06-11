# Alluci Sovereign Agent: Information Security Policy (SOC-2 / ISO-27001)

This Information Security Policy outlines the architectural and operational controls integrated into the Alluci Sovereign Agent to align with SOC-2 Trust Services Criteria and ISO-27001 standards. 

Because the Alluci Sovereign Agent operates on a strictly **Local-First, Single-Tenant** architecture, many traditional cloud vulnerabilities are physically eliminated. This policy translates traditional enterprise security requirements into the Sovereign Agent context.

---

## 1. Asset Inventory & Classification

In a decentralized, local-first environment, the definition of an "asset" shifts from cloud infrastructure to localized data silos and cryptographic keys on the host machine.

### 1.1. Data Assets
| Asset Name | Classification | Storage Location | Protection Mechanism |
| :--- | :--- | :--- | :--- |
| **Verus Vault** | Critical / Highly Restricted | Local File System (`~/.polytope/`) | AES-256-GCM encryption via Polytope Master Key. |
| **polytope_data.db** | Confidential | Local File System (SQLite) | Host OS-level File Permissions. |
| **Dream Pool Telemetry** | Confidential | Local File System | Isolated from external egress; utilized only by local LoRA Forge. |
| **AlluciSecureProxy Cache** | Volatile Confidential | Local RAM | Ephemeral; destroyed instantly upon response deanonymization. |

### 1.2. Cryptographic Assets
- **Polytope Master Key:** The root cryptographic seed used to derive encryption keys. Never stored in plaintext; resides only in active memory or secure hardware enclaves during execution.
- **Verus Identities (i-Addresses):** Cryptographic signatures proving ownership of the vault and blockchain-anchored data.

---

## 2. Access Control & Authorization (RBAC)

Traditional Role-Based Access Control (RBAC) assumes a multi-tenant cloud application. In the Sovereign Agent, RBAC is redefined as **Hierarchical Cryptographic Access Control**.

### 2.1. The Sovereign Master Gate
Access to the entire system is gated by the `POLYTOPE_MASTER_KEY` and Biometric Step-Up validation (Affective Tension/PSI monitoring). 
- **Authentication:** To initiate the daemon or access the web interface, the Master Key must be supplied (e.g., `/api/v1/auth/login`).
- **Authorization:** Only the holder of the Master Key operates at the **Sovereign Admin** level.

### 2.2. Vault Segmentation
The local Verus Vault operates its own internal access control matrix to prevent sub-agents from over-accessing secrets:
- Secrets are namespace-isolated (e.g., `alluci_api_keys`, `verus_identities`).
- A sub-agent delegated to draft an email is only granted access to the `email_credentials` namespace and cannot decrypt or access the `verus_wallet` namespace.

---

## 3. Incident Response & Lockdown Protocols

Because the agent is autonomous, Incident Response is largely automated via internal **Circuit Breakers** and **Autonomic Nervous System (ANS)** monitoring.

### 3.1. Incident Triggers
1. **Biometric Failure / High PSI Spike:** If the user's affective tension suddenly spikes or hardware biometric validation fails during a critical task, the system triggers an automatic downgrade of `AutonomyLevel`.
2. **Financial Threshold Breach:** The LLM Circuit Breaker monitors inference token costs. If an infinite loop or adversarial prompt triggers massive cloud usage, the circuit breaker instantly severs cloud API connections.
3. **Cryptographic Integrity Failure:** If the `ExecutionManifest` signature validation fails, indicating an external script is trying to bypass the orchestrator, the request is rejected with a 403 Forbidden.

### 3.2. Automated Lockdown Sequence
When a critical incident is detected:
1. **Airgap Enforcement:** The agent forcefully sets `SOVEREIGN_MODE = True`, terminating all connections to external third-party providers (OpenAI, Gemini).
2. **Task Suspension:** All active background objectives are suspended and pushed to the `queued_task` table with a status of `SUSPENDED_SECURITY`.
3. **Audit Ledger Lock:** The incident is cryptographically logged into the `AuditLog` and optionally anchored to the Verus Blockchain to provide an immutable forensic trail.

---

## 4. Third-Party Provider Risk Assessment

The Sovereign Agent utilizes third-party LLM providers (Google, OpenAI) strictly as stateless computational engines, never as data processors.

### 4.1. The AlluciSecureProxy Risk Mitigation
The primary risk of utilizing third-party LLMs is the exposure of Personally Identifiable Information (PII) and the unauthorized retention of data by the provider.

To mitigate this risk to acceptable SOC-2 tolerances:
- **Zero-Trust Egress:** The `AlluciSecureProxy` intercepts all outbound requests.
- **Pseudonymization:** All PII is stripped and replaced with mathematically abstract tokens (e.g., `[EMAIL_1001]`).
- **Evaluation:** Third-party providers are assessed based on their ability to execute abstract logic. Because the data they receive is legally pseudonymized (GDPR Recital 26) and useless without the local ephemeral vault, the risk of data leakage via the provider's servers is mathematically negated.

### 4.2. Regional Compliance Enforcement
If an enterprise or individual requires strict physical infrastructure compliance (Schrems II):
- The agent utilizes the `DATA_REGION = "EU"` configuration.
- The `ENFORCE_EU_ENDPOINTS` policy dynamically rewrites Google Generative AI and Azure OpenAI client URLs to guarantee physical server locality (e.g., Frankfurt/Paris datacenters), further reducing third-party cross-border risk.
