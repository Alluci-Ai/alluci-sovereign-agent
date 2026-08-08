---
name: Compensation Strategy & Total Rewards Management
description: Deterministic strategic framework to audit compensation bands, model equity incentive pools, benchmark market percentiles, structure total rewards packages, and optimize workforce cash/equity allocations.
---

# Compensation Strategy & Total Rewards Management (`cmp_01`)

## 1. Overview & Operational Mandate

This skill defines the operational, cognitive, and mathematical sequence for the **Alluci Sovereign Agent** to execute **Compensation Strategy & Total Rewards Management**.

### Strategic Purpose
Compensation is the core vehicle aligning individual incentives with enterprise strategy (`spe_01`), financial sustainability (`suf_01`), and equity stewardship (`ocs_01`). Unbenchmarked salary structures, unstandardized pay bands, or mismanaged equity option pools lead to key talent attrition, uncompetitive hiring, internal pay disparities, and unmodeled equity dilution.

**The Objective:** Establish a transparent, market-benchmarked, and mathematically sound **Total Rewards System** that optimizes cash compensation, variable incentives, equity option grants, and health benefits across all organizational roles.

$$\text{Comp Audit} \longrightarrow \text{Market Benchmarking} \longrightarrow \text{Salary Band Design} \longrightarrow \text{Equity Option Modeling} \longrightarrow \text{Executive Approval} \longrightarrow \text{Vault Archive}$$

---

## 2. Core Values & Non-Negotiable Principles

When executing this skill, Alluci MUST strictly enforce the following 8 principles:

1. **Pay Parity & Internal Fairness:** Maintain equal pay for equal value across gender, demographic, and geographical boundaries.
2. **Performance Alignment:** Align variable incentives and equity grants directly with strategic milestones (`spe_01`).
3. **Founder & Shareholder Equity Stewardship:** Protect capitalization table integrity (`ocs_01`) by sizing option pools responsibly.
4. **Market Benchmarking Rigor:** Anchor cash and equity ranges to empirical 50th, 75th, or 90th market percentiles for company stage.
5. **Total Rewards Optimization:** Evaluate total compensation holistically (Base Cash + Bonus + Equity Vesting Value + Benefits).
6. **Retention-Driven Vesting Design:** Enforce standard 4-year vesting schedules with a mandatory 1-year cliff.
7. **Transparency in Compensation:** Maintain clear grade and level guidelines for career progression.
8. **Financial Sustainability:** Ensure total compensation spend fits within net burn and runway targets (`suf_01`).

---

## 3. The 4-Pillar Total Rewards Architecture

Alluci structures compensation into 4 core pillars:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        4-PILLAR TOTAL REWARDS ARCHITECTURE                             │
├───────────────────────────┬───────────────────────────┬────────────────────────────────┤
│ Pillar 1: Base Cash       │ Pillar 2: Variable Cash   │ Pillar 3: Equity Incentives    │
│ (Fixed Salary)            │ (Bonus / Commission)      │ (ISO / NSO Options & RSUs)     │
├───────────────────────────┼───────────────────────────┼────────────────────────────────┤
│ Fixed monthly/annual cash │ Performance-linked bonus, │ Incentive Stock Options (ISOs),│
│ compensation benchmarked  │ sales commissions (MBOs,  │ Non-Qualified Options (NSOs),  │
│ to market percentile      │ ARR targets, product      │ RSUs with 4-year vesting and   │
│ ranges (P50, P75).        │ launch milestones).       │ 1-year cliff.                  │
└───────────────────────────┴───────────────────────────┴────────────────────────────────┘
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Pillar 4: Benefits, Tech & Total Rewards TCO                                           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ Health, dental, retirement 401(k), paid time off, plus hardware/software tooling      │
│ subscriptions per headcount (from swd_01).                                             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Mathematical Models & Equity Formulations

### 7-Tier Compensation Decision Hierarchy
When resolving compensation tradeoffs or structuring offer packages, Alluci MUST prioritize:

$$\text{1. Strategic & Role Impact} \succ \text{2. Market Benchmarking Alignment (P50/P75)} \succ \text{3. Internal Pay Parity} \succ \text{4. Cap Table Protection (ocs\_01)} \succ \text{5. Runway Sustainability (suf\_01)} \succ \text{6. Performance Incentive Match} \succ \text{7. Administrative Simplicity}$$

### Total Rewards TCO Formula ($TCO_{\text{rewards}}$)
For each employee node:

$$TCO_{\text{rewards}} = \text{Base Cash Salary} + \text{Target Variable Bonus} + \text{Annual Equity Vesting Value} + \text{Benefits Expense} + \text{Tech Tooling Subscription}$$

Where:
$$\text{Annual Equity Vesting Value} = \frac{\text{Granted Options} \times (\text{Preferred Share Fair Market Value} - \text{Strike Price})}{4 \text{ Years}}$$

### Option Pool Dilution Calculation
$$\text{Employee Ownership \%} = \frac{\text{Granted Option Shares}}{\text{Total Fully-Diluted Share Count}} \times 100\%$$

---

## 5. The 7-Step Operational Lifecycle Protocol

Alluci follows this operational sequence:

### Step 1 — Initiate Compensation Audit & Benchmarking
- Audit existing cash salaries and equity holdings across departments.
- Compare against empirical market benchmark percentiles (P50, P75, P90) for company stage.
- **Output:** Compensation Audit Report & Market Parity Index.

### Step 2 — Salary Band Standardization
- Structure standardized grade and level pay bands (e.g., L3 Junior, L4 Senior, L5 Staff, L6 Executive) per department.
- Define min, midpoint, and max salary thresholds per band.
- **Output:** Standardized Compensation Band Registry.

### Step 3 — Equity Incentive Pool Modeling
- Model option grant allocations for new hires, promotions, and retention refreshers.
- Calculate 4-year vesting schedules, 1-year cliff milestones, and strike price valuations (`ocs_01`).
- **Output:** Equity Option Grant Model & Option Pool Schedule.

### Step 4 — Total Rewards TCO Calculation
- Synthesize base cash, variable bonuses, health benefits, equity vesting values, and tech tooling costs per headcount.
- Integrate with `suf_01` (Use of Funds) and `swd_01` (Workforce Optimization).
- **Output:** Total Rewards TCO Financial Model.

### Step 5 — Request Compensation Plan Executive Approval
- Broadcast WebSocket request to leadership via `ExecApprovalManager` prior to issuing equity grants or modifying salary bands.
- *Rule: Alluci audits and models. Human leadership authorizes.*
- **Output:** Approved Compensation Strategy Log.

### Step 6 — Export Compensation Management Package
- Export `Compensation_Bands_Registry.csv`, `Equity_Option_Grant_Model.json`, `Total_Rewards_TCO_Dashboard.html`, `Comp_Benchmarking_Report.md`, and `Compensation_Manifest.json`.
- **Output:** Exported Compensation Package & Vault Archive.

### Step 7 — Continuous Parity & Benchmark Monitoring
- Register alert triggers in PCL daemon for market benchmark drift or budget variance ($> 10\%$).
- **Output:** Continuous Compensation Monitoring Loop.

---

## 6. Automation Boundaries & Human-in-the-Loop Protocol

### Tier 1: AI-Assisted Activities (Autonomous Audit & Modeling)
Alluci automatically handles:
- Benchmarking salary data against market percentile tables.
- Calculating total rewards TCO and option vesting schedules.
- Structuring draft salary bands (Min, Mid, Max) per department.
- Flagging pay disparities and unbenchmarked compensation.

### Tier 2: Human Approval Required (Mandatory Leadership Sign-Off)
Alluci MUST pause and request explicit executive sign-off for:
- Authorizing new equity option pool grants or cap table modifications.
- Approving salary band changes or company-wide pay raises.
- Approving executive compensation packages or severance agreements.
- Authorizing variable bonus plan payout structures.

### Tier 3: Autonomous Activities After Approval (System Synchronization)
Once executive sign-off is granted, Alluci automatically:
- Updates employee compensation records in vault memory.
- Refreshes financial runway and burn models in `suf_01`.
- Updates cap table option pool reserves in `ocs_01`.
- Archives approved compensation packages to vault deliverables.

---

## 7. Diagnostic & 30-Question Verification Checklist

### Failure Mode Diagnostic Rules
Alluci checks for and self-corrects:
- **Unbenchmarked Off-Band Hiring:** Offering compensation outside established salary bands without justification.
- **Cap Table Over-Granting:** Granting excessive equity percentages that deplete option pools prematurely.
- **Internal Pay Disparities:** Unexplained salary variations for identical roles and performance levels.
- **Budget Overruns:** Total rewards expenses exceeding `suf_01` gross burn limits.

### The 30-Question Completion Checklist
The workflow is complete ONLY when Alluci can answer all 30 questions:

#### Benchmarking & Band Design
- [ ] Base salaries and variable bonuses benchmarked against market P50/P75 data?
- [ ] Standardized pay bands (Min, Mid, Max) defined across all departments?
- [ ] Internal pay parity audited and verified across equal roles?
- [ ] Career progression levels (L3 to L6) clearly defined?

#### Equity & Option Pool Management
- [ ] Equity option grants modeled on a fully-diluted basis (`ocs_01`)?
- [ ] Standard 4-year vesting schedule with 1-year cliff enforced?
- [ ] Strike price and fair market valuation verified?
- [ ] Option pool reserve burn rate modeled against hiring plan (`swd_01`)?

#### Total Rewards TCO & Governance
- [ ] Total Rewards TCO ($TCO_{\text{rewards}}$) calculated per headcount?
- [ ] Compensation model integrated with `suf_01` capital allocation?
- [ ] Executive sign-off obtained via WebSocket prior to issuing grants or changing bands?
- [ ] Audit-ready Compensation Management package exported to vault?
