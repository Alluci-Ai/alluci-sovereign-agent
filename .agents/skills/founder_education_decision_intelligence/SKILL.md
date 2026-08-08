---
name: Founder Education & Decision Intelligence
description: Deterministic strategic framework to synthesize founder learning modules, evaluate decision confidence scores, log structured decision journals, apply mental models, and accelerate executive decision mastery.
---

# Founder Education & Decision Intelligence (`fde_01`)

## 1. Overview & Operational Mandate

This skill defines the operational, cognitive, and educational sequence for the **Alluci Sovereign Agent** to execute **Founder Education & Decision Intelligence**.

### Strategic Purpose
Founders and executive leaders are continuously required to make high-stakes, irreversible decisions under condition of extreme uncertainty. Traditional executive decision-making relies heavily on unexamined intuition, informal advice, or ad-hoc spreadsheets, leading to cognitive biases, unanalyzed trade-offs, forgotten decision rationale, and repeated strategic mistakes.

**The Objective:** Transform fragmented founder intuition into a systematic **Executive Decision Intelligence Engine** that synthesizes just-in-time executive learning briefs, applies mental models, computes mathematical Decision Confidence Scores, logs decision journal entries, and continuously audits decision outcomes.

$$\text{Learning Need} \longrightarrow \text{Mental Model Synthesis} \longrightarrow \text{Confidence Evaluation} \longrightarrow \text{Decision Journaling} \longrightarrow \text{Executive Approval} \longrightarrow \text{Vault Archive}$$

---

## 2. Core Values & Non-Negotiable Principles

When executing this skill, Alluci MUST strictly enforce the following 8 principles:

1. **First Principles Clarity:** Deconstruct complex business problems to fundamental truths before reasoning by analogy.
2. **Second-Order Awareness:** Always evaluate "And then what?"—modeling second and third-order consequences of major decisions.
3. **Evidence-Based Intelligence:** Ground recommendations in empirical organizational evidence (`okd_01`), financial data (`suf_01`), and market research (`fnd_02`).
4. **Continuous Executive Learning:** Provide just-in-time, action-oriented executive briefs tailored to active strategic challenges.
5. **Mental Model Rigor:** Apply established mental models (First Principles, Inversion, Opportunity Cost, Margin of Safety, Pareto Principle) to eliminate cognitive bias.
6. **Decision Journal Transparency:** Document every major strategic decision with options considered, expected outcomes, and review triggers.
7. **Risk-Adjusted Decision Making:** Explicitly evaluate down-side risks, failure modes, and mitigation strategies.
8. **Long-Term Enterprise Stewardship:** Prioritize decisions that build enduring organizational value over short-term expediency.

---

## 3. The 7 Core Founder Mental Models Architecture

Alluci integrates 7 fundamental mental models into every executive decision workflow:

```
🧠 MENTAL MODEL 1: FIRST PRINCIPLES THINKING
   └── Boil a problem down to fundamental truths. Rebuild strategy from scratch without legacy assumptions.

🧠 MENTAL MODEL 2: SECOND-ORDER THINKING
   └── Ask "And then what?". Evaluate long-term secondary consequences beyond immediate first-order effects.

🧠 MENTAL MODEL 3: INVERSION (REVERSE THINKING)
   └── Instead of "How do we succeed?", ask "How could this project fail catastrophically?" and systematically eliminate failure points.

🧠 MENTAL MODEL 4: OPPORTUNITY COST & MARGINAL VALUE
   └── Evaluate what is given up by selecting Option A over Option B ($TCO$, capital allocation, human bandwidth).

🧠 MENTAL MODEL 5: MARGIN OF SAFETY
   └── Build buffer into runway projections ($suf_01$), project timelines ($spe_01$), and capacity planning ($swd_01$).

🧠 MENTAL MODEL 6: CONWAY'S LAW & TEAM TOPOLOGIES
   └── Align organizational structures ($swd_01$) with desired architecture and product outcomes.

🧠 MENTAL MODEL 7: PARETO PRINCIPLE (80/20 RULE)
   └── Identify the 20% of strategic initiatives that generate 80% of enterprise value and growth.
```

---

## 4. Mathematical Models & Decision Confidence Scoring

### 7-Tier Decision Intelligence Hierarchy
When synthesizing executive guidance or scoring options, Alluci MUST prioritize:

$$\text{1. Strategic Alignment} \succ \text{2. Evidence Quality \& Rigor} \succ \text{3. Financial Runway Sustainability (suf\_01)} \succ \text{4. Risk-Adjusted Outcome} \succ \text{5. Second-Order Impact} \succ \text{6. Reversibility (Type 1 vs Type 2)} \succ \text{7. Execution Speed}$$

### Multi-Factor Decision Confidence Score ($DCS$)
Alluci evaluates every proposed decision across 4 weighted factors (0-100%):

$$DCS = (W_{\text{evidence}} \times S_{\text{evidence}}) + (W_{\text{alignment}} \times S_{\text{alignment}}) + (W_{\text{risk}} \times S_{\text{risk}}) + (W_{\text{outcomes}} \times S_{\text{outcomes}})$$

Where:
- $W_{\text{evidence}} = 0.35$ (Quality and empirical verification of organizational data)
- $W_{\text{alignment}} = 0.25$ (Strategic objective alignment from `spe_01`)
- $W_{\text{risk}} = 0.25$ (Downside mitigation & margin of safety)
- $W_{\text{outcomes}} = 0.15$ (Agreement across historical scenario modeling)

#### Decision Threshold Rules:
- **$DCS \ge 80\%$ (High Confidence):** Authorize execution immediately.
- **$60\% \le DCS < 80\%$ (Moderate Confidence):** Surface key assumptions and require executive review.
- **$DCS < 60\%$ (Low Confidence):** Request additional evidence collection or pilot validation prior to execution.

---

## 5. The 7-Step Operational Lifecycle Protocol

Alluci follows this operational sequence:

### Step 1 — Strategic Bottleneck & Learning Discovery
- Identify active strategic decisions, friction points, or growth bottlenecks across `spe_01`, `suf_01`, `ocs_01`, or `swd_01`.
- **Output:** Founder Learning Need Register.

### Step 2 — Executive Learning Brief Synthesis
- Synthesize a concise, 1-page executive learning module covering core concepts, real-world case studies, trade-off matrices, and key questions.
- **Output:** Founder Executive Curriculum Module.

### Step 3 — Mental Model & Scenario Application
- Apply First Principles, Inversion, and Opportunity Cost models to the specific decision scenario.
- **Output:** Mental Model Trade-Off Matrix.

### Step 4 — Multi-Factor Decision Confidence Scoring
- Calculate the Decision Confidence Score ($DCS$, 0-100%) and document underlying assumptions.
- **Output:** Decision Confidence Evaluation Report.

### Step 5 — Executive Decision Journal Logging
- Create a structured entry in the Decision Journal Ledger (`Decision`, `Rationale`, `Alternatives Considered`, `Expected Outcome`, `Review Date`).
- **Output:** Logged Decision Journal Entry.

### Step 6 — Request Executive Decision Sign-Off
- Broadcast WebSocket request to leadership via `ExecApprovalManager` prior to authorizing major strategic decisions.
- *Rule: Alluci educates, scores, and logs. Human founder authorizes.*
- **Output:** Approved Decision Sign-Off Record.

### Step 7 — Export Education & Decision Package
- Export `Founder_Executive_Curriculum.json`, `Decision_Journal_Ledger.csv`, `Mental_Models_Dashboard.html`, `Decision_Confidence_Report.md`, and `Education_Manifest.json`.
- **Output:** Exported Education Package & Vault Archive.

---

## 6. Automation Boundaries & Human-in-the-Loop Protocol

### Tier 1: AI-Assisted Activities (Autonomous Synthesis & Math)
Alluci automatically handles:
- Executive learning brief synthesis & mental model framing.
- Decision Confidence Score ($DCS$) calculation & assumption tracking.
- Scenario trade-off modeling (Option A vs Option B vs Option C).
- Decision journal template generation & historical decision retrieval.

### Tier 2: Human Approval Required (Mandatory Founder Sign-Off)
Alluci MUST pause and request explicit founder sign-off for:
- Authorizing Type 1 irreversible strategic decisions (e.g. M&A, major pivot, debt financing).
- Finalizing annual executive decision targets and strategic priorities (`spe_01`).
- Overriding low-confidence decision warnings ($DCS < 60\%$).

### Tier 3: Autonomous Activities After Approval (System Synchronization)
Once founder sign-off is granted, Alluci automatically:
- Archives approved decision journal entries in vault memory.
- Registers review triggers in PCL daemon (e.g., 90-day post-decision audit).
- Updates persistent Organizational Memory (`okd_01`).
- Synchronizes downstream workflows (`spe_01`, `suf_01`, `swd_01`).

---

## 7. Diagnostic & 30-Question Verification Checklist

### Failure Mode Diagnostic Rules
Alluci checks for and self-corrects:
- **Raw Intuition Bias:** Making strategic commitments without logging alternatives or trade-offs.
- **Confirmation Bias:** Selectively citing evidence while ignoring contradictory organizational data.
- **Type 1 / Type 2 Confusion:** Treating reversible operational choices with slow, irreversible bureaucratic processes.
- **Unreviewed Decisions:** Failing to audit decision outcomes against original journal hypotheses.

### The 30-Question Completion Checklist
The workflow is complete ONLY when Alluci can answer all 30 questions:

#### Education & Mental Models
- [ ] Strategic bottleneck identified and mapped to executive learning domain?
- [ ] Executive learning module synthesized with case studies and heuristics?
- [ ] First Principles and Inversion mental models applied?
- [ ] Opportunity costs ($TCO$, capital, bandwidth) explicitly evaluated?

#### Confidence & Decision Journaling
- [ ] Multi-factor Decision Confidence Score ($DCS$) computed (0-100%)?
- [ ] Key assumptions and failure modes documented?
- [ ] Decision journal entry logged (Options, Rationale, Expected Outcome, Review Trigger)?
- [ ] Type 1 (irreversible) vs Type 2 (reversible) classification assigned?

#### Governance & Continuous Intelligence
- [ ] Executive sign-off obtained via WebSocket prior to major commitments?
- [ ] Review triggers registered in PCL daemon for 90-day post-decision audit?
- [ ] Audit-ready Education & Decision Intelligence package exported to vault?
