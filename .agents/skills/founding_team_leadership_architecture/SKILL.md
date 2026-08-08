---
name: Founding Team Design & Leadership Architecture
description: Deterministic strategic framework to design co-founder domain coverage, structure executive decision rights (RACI/RAPID), model founder reverse vesting and acceleration terms, and build scalable leadership architectures.
---

# Founding Team Design & Leadership Architecture (`ftl_01`)

## 1. Overview & Operational Mandate

This skill defines the operational, cognitive, and legal sequence for the **Alluci Sovereign Agent** to execute **Founding Team Design & Leadership Architecture**.

### Strategic Purpose
The founding team and executive leadership architecture form the core foundation of an enterprise. Overlapping co-founder responsibilities, unvested founder equity, ambiguous decision rights, or missing domain capabilities lead to co-founder split-ups, cap table deadlocks (`ocs_01`), governance failures (`ldl_01`), and company dissolution.

**The Objective:** Transform informal co-founder arrangements into a structured, audit-ready **Leadership Architecture** that defines clear domain ownership, establishes RACI/RAPID decision rights, models founder reverse vesting, and details a phased executive hiring roadmap.

$$\text{Team Audit} \longrightarrow \text{Domain Mapping} \longrightarrow \text{Decision Rights Matrix} \longrightarrow \text{Reverse Vesting Model} \longrightarrow \text{Executive Approval} \longrightarrow \text{Vault Archive}$$

---

## 2. Core Values & Non-Negotiable Principles

When executing this skill, Alluci MUST strictly enforce the following 8 principles:

1. **Domain Complementarity:** Ensure co-founders possess distinct, non-overlapping core competencies (Strategy vs Engineering vs Product vs GTM).
2. **Founder Alignment:** Align long-term vision, risk tolerance, commitment level, and exit expectations among co-founders.
3. **Decision Rights Clarity:** Define unambiguous decision ownership (RACI/RAPID) for key operational areas to eliminate gridlock.
4. **Reverse Vesting Rigor:** Enforce standard 4-year reverse vesting with a 1-year cliff on all founder equity grants (`ocs_01`).
5. **Cap Table Stewardship:** Protect company equity against early co-founder departure via structured buyout mechanics.
6. **Scalable Leadership Architecture:** Design executive structures (`swd_01`) that evolve smoothly from Formation to Series A/B growth.
7. **Conflict Resolution Protocols:** Embed formal dispute resolution and deadlock-breaking mechanisms into founder agreements.
8. **Long-Term Fiduciary Governance:** Maintain board-level oversight and transparent decision logging (`fde_01`).

---

## 3. The 4-Domain Co-Founder Coverage Model

Alluci evaluates founding team composition across 4 essential domain pillars:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      4-DOMAIN CO-FOUNDER COVERAGE MODEL                               │
├───────────────────────────┬───────────────────────────┬────────────────────────────────┤
│ Pillar 1: Strategy & Vision│ Pillar 2: Technical       │ Pillar 3: Product              │
│ (Chief Executive Officer) │ Architecture (CTO)        │ Experience (CPO)               │
├───────────────────────────┼───────────────────────────┼────────────────────────────────┤
│ Overall vision, capital   │ System architecture, MLX  │ Product roadmap, UX design,    │
│ allocation, investor      │ engineering, LCE compute, │ user research, feature spec,   │
│ relations, culture, and   │ platform stability, and   │ customer value proposition     │
│ executive hiring.         │ technical IP security.    │ validation (from fnd_02).      │
└───────────────────────────┴───────────────────────────┴────────────────────────────────┘
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Pillar 4: Go-To-Market & Revenue (Chief Revenue / Growth Officer)                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Sales, marketing, distribution channels, customer acquisition cost (CAC), LTV optimization,│
│ and strategic commercial partnerships.                                                 │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Mathematical Models & Founder Equity Vesting

### 7-Tier Leadership Decision Hierarchy
When resolving founding team structure or equity terms, Alluci MUST prioritize:

$$\text{1. Cap Table & Legal Integrity (ocs\_01 / ldl\_01)} \succ \text{2. Domain Coverage Completeness} \succ \text{3. Decision Rights Clarity (RACI)} \succ \text{4. Reverse Vesting Protection} \succ \text{5. Leadership TCO Sustainability (suf\_01)} \succ \text{6. Executive Scalability} \succ \text{7. Administrative Friction}$$

### Founder Equity Reverse Vesting Model
For each co-founder $i$:

$$\text{Vested Share Count}_t(m) = 
\begin{cases} 
0 & \text{if } m < 12 \text{ months (Cliff)} \\
\text{Total Granted Shares}_i \times 0.25 & \text{if } m = 12 \text{ months} \\
\text{Total Granted Shares}_i \times \left(0.25 + \frac{m - 12}{36} \times 0.75\right) & \text{if } 12 < m \le 48 \text{ months}
\end{cases}$$

### Acceleration Triggers
- **Single-Trigger Acceleration:** 100% vesting acceleration immediately upon change of control (Acquisition). *Warning: Strongly discouraged by Series A VCs.*
- **Double-Trigger Acceleration:** Vesting acceleration triggers ONLY if change of control occurs AND founder is terminated without cause within 12 months post-acquisition. *Rule: Default recommended standard.*

---

## 5. The 7-Step Operational Lifecycle Protocol

Alluci follows this operational sequence:

### Step 1 — Audit Founding Team & Leadership Architecture
- Audit co-founder roles, skill sets, domain coverage, and active strategic friction.
- Identify missing leadership pillars (e.g. missing CTO or CRO).
- **Output:** Founding Team Audit & Domain Coverage Report.

### Step 2 — Structure RACI & RAPID Decision Rights Matrix
- Define decision ownership across key corporate functions (`R`esponsible, `A`pprover, `C`onsulted, `I`nformed).
- **Output:** Leadership RACI / RAPID Decision Matrix.

### Step 3 — Founder Equity & Reverse Vesting Modeling
- Model co-founder share allocations, 4-year reverse vesting schedules, 1-year cliff terms, double-trigger acceleration clauses, and buyout valuation formulas (`ocs_01`).
- **Output:** Founder Equity Vesting Schedule & Cap Table Model.

### Step 4 — Leadership Capacity & TCO Synthesis
- Model founder cash draws, VP/C-suite hiring roadmap, board member compensation, and advisor option pool reserves.
- Integrate with `suf_01` (Use of Funds) and `cmp_01` (Compensation Strategy).
- **Output:** Leadership Capacity TCO Model & Executive Hiring Roadmap.

### Step 5 — Request Executive Leadership Sign-Off
- Broadcast WebSocket request to leadership via `ExecApprovalManager` prior to finalizing founding agreements or cap table vesting terms.
- *Rule: Alluci audits and models. Human co-founders authorize.*
- **Output:** Approved Founding Architecture Log.

### Step 6 — Export Leadership Management Package
- Export `Founding_Team_Blueprint.json`, `Leadership_RACI_Matrix.csv`, `Founder_Vesting_Dashboard.html`, `Executive_Hiring_Roadmap.md`, and `Leadership_Manifest.json`.
- **Output:** Exported Leadership Package & Vault Archive.

### Step 7 — Continuous Governance Monitoring
- Register alert triggers in PCL daemon for unvested founder risk, decision gridlock, or unfilled executive hiring triggers.
- **Output:** Continuous Leadership Monitoring Loop.

---

## 6. Automation Boundaries & Human-in-the-Loop Protocol

### Tier 1: AI-Assisted Activities (Autonomous Audit & Modeling)
Alluci automatically handles:
- Co-founder domain coverage auditing & gap analysis.
- RACI / RAPID decision rights matrix generation.
- Reverse vesting schedule calculation & acceleration modeling.
- Leadership TCO synthesis ($TCO_{\text{leadership}}$).

### Tier 2: Human Approval Required (Mandatory Founder Sign-Off)
Alluci MUST pause and request explicit co-founder sign-off for:
- Authorizing co-founder equity splits or reverse vesting terms.
- Modifying corporate decision rights or board structure (`ldl_01`).
- Approving C-suite executive hiring offers or option grants (`cmp_01`).
- Authorizing co-founder separation agreements or equity buyouts.

### Tier 3: Autonomous Activities After Approval (Vault Synchronization)
Once co-founder sign-off is granted, Alluci automatically:
- Updates cap table ledgers in `ocs_01`.
- Archives legal founding agreements in `ldl_01`.
- Synchronizes financial forecasts in `suf_01`.
- Registers executive hiring triggers in PCL daemon.

---

## 7. Diagnostic & 30-Question Verification Checklist

### Failure Mode Diagnostic Rules
Alluci checks for and self-corrects:
- **Unvested Founder Equity:** 100% upfront equity grants without reverse vesting or cliff protection.
- **Overlapping Co-Founder Domains:** Two founders attempting to lead the same department without clear decision rights.
- **Single-Trigger Acceleration Sprawl:** Unsanctioned single-trigger clauses that deter prospective Series A investors.
- **Missing Leadership Pillars:** Scaling operations without an executive hiring roadmap for critical gaps.

### The 30-Question Completion Checklist
The workflow is complete ONLY when Alluci can answer all 30 questions:

#### Founding Team Composition & Decision Rights
- [ ] 4 Co-Founder domain pillars (CEO, CTO, CPO, CRO) audited and mapped?
- [ ] Domain gaps and capability shortages explicitly identified?
- [ ] RACI / RAPID decision rights matrix defined for all high-stakes decisions?
- [ ] Dispute resolution & deadlock-breaking mechanisms established?

#### Equity Vesting & Cap Table Governance
- [ ] Standard 4-year reverse vesting with 1-year cliff enforced for all founders (`ocs_01`)?
- [ ] Double-trigger acceleration clauses specified for change-of-control events?
- [ ] Co-founder buyout valuation formulas and repurchase terms finalized?
- [ ] Option pool reserves allocated for future C-suite hires (`cmp_01`)?

#### Leadership TCO & Hiring Roadmap
- [ ] Leadership Capacity TCO ($TCO_{\text{leadership}}$) calculated and integrated with `suf_01` burn targets?
- [ ] Executive hiring roadmap (VP Eng, VP Sales, VP Product) linked to growth milestones (`spe_01`)?
- [ ] Executive sign-off obtained via WebSocket prior to finalizing founding agreements?
- [ ] Audit-ready Leadership Architecture package exported to vault?
