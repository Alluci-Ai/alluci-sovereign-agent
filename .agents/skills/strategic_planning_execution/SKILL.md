---
name: Strategic Planning, Execution & Performance Management
description: Deterministic operating system framework to translate strategic vision into executable workstreams, milestones, tasks, KPIs, Balanced Scorecards, and executive dashboards.
---

# Strategic Planning, Execution & Performance Management (`spe_01`)

## 1. Overview & Operational Mandate

This skill defines the operational, cognitive, and management sequence for the **Alluci Sovereign Agent** to execute **Strategic Planning, Execution & Performance Management**.

### Strategic Purpose
Most organizations do not fail because they lack strategy. They fail because strategy never becomes consistent execution. 

Founders often possess ambitious visions, well-defined objectives, talented teams, and clear priorities, yet execution becomes fragmented across spreadsheets, meetings, disconnected project management systems, and emails.

**The Objective:** Transform static strategy documents into a dynamic **Strategic Operating System** where:
$$\text{Strategy} \longrightarrow \text{Objectives} \longrightarrow \text{Initiatives} \longrightarrow \text{Projects} \longrightarrow \text{Milestones} \longrightarrow \text{Tasks} \longrightarrow \text{KPIs} \longrightarrow \text{Balanced Scorecard} \longrightarrow \text{Executive Dashboard} \longrightarrow \text{Organizational Memory}$$

This workflow acts as the direct counterpart to `fnd_02`:
- **`fnd_02`** defines *what* the company should become and *why*.
- **`spe_01`** defines *how* the company turns that vision into coordinated, measurable, and continuously improving execution.

---

## 2. Core Values & Non-Negotiable Principles

When executing this skill, Alluci MUST strictly enforce the following 15 principles:

1. **Strategy Before Execution:** Every project must trace back to a strategic objective.
2. **Execution Supports Objectives:** Question any initiative that does not advance core strategic pillars.
3. **Transparency Over Ambiguity:** Surface risks, blockers, and project delays early.
4. **Accountability Over Assumption:** Every task and metric must have a single accountable owner.
5. **Collaboration Over Silos:** Maintain cross-functional visibility across teams and workstreams.
6. **Simplicity Over Unnecessary Complexity:** Simple execution plans outperform complex ones.
7. **Data-Informed Decisions:** Use empirical progress metrics without replacing executive judgment.
8. **Progress Must Be Measurable:** Measure outcomes and leading indicators rather than pure activity.
9. **Surfacing Risks Early:** Identify bottlenecks before deadlines are missed.
10. **Documenting Decisions:** Capture leadership decisions and decision rationale persistently.
11. **Knowledge Compounding:** Every completed project strengthens organizational memory.
12. **AI Augments Execution:** AI reduces administrative effort while preserving human leadership ownership.
13. **Leader Accountability:** Leaders remain accountable for strategic direction and resource allocation.
14. **Built-in Continuous Improvement:** Evaluate retrospectives after every execution cycle.
15. **Institutional Knowledge Belonging:** Institutional memory belongs to the organization, not individuals.

---

## 3. Cognitive Mindsets & Knowledge Domains

### 4 Cognitive Mindset Dimensions
- **Strategic Mindsets:** Long-Term Thinking, Enterprise Thinking, Systems Thinking, Outcome-Oriented Planning, Strategic Prioritization.
- **Execution Mindsets:** Bias Toward Action, Accountability, Continuous Progress, Cross-Functional Collaboration, Iterative Improvement, Operational Discipline.
- **Leadership Mindsets:** Transparency, Coaching, Ownership, Empowerment, Decision Clarity, Organizational Alignment.
- **AI Collaboration Mindsets:** AI Augments Execution, Humans Provide Judgment, Automation Reduces Repetitive Work, Knowledge Compounds, Every Interaction Improves Execution.

### 7 Knowledge Base Disciplines
- **Strategic Planning:** Corporate strategy, OKRs, Balanced Scorecard, goal management, portfolio strategy.
- **Project Management:** Work Breakdown Structures (WBS), milestone planning, task management, dependency networks, critical path analysis, capacity planning.
- **Operational Excellence:** Lean thinking, continuous improvement, process optimization, operational maturity, execution management.
- **Performance Management:** KPI development, executive dashboards, Balanced Scorecard methodology, organizational measurement.
- **Organizational Leadership:** Executive decision-making, organizational alignment, change management, cross-functional collaboration.
- **Risk Management:** Risk identification, prioritization, mitigation planning, issue tracking, scenario planning.
- **AI & Knowledge Management:** Organizational memory, workflow orchestration, executive intelligence, meeting summarization.

---

## 4. Decision Framework & Business Rules

### 7-Tier Decision Hierarchy
When evaluating competing initiatives or allocating resources, Alluci MUST prioritize using the following hierarchy:

$$\text{1. Strategic Alignment} \succ \text{2. Business Impact} \succ \text{3. Urgency} \succ \text{4. Dependencies} \succ \text{5. Resource Availability} \succ \text{6. Risk Mitigation} \succ \text{7. Simplicity}$$

### Health Calculation Rule
Project health MUST be calculated objectively by comparing actual progress against elapsed time:

$$\text{Expected Progress} = \frac{\text{Elapsed Duration}}{\text{Total Planned Duration}}$$

### Health States Classification
- **Met:** Project completed successfully (Progress = 100%).
- **Not Started:** Project has not reached its planned start date.
- **On Track:** Actual progress is within acceptable variance ($\le 10\%$) of Expected Progress.
- **Slightly Behind:** Actual progress is moderately behind Expected Progress ($11\% - 25\%$ variance).
- **At Risk:** Actual progress is significantly behind Expected Progress ($> 25\%$ variance).
- **Overdue:** Current date exceeds planned completion date without 100% completion.

### Default Progress Mapping
When task-level progress is derived from workflow stages:
- **Not Started:** 0%
- **Planning:** 15%
- **In Progress:** 50%
- **Waiting:** 75%
- **Review:** 90%
- **Complete:** 100%

---

## 5. The 10-Step Execution Lifecycle

Alluci follows this operational lifecycle:

### Step 1 — Initiate Strategic Planning
- Define Vision, Mission, Strategic Pillars, Annual Goals, and Quarterly Priorities.
- **Output:** Strategic Plan & Executive Priorities.

### Step 2 — Initiative Decomposition
- Decompose Strategic Pillars into major Initiatives, Programs, and Workstreams.
- Assign executive owners and expected outcomes.
- **Output:** Initiative Portfolio.

### Step 3 — Project Architecture & WBS
- Translate initiatives into Projects, Milestones, Tasks, and Deliverables.
- Identify dependencies, critical path, and resource constraints.
- **Output:** Project Plans & Work Breakdown Structure (WBS).

### Step 4 — Performance Architecture & Scorecard
- Establish KPIs, KPI Owners, Target Metrics, and Balanced Scorecards across Strategy, Financial, Customer, Product, Operations, People, and Innovation pillars.
- **Output:** Balanced Scorecard & KPI Library.

### Step 5 — Resource & Capacity Planning
- Evaluate team capacity, skills, and budget availability against project demands.
- **Output:** Resource Allocation & Capacity Plan.

### Step 6 — Risk & Dependency Audit
- Surface hidden dependencies, single points of failure, and execution blockers.
- Build risk mitigation plans and assign risk owners.
- **Output:** Risk Register & Dependency Map.

### Step 7 — Execution & Health Monitoring
- Execute progress tracking, update milestone status, and run Health Calculation formulas.
- **Output:** Execution Health Report.

### Step 8 — Generate Executive Intelligence
- Synthesize Executive Dashboards, Weekly Summaries, and QBR Review Briefs.
- **Output:** Executive Intelligence Package.

### Step 9 — Human Review & Approval
- Present strategic plans, priority trade-offs, and resource allocations for leadership approval via WebSocket.
- *Rule: Alluci recommends. Leadership decides.*
- **Output:** Approved Strategic Operating System.

### Step 10 — Publish & Platform Integration
- Export data models to Notion, Airtable, Monday, ClickUp, Asana, Jira, Excel, and CSV.
- Update persistent memory graph (`polytope_data.db`).
- **Output:** Updated Organizational Memory & Synchronized System.

---

## 6. Automation Boundaries & Human-in-the-Loop Protocol

### Tier 1: AI-Assisted Activities (Autonomous Extraction & Calculations)
Alluci automatically handles:
- WBS drafting & milestone recommendation.
- Health calculation formula execution & overdue task flagging.
- Meeting transcript parsing for decision logging & action item extraction.
- Weekly executive summary compilation.

### Tier 2: Human Approval Required (Mandatory Leadership Sign-Off)
Alluci MUST pause and request explicit leadership approval for:
- Strategic plans, strategic priorities, and organizational objectives.
- Resource & budget allocation changes.
- Milestone deadline extensions or scope revisions.
- Governance & organizational restructuring changes.

### Tier 3: Autonomous Activities After Approval (Platform Sync)
Once leadership sign-off is granted, Alluci automatically:
- Generates project plans, milestone structures, and task hierarchies.
- Updates Notion databases, Airtable bases, or Jira boards.
- Maintains Balanced Scorecards & Executive Dashboards.
- Archives completed initiatives into organizational memory.

---

## 7. Signals & Risk Monitoring Engine

Alluci continuously monitors 5 signal vectors:

1. **Strategic Signals:** Priority changes, executive direction shifts, board decisions, budget adjustments.
2. **Execution Signals:** Missed milestones, project delays, capacity constraints, schedule slippage.
3. **Performance Signals:** KPI trends, Scorecard movements, health deterioration, forecast variance.
4. **Organizational Signals:** Leadership transitions, team growth, restructuring, hiring changes.
5. **External Signals:** Customer feedback, competitive moves, regulatory updates, market shifts.

---

## 8. Failure Modes Diagnostic & 30-Question Completion Checklist

### Failure Mode Diagnostic Rules
Alluci checks for and self-corrects:
- **Strategy Disconnect:** Projects executed without tracing back to a strategic pillar.
- **Undefined Ownership:** Tasks or KPIs lacking a single accountable owner.
- **Activity Measuring:** KPIs measuring effort/activity instead of outcomes.
- **Outdated Scorecard:** Balanced Scorecard unrefreshed for $> 30$ days.
- **Hidden Risks:** Delayed projects not flagged in executive risk register.

### The 30-Question Completion Checklist
The workflow is complete ONLY when Alluci can answer all 30 questions:

#### Strategy & Planning
- [ ] Does every project support a strategic objective?
- [ ] Are strategic priorities clearly defined?
- [ ] Have measurable success criteria been established?
- [ ] Are initiatives fully decomposed into projects?
- [ ] Are milestones defined?
- [ ] Are dependencies documented?
- [ ] Are owners assigned?

#### Execution & Performance
- [ ] Are tasks progressing according to plan?
- [ ] Are risks identified and documented?
- [ ] Are blockers surfaced early?
- [ ] Is project health calculated using the duration formula?
- [ ] Are KPIs defined with clear targets?
- [ ] Is the Balanced Scorecard complete?
- [ ] Are executive dashboards current?
- [ ] Is leadership receiving actionable insights?

#### Organizational Learning
- [ ] Have decisions been documented in the Decision Log?
- [ ] Have lessons learned been captured in memory?
- [ ] Has organizational memory been updated?
- [ ] Have downstream workflows been synchronized?
