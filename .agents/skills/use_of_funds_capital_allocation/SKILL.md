---
name: Strategic Use of Funds & Capital Allocation Management
description: Deterministic strategic framework to monitor, audit, report, validate, and verify capital allocation, gross/net burn rates, runway trajectory, and investor covenant compliance.
---

# Strategic Use of Funds & Capital Allocation Management (`suf_01`)

## 1. Overview & Operational Mandate

This skill defines the operational, mathematical, and fiduciary sequence for the **Alluci Sovereign Agent** to execute **Strategic Use of Funds & Capital Allocation Management**.

### Strategic Purpose
Capital is the fuel that powers corporate strategy. Unmonitored burn rates, unauthorized budget reallocations, unexpected cost overruns, or covenant breaches deplete runway prematurely and destroy investor confidence.

**The Objective:** Transform static financial projections into a dynamic **Capital Allocation & Runway Operating System** that continuously monitors, audits, reports, validates, and verifies capital deployment, gross/net burn rates, runway months, and investor covenant compliance.

$$\text{Capital Deployment} \longrightarrow \text{Burn & Runway Calculation} \longrightarrow \text{Variance Audit} \longrightarrow \text{Covenant Verification} \longrightarrow \text{Executive Approval} \longrightarrow \text{Vault Archive}$$

---

## 2. Core Values & Non-Negotiable Principles

When executing this skill, Alluci MUST strictly enforce the following 8 principles:

1. **Fiduciary Stewardship:** Manage capital deployment with extreme financial discipline and transparency.
2. **Capital Efficiency:** Maximize milestone progress per dollar of capital burned.
3. **Runway Maximization:** Proactively extend runway by monitoring net burn rates and eliminating unaligned expenses.
4. **Variance Vigilance:** Audit budget vs actuals monthly; flag any category variance exceeding 15%.
5. **Covenant Compliance:** Ensure capital deployment strictly adheres to pitch deck commitments and investor term sheet covenants.
6. **Milestone-Oriented Spending:** Connect every capital expenditure directly to strategic initiatives (`spe_01`).
7. **Data-Driven Allocation:** Base resource allocation on empirical performance metrics and ROI.
8. **Transparency in Reporting:** Provide clear, audit-ready financial dashboards to executives and board members.

---

## 3. Capital Allocation Taxonomy & Allocation Buckets

Alluci organizes capital allocation into 4 standard strategic buckets:

```
💰 01_PRODUCT_AND_ENGINEERING (R&D) / Target Allocation: 35% - 45%
   ├── Core AI & System Engineering
   ├── Infrastructure & Cloud Computing Costs
   ├── Technical Product Management
   └── Security & Compliance Audits (SOC2)

💰 02_GO_TO_MARKET_AND_GROWTH (GTM) / Target Allocation: 30% - 40%
   ├── Sales & Business Development Team
   ├── Performance Marketing & Brand
   ├── Customer Success & Onboarding
   └── Channel & Strategic Partnerships

💰 03_OPERATIONS_AND_GOVERNANCE (G&A) / Target Allocation: 10% - 20%
   ├── Executive Leadership & HR
   ├── Legal, Corporate Governance & IP
   ├── Finance, Accounting & Tax Compliance
   └── Software Tools & Operating Overhead

💰 04_CAPITAL_RESERVE_AND_CONTINGENCY / Target Allocation: 10% - 15%
   ├── Strategic Cash Reserve Buffer
   └── Emergency Contingency Fund
```

---

## 4. Mathematical Formulations & Decision Hierarchy

### 7-Tier Capital Allocation Decision Hierarchy
When evaluating budget reallocations or expense requests, Alluci MUST prioritize:

$$\text{1. Runway Preservation ($\ge 12$ Mos)} \succ \text{2. Core Product R&D} \succ \text{3. Revenue-Generating GTM} \succ \text{4. Legal & Regulatory Compliance} \succ \text{5. Operational Overhead} \succ \text{6. Non-Essential Software} \succ \text{7. Unbudgeted Experiments}$$

### Key Financial Calculations

#### 1. Gross Burn Rate
$$\text{Gross Burn Rate} = \sum \text{Total Monthly Operating Cash Expenditures}$$

#### 2. Net Burn Rate
$$\text{Net Burn Rate} = \text{Gross Burn Rate} - \text{Recognized Monthly Cash Receipts}$$

#### 3. Runway Months
$$\text{Runway (Months)} = \frac{\text{Current Cash & Cash Equivalents}}{\text{Net Monthly Burn Rate}}$$

#### 4. Zero Cash Date (ZCD)
$$\text{Zero Cash Date} = \text{Current Date} + \text{Runway (Months)}$$

#### 5. Category Budget Variance (%)
$$\text{Budget Variance \%} = \frac{\text{Actual Spending} - \text{Budgeted Allocation}}{\text{Budgeted Allocation}} \times 100.0$$

#### 6. Milestone Runway Efficiency Score
$$\text{Milestone Runway Efficiency} = \frac{\text{Milestones Completed}}{\text{Capital Burned (\$M)}}$$

---

## 5. The 7-Step Operational Lifecycle Protocol

Alluci follows this operational sequence:

### Step 1 — Initiate Capital Allocation Audit
- Audit cash balance, monthly gross burn, monthly cash receipts, and net burn.
- Categorize spending across R&D, GTM, G&A, and Reserve buckets.
- **Output:** Capital Allocation Audit Report.

### Step 2 — Compute Burn Rate & Runway Trajectory
- Calculate Gross Burn Rate, Net Burn Rate, Runway Months, and Zero Cash Date.
- Evaluate Runway Health Status:
  - **Healthy:** Runway $\ge 12$ months.
  - **Caution:** Runway $6 - 11$ months.
  - **Critical Alert:** Runway $< 6$ months.
- **Output:** Runway & Burn Trajectory Analysis.

### Step 3 — Run Budget vs Actual Variance Audit
- Compare actual expenditures against budgeted baseline across all strategic categories.
- Flag any variance exceeding $+15\%$.
- **Output:** Variance Analysis Report & Flagged Cost Overruns.

### Step 4 — Verify Investor Covenant & Plan Compliance
- Verify spending against investor pitch deck representations and term sheet covenants.
- Audit unauthorized reallocations or unbudgeted capital expenditures.
- **Output:** Investor Covenant Compliance Certification.

### Step 5 — Request Reallocation Approval
- Broadcast WebSocket request via `ExecApprovalManager` prior to approving category budget shifts $> 15\%$.
- *Rule: Alluci audits and calculates. Founders/board authorize.*
- **Output:** Approved Budget Reallocation Log.

### Step 6 — Export Capital Allocation Package
- Generate `Use_Of_Funds_Audit_Report.json`, `Runway_And_Burn_Model.csv`, `Capital_Allocation_Dashboard.html`, `Covenant_Compliance_Verification.md`, and `Capital_Allocation_Manifest.json`.
- **Output:** Exported Capital Allocation Package & Vault Archive.

### Step 7 — Continuous Runway Monitoring
- Register runway threshold alerts ($< 6$ months) and net burn escalation triggers in the PCL monitoring daemon.
- **Output:** Continuous Financial Monitoring Active.

---

## 6. Automation Boundaries & Human-in-the-Loop Protocol

### Tier 1: AI-Assisted Activities (Autonomous Audit & Math)
Alluci automatically handles:
- Gross burn, net burn, runway months, and Zero Cash Date calculations.
- Budget vs actual variance calculation & $+15\%$ breach detection.
- Pitch deck vs actual capital allocation comparison.
- Financial dashboard HTML and CSV model generation.

### Tier 2: Human Approval Required (Mandatory Leadership Sign-Off)
Alluci MUST pause and request explicit executive/board approval for:
- Reallocating $> 15\%$ of budget between strategic categories.
- Authorizing unbudgeted capital expenditures $> \$10,000$.
- Modifying cash reserve buffers or emergency funds.
- Approving official Use of Funds reports for investor data rooms or board meetings.

### Tier 3: Autonomous Activities After Approval (Vault Archival)
Once executive sign-off is granted, Alluci automatically:
- Updates financial ledgers & allocation models.
- Exports audit-ready CSV/JSON/HTML/MD packages.
- Registers updated Zero Cash Date alerts in PCL daemon.
- Updates persistent organizational memory graphs (`polytope_data.db`).

---

## 7. Diagnostic & 30-Question Verification Checklist

### Failure Mode Diagnostic Rules
Alluci checks for and self-corrects:
- **Runway Illusion:** Calculating runway using gross burn instead of net burn (or over-optimistic revenue projections).
- **Creeping Reallocation:** Unnoticed shift of R&D funds into G&A overhead.
- **Covenant Default:** Spending $> 20\%$ off pitch deck plan without investor notification.
- **Silent Cash Drain:** Unallocated software subscriptions causing cumulative burn escalation.

### The 30-Question Completion Checklist
The workflow is complete ONLY when Alluci can answer all 30 questions:

#### Financial Math & Runway
- [ ] Current Cash Balance verified against bank records?
- [ ] Gross Monthly Burn Rate calculated accurately?
- [ ] Net Monthly Burn Rate calculated accurately?
- [ ] Runway Months calculated ($\text{Cash} / \text{Net Burn}$)?
- [ ] Zero Cash Date explicitly identified?
- [ ] Runway Status confirmed (Healthy $\ge 12$ mos, Caution $6-11$ mos, Critical $< 6$ mos)?

#### Allocation & Variance Audit
- [ ] Spending categorized into R&D, GTM, G&A, and Reserve buckets?
- [ ] Budget vs Actual variance calculated per category?
- [ ] All variances $> 15\%$ flagged and investigated?
- [ ] Unbudgeted expenses identified and audited?

#### Compliance & Reporting
- [ ] Use of Funds reconciled with pitch deck commitments?
- [ ] Term sheet financial covenants verified?
- [ ] Milestone Runway Efficiency Score computed?
- [ ] Executive sign-off obtained via WebSocket for major reallocations?
- [ ] Audit-ready Capital Allocation package archived in vault?
