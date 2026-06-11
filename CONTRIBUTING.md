# Contributing to the Alluci Sovereign Agent

Welcome, and thank you for your interest in the Alluci Sovereign Agent architecture.

**The Alluci Sovereign Agent is 100% proprietary software.** We are building a mathematically secure, zero-trust cognitive architecture designed to guarantee absolute data sovereignty. Because of the highly sensitive, cryptographic, and topological nature of this system, we do not operate under a standard open-source contribution model.

We maintain a strictly-gated, high-trust engineering environment. **We do not accept unsolicited pull requests, automated AI-generated code dumps, or "vibe-coded" patches.** Every line of code entering the main branch is subjected to rigorous zero-trust security audits, topological continuity checks, and manual architectural review.

If you are an elite, highly qualified engineer who aligns with the ethos of absolute data sovereignty and local-first compute, we welcome you to apply for "Verified Contributor" status.

---

## 1. The "Verified Contributor" Gate

To prevent repository bloat and ensure the highest security standards, all contributions must be pre-authorized. **Unsolicited Pull Requests from unverified actors will be immediately closed.**

### How to Apply for Verified Status
We do not use GitHub Issues for contributor requests, as this creates unnecessary noise for the core engineering team.

If you are interested in contributing, please send an **Expression of Interest** to **query@alluci.ai** with the subject line:
`[Alluci Core Contributor Request] - <Your Name>`

Please include:
1. A brief summary of your professional engineering background (e.g., GitHub profile, LinkedIn, or portfolio).
2. The specific architectural subsystem you wish to enhance (e.g., *Polytope Projection Network*, *Sovereign Proxies*, *Axiomatic Value Logic*, *Local Cognitive Engines*).
3. A brief outline of the value you intend to bring to the architecture.

Our core team will review your request privately. If your expertise aligns with our roadmap, you will undergo our verification process. Once cleared, you will be granted **Verified Contributor** status and authorized to open Pull Requests.

---

## 2. Engineering & Quality Standards

Verified Contributors must adhere to strict zero-trust engineering principles:

- **Zero AI-Vibe Coding:** While AI coding assistants are powerful tools for scaffolding, contributors are held 100% accountable for the determinism, security, and mathematical soundness of their commits. Blindly pushing AI-generated code without deep architectural understanding is grounds for immediate revocation of contributor status.
- **Local Quality Gates:** You MUST run the production readiness suite before committing. If your code fails the local tests, type checks, or security scans, the PR will be rejected.
  ```bash
  # Run the full quality and security gate
  make quality
  ```
- **Commit Message Standards:** We enforce [Conventional Commits](https://www.conventionalcommits.org/). This maintains a clean, auditable cryptographic history.
  - Examples: `feat(ppn): Implement new homology projection algorithm`, `fix(proxy): Resolve PII leakage in edge case`, `sec(avl): Harden Lipschitz budget constraints`.

---

## 3. Pull Request (PR) Requirements

When a Verified Contributor opens a Pull Request, our automated **Security Impact Review** template will trigger. 

**Every PR must explicitly address:**
1. **Data Egress Boundaries:** Does this code touch or alter any network egress pathways?
2. **Cryptographic Handling:** Does this interact with the Verus Vault, JWT keys, or local encryption?
3. **Topological Determinism:** Does this introduce any floating-point non-determinism into the cognitive topology or PPN?

### The Review Checklist
Before your code is merged, it must satisfy the following:
- [ ] You are a **Verified Contributor**.
- [ ] The code passes `make quality` locally.
- [ ] You have written comprehensive unit tests for the newly introduced logic.
- [ ] The **Security Impact Review** section in the PR template is fully completed.
- [ ] No GPL, AGPL, or other viral open-source licenses have been introduced to the dependency graph.

We are deeply committed to building the most secure, autonomous cognitive architecture in the world. We look forward to collaborating with engineers who share this vision.
