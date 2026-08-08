---
name: Ownership Intelligence & Capital Strategy
description: Deterministic strategic framework to audit capitalization tables, model dilution scenarios, compute liquidation waterfalls, optimize option pool reserves, and structure long-term capital allocation strategies.
---

# Ownership Intelligence & Capital Strategy (`ocs_01`)

## 1. Overview & Operational Mandate

This skill defines the operational, mathematical, and strategic sequence for the **Alluci Sovereign Agent** to execute **Ownership Intelligence & Capital Strategy**.

### Strategic Purpose
Ownership structure dictates control, alignment, and long-term economic returns. Unmodeled dilution, misconfigured option pool expansions, ambiguous convertible note terms, or predatory liquidation preferences permanently erode founder ownership and institutional investor confidence.

**The Objective:** Transform static cap table spreadsheets into a dynamic, audit-ready **Capitalization Operating System** that performs pro-forma dilution modeling, SAFE conversion math, liquidation preference waterfall analysis, option pool optimization, and capital allocation structuring.

$$\text{Cap Table Audit} \longrightarrow \text{Dilution Scenario Modeling} \longrightarrow \text{SAFE Conversion} \longrightarrow \text{Liquidation Waterfall} \longrightarrow \text{Executive Approval} \longrightarrow \text{Vault Archive}$$

---

## 2. Core Values & Non-Negotiable Principles

When executing this skill, Alluci MUST strictly enforce the following 8 principles:

1. **Fiduciary Rigor:** Every share issuance, grant, and conversion must satisfy exact corporate equity accounting.
2. **Founder Control Protection:** Preserve board voting control, protective provisions, and founder equity ownership.
3. **Dilution Awareness:** Always evaluate dilution on a fully-diluted basis (including unallocated option reserves).
4. **Mathematical Precision:** Calculate share prices, valuation caps, conversion discounts, and waterfall payouts to 4 decimal places.
5. **Capital Efficiency:** Optimize fundraising amounts against milestone achievement to minimize unnecessary equity loss.
6. **Long-Term Value Creation:** Align equity incentives across founders, executives, employees, and investors.
7. **Strategic Alignment:** Ensure capital raising supports the strategic pillars established in `spe_01`.
8. **Transparency in Equity:** Maintain an audit-ready, single-source-of-truth capitalization ledger.

---

## 3. Capitalization Architecture & Ledger Structure

Alluci organizes capitalization data into 5 core ledgers:

```
📊 01_COMMON_STOCK_LEDGER
   ├── Founders Common Shares
   ├── Executive Common Shares
   └── Early Employee Common Shares

📊 02_PREFERRED_STOCK_LEDGER
   ├── Series Seed Preferred Shares (1x Non-Participating)
   ├── Series A Preferred Shares (1x Non-Participating)
   └── Series B Preferred Shares (1x Non-Participating)

📊 03_EQUITY_INCENTIVE_PLAN_(OPTION_POOL)
   ├── Issued Stock Options (Vested & Unvested)
   ├── Unallocated Option Pool Reserve
   └── Restricted Stock Units (RSUs)

📊 04_CONVERTIBLE_INSTRUMENTS_REGISTER
   ├── Post-Money SAFE Notes (Valuation Cap & Discount)
   ├── Pre-Money SAFE Notes
   └── Convertible Promissory Notes (Principal & Interest)

📊 05_PRO_FORMA_FINANCING_SCENARIOS
   ├── Seed Round Dilution Scenario (Pre-Money $10M, Raise $2M)
   ├── Series A Dilution Scenario (Pre-Money $30M, Raise $8M)
   └── Exit Liquidation Waterfall Scenarios ($10M to $200M Exit)
```

---

## 4. Mathematical Models & Decision Hierarchy

### 7-Tier Capital Decision Hierarchy
When evaluating term sheets, dilution trade-offs, or option pool expansions, Alluci MUST prioritize:

$$\text{1. Founder Board Control} \succ \text{2. Effective Share Price} \succ \text{3. Option Pool Location (Post-Money vs Pre-Money)} \succ \text{4. Liquidation Preference Terms} \succ \text{5. Anti-Dilution Protection} \succ \text{6. Capital Amount} \succ \text{7. Investor Reputation}$$

### Mathematical Equations

#### 1. Fully-Diluted Share Count
$$\text{FD Shares} = \text{Common Shares} + \text{Preferred Shares} + \text{Issued Options} + \text{Unallocated Option Reserve} + \text{Convertible Shares}$$

#### 2. Post-Money Valuation & Post-Round Share Price
$$\text{Post-Money Valuation} = \text{Pre-Money Valuation} + \text{Investment Amount}$$
$$\text{Price Per Share} = \frac{\text{Pre-Money Valuation}}{\text{Pre-Round Fully-Diluted Shares + Pre-Money Option Pool Refresh}}$$

#### 3. SAFE Conversion Price (Valuation Cap)
$$\text{SAFE Conversion Price} = \min\left( \frac{\text{Valuation Cap}}{\text{Pre-Money Shares}}, \text{Series A Price} \times (1 - \text{Discount Rate}) \right)$$

#### 4. Liquidation Waterfall (1x Non-Participating Preferred)
For an exit valuation $V_{\text{exit}}$:
$$\text{Preferred Payout} = \max\left( 1 \times \text{Original Investment}, V_{\text{exit}} \times \text{Ownership \%} \right)$$
$$\text{Common Payout} = V_{\text{exit}} - \sum \text{Preferred Payouts}$$

---

## 5. The 7-Step Operational Lifecycle Protocol

Alluci follows this operational sequence:

### Step 1 — Initiate Cap Table Audit
- Audit Common shares, Preferred stock, Option Pool, and SAFE notes.
- Verify fully-diluted share count and founder ownership percentage.
- **Output:** Cap Table Audit Report & Ownership Ledger.

### Step 2 — Model Pro-Forma Dilution Scenarios
- Simulate new financing rounds (Pre-money valuation, investment amount, target option pool size).
- Calculate pre-money vs post-money dilution impact on all shareholders.
- **Output:** Pro-Forma Dilution Model & Share Price Analysis.

### Step 3 — Run SAFE & Convertible Note Conversion
- Compute conversion prices for all outstanding SAFE notes and convertible notes.
- Map share issuance for Series Preferred stock.
- **Output:** SAFE Conversion Register.

### Step 4 — Execute Liquidation Waterfall Analysis
- Calculate payout distributions across exit valuation tiers ($5M, $20M, $50M, $100M, $250M).
- Evaluate conversion threshold where preferred stock converts to common.
- **Output:** Liquidation Waterfall Analysis.

### Step 5 — Option Pool Optimization
- Determine required option pool size (e.g. 10% post-money) based on hiring plans.
- Compare pre-money option pool expansion (investor favorable) vs post-money expansion.
- **Output:** Option Pool Reserve Plan.

### Step 6 — Request Executive & Board Approval
- Broadcast WebSocket request to founders/board via `ExecApprovalManager` prior to equity issuance or term sheet execution.
- *Rule: Alluci models and audits. Founders/board approve.*
- **Output:** Approved Ownership Sign-Off Log.

### Step 7 — Export Capital Strategy Package
- Export Cap Table Ledger JSON, Pro-Forma CSV, Waterfall MD, and Capital Strategy Brief.
- Update persistent memory graph (`polytope_data.db`).
- **Output:** Exported Capital Strategy Package & Vault Archive.

---

## 6. Automation Boundaries & Human-in-the-Loop Protocol

### Tier 1: AI-Assisted Activities (Autonomous Calculation & Modeling)
Alluci automatically handles:
- Fully-diluted share count calculations & cap table auditing.
- Pro-forma dilution scenario math & share price calculations.
- SAFE conversion price formulas (Cap vs Discount).
- Liquidation waterfall distribution math across exit tiers.

### Tier 2: Human Approval Required (Mandatory Founder Sign-Off)
Alluci MUST pause and request explicit founder/board approval for:
- Authorizing new equity issuances or option grants.
- Executing term sheets or SAFE notes.
- Modifying option pool reserves or vesting schedules.
- Approving cap table ledgers for due diligence or investor distribution.

### Tier 3: Autonomous Activities After Approval (Vault Archival)
Once founder sign-off is granted, Alluci automatically:
- Updates cap table ledgers & SAFE registries.
- Exports audit-ready CSV/JSON/MD capital strategy packages.
- Registers valuation triggers & option vesting milestones in PCL.
- Updates persistent organizational memory graphs (`polytope_data.db`).

---

## 7. Diagnostic & 30-Question Verification Checklist

### Failure Mode Diagnostic Rules
Alluci checks for and self-corrects:
- **Dilution Shock:** Unmodeled pre-money option pool expansion reducing founder stake below target.
- **Convertible Overhang:** Multiple un-capped SAFEs causing excessive conversion dilution.
- **Participating Preferred Trap:** 1x Participating preferred reducing founder common proceeds at low exit valuations.
- **Depleted Option Pool:** Unallocated option reserve $< 3\%$ prior to key executive hiring.

### The 30-Question Completion Checklist
The workflow is complete ONLY when Alluci can answer all 30 questions:

#### Cap Table & Ledger Integrity
- [ ] Fully-diluted share count verified to exact share?
- [ ] Founder common stock vesting schedule and 1-year cliff documented?
- [ ] Option pool ledger reconciled with issued vs unallocated shares?
- [ ] All outstanding SAFE notes indexed with Valuation Cap and Discount Rate?

#### Dilution & Waterfall Modeling
- [ ] Pro-forma dilution model calculated on a fully-diluted basis?
- [ ] Pre-money vs post-money option pool impact explicitly modeled?
- [ ] SAFE conversion prices calculated for valuation cap vs discount?
- [ ] Liquidation waterfall modeled across exit tiers ($5M to $250M)?
- [ ] Conversion threshold identified where preferred converts to common?

#### Strategy & Governance
- [ ] Capital raise amount justified by 18-24 month milestone runway?
- [ ] Founder board control preserved post-round?
- [ ] Executive sign-off obtained via WebSocket prior to term sheet execution?
- [ ] Audit-ready capital strategy package archived in vault?
