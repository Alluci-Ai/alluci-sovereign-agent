---
name: Organizational Knowledge & Document Management
description: Deterministic strategic framework to structure, index, version, audit, and retrieve organizational memory, knowledge graph assets, standardized document taxonomies, and cross-workflow intelligence.
---

# Organizational Knowledge & Document Management (`okd_01`)

## 1. Overview & Operational Mandate

This skill defines the operational, cognitive, and architectural sequence for the **Alluci Sovereign Agent** to execute **Organizational Knowledge & Document Management**.

### Strategic Purpose
Institutional knowledge is an organization's most valuable strategic asset. Fragmented files, undocumented decisions, unindexed repositories, conflicting document versions, and knowledge silos cripple operational efficiency, destroy enterprise value, and disrupt investor due diligence.

**The Objective:** Transform scattered corporate documents into a unified, self-healing **Organizational Knowledge System** that indexes, versions, audits, protects, and retrieves institutional memory across all workflows.

$$\text{Knowledge Audit} \longrightarrow \text{Taxonomy \& Metadata Tagging} \longrightarrow \text{Single Source Resolution} \longrightarrow \text{Graph Indexing} \longrightarrow \text{Executive Approval} \longrightarrow \text{Memory Storage}$$

---

## 2. Core Values & Non-Negotiable Principles

When executing this skill, Alluci MUST strictly enforce the following 8 principles:

1. **Single Source of Truth:** Every published document must have one designated owner, one approved version, and one authoritative location.
2. **Institutional Memory Preservation:** Capture decision rationale, meeting intelligence, and historical context permanently.
3. **Knowledge Compounding:** Ensure every executed project (`spe_01`), diligence event (`ir_01`), and contract (`ldl_01`) enriches the organizational knowledge base.
4. **Audit Readiness:** Maintain audit-ready document registries, version histories, and confidentiality tags.
5. **Zero Knowledge Silos:** Enable seamless cross-departmental information discovery while maintaining security.
6. **Metadata Rigor:** Enforce strict metadata tags (Owner, Version, Date, Category, Confidentiality Level, Dependencies).
7. **Confidentiality Protection:** Enforce access policies (`Public`, `Restricted`, `Strictly Confidential`).
8. **Continuous Learning:** Monitor document freshness; flag stale assets ($> 90$ days unreviewed).

---

## 3. The 6-Layer Organizational Memory Architecture

Alluci structures institutional memory into 6 interconnected layers:

```
🧠 LAYER 1: STRATEGIC MEMORY
   ├── Vision, Mission, Strategic Pillars & Annual Objectives (from spe_01)
   ├── Market Thesis, Category Definition & Contrarian Beliefs (from fnd_02)
   └── Executive Decision Logs & Board Resolutions

🧠 LAYER 2: OPERATIONAL MEMORY
   ├── Project Plans, Work Breakdown Structures (WBS) & Milestones (from spe_01)
   ├── Standard Operating Procedures (SOPs) & Process Maps
   └── Team Structures, Role Descriptions & Capability Maps (from swd_01)

🧠 LAYER 3: LEGAL & GOVERNANCE MEMORY
   ├── Certificate of Incorporation, Bylaws & Board Minutes (from ldl_01)
   ├── IP Registrations, Patents & PIIA Agreements
   └── Executed Commercial Contracts & Material Agreements

🧠 LAYER 4: FINANCIAL & CAPITAL MEMORY
   ├── Capitalization Table Ledgers & Dilution Scenarios (from ocs_01)
   ├── Financial Models, Budgets & Use of Funds Audits (from suf_01)
   └── Investor Pitch Decks, Data Room Manifests & Investor Guides (from ir_01)

🧠 LAYER 5: PRODUCT & TECHNICAL MEMORY
   ├── Technical Architecture Specs & API Schemas
   ├── Product Roadmaps, Feature Specs & Security Auditing (SOC2)
   └── Codebase Documentation & Architecture Impact Analysis

🧠 LAYER 6: AI AGENT & AUTOMATION MEMORY
   ├── Active AI Agent Rosters, Prompt System Instructions & Tools
   ├── Token Usage History, Model Selection Rules & Cost Logs
   └── Vector Embeddings & Graph Traversal Nodes (polytope_data.db)
```

---

## 4. Decision Framework & Naming Conventions

### 7-Tier Knowledge Decision Hierarchy
When resolving conflicts, indexing files, or structuring memory objects, Alluci MUST prioritize:

$$\text{1. Single Source of Truth Integrity} \succ \text{2. Security \& Confidentiality} \succ \text{3. Legal \& Governance Authority} \succ \text{4. Metadata Completeness} \succ \text{5. Retrieval Speed} \succ \text{6. Cross-Workflow Linkage} \succ \text{7. Storage Efficiency}$$

### Standardized Document Naming Conventions
Alluci enforces strict document naming formats across all categories:

$$\text{[CategoryCode]\_[\text{DocType}]\_[\text{Owner/Counterparty}]\_[\text{YYYYMMDD}]\_v[\text{Major}.\text{Minor}].\text{ext}}$$

#### Examples:
- `LEGAL_PIIA_JohnDoe_20260808_v1.0.pdf`
- `FINANCE_UseOfFunds_Q3Audit_20260808_v2.1.json`
- `STRATEGY_OperatingPlan_Executive_20260808_v1.0.md`
- `DATAROOM_DocSendSpec_DiligenceCo_20260808_v1.0.json`

---

## 5. The 7-Step Operational Lifecycle Protocol

Alluci follows this operational sequence:

### Step 1 — Initiate Knowledge Repository Audit
- Audit existing documents across all 6 memory layers.
- Check document freshness, missing metadata, and version conflicts.
- **Output:** Knowledge Repository Audit Report & Health Index (0-100%).

### Step 2 — Document Taxonomy & Naming Validation
- Apply standardized naming conventions (`[Category]_[DocType]_[Owner]_[YYYYMMDD]_v[X.X]`).
- Tag mandatory metadata (Owner, Version, Date, Confidentiality Level, Parent Workflow).
- **Output:** Document Taxonomy Registry & Metadata Index.

### Step 3 — Single Source of Truth Resolution
- Detect duplicate, outdated, or conflicting files across workspace directories.
- Assign one authoritative source location and archive superseded versions.
- **Output:** Single Source of Truth Register.

### Step 4 — Vector Indexing & Knowledge Graph Linkage
- Embed document contents into persistent vector stores (`polytope_data.db`).
- Link document nodes to strategic pillars (`spe_01`), contracts (`ldl_01`), and data room folders (`ir_01`).
- **Output:** Indexed Knowledge Graph Node Map.

### Step 5 — Semantic Memory Query Execution
- Process natural language or structured queries over organizational memory.
- Perform hybrid keyword + vector semantic search with exact source citations.
- **Output:** Semantic Query Response Package.

### Step 6 — Request Knowledge Base Modification Approval
- Broadcast WebSocket request to leadership via `ExecApprovalManager` prior to archiving strategic records or altering corporate memory objects.
- *Rule: Alluci indexes and retrieves. Human leadership approves memory changes.*
- **Output:** Approved Knowledge Update Log.

### Step 7 — Export Knowledge Management Package
- Export `Knowledge_Graph_Index.json`, `Document_Taxonomy_Registry.csv`, `Organizational_Memory_Architecture.md`, `Metadata_Verification_Report.json`, and `Knowledge_Management_Manifest.json`.
- **Output:** Exported Knowledge Package & Vault Archive.

---

## 6. Automation Boundaries & Human-in-the-Loop Protocol

### Tier 1: AI-Assisted Activities (Autonomous Audit & Indexing)
Alluci automatically handles:
- Document inventory parsing, metadata tagging, & health index scoring.
- Standardized document naming convention validation.
- Vector embedding generation & graph node linking.
- Semantic memory search & cross-document citation retrieval.
- Stale asset detection ($> 90$ days unreviewed).

### Tier 2: Human Approval Required (Mandatory Executive Sign-Off)
Alluci MUST pause and request explicit executive approval for:
- Modifying core strategic, legal, or financial memory objects.
- Archiving or deleting corporate governance documents.
- Changing document confidentiality classifications (`Restricted` $\rightarrow$ `Public`).
- Releasing internal knowledge bases to external third parties or investors.

### Tier 3: Autonomous Activities After Approval (Vault Synchronization)
Once executive sign-off is granted, Alluci automatically:
- Archives approved document versions into vault repositories.
- Updates persistent graph indexes & vector databases.
- Registers document freshness triggers in PCL monitoring daemon.
- Synchronizes cross-workflow dependencies (`ir_01`, `ldl_01`, `spe_01`).

---

## 7. Diagnostic & 30-Question Verification Checklist

### Failure Mode Diagnostic Rules
Alluci checks for and self-corrects:
- **Version Drift:** Multiple files marked "final" with conflicting content.
- **Orphaned Documents:** Files uploaded without owner or metadata tags.
- **Unindexed Silos:** Critical legal or financial PDFs un-indexed in vector search.
- **Stale Memory Assets:** Strategic plans un-refreshed for $> 90$ days.

### The 30-Question Completion Checklist
The workflow is complete ONLY when Alluci can answer all 30 questions:

#### Memory Architecture & Taxonomy
- [ ] All 6 memory layers (Strategic, Operational, Legal, Financial, Product, AI) indexed?
- [ ] Standardized document naming applied (`[Cat]_[Type]_[Owner]_[Date]_v[X.X]`)?
- [ ] Metadata tags attached (Owner, Date, Version, Confidentiality Level)?
- [ ] Single source of truth assigned for 100% of published documents?

#### Retrieval & Graph Indexing
- [ ] Document contents embedded into vector database (`polytope_data.db`)?
- [ ] Knowledge graph relationships mapped across workflows (`spe_01`, `ldl_01`, `ir_01`)?
- [ ] Semantic query retrieval tested with exact line/file citations?
- [ ] Duplicate or conflicting files resolved and archived?

#### Security & Governance
- [ ] Confidentiality classifications attached (`Public`, `Restricted`, `Strictly Confidential`)?
- [ ] Stale document alert registered in PCL daemon ($> 90$ days)?
- [ ] Executive sign-off obtained via WebSocket prior to archiving strategic records?
- [ ] Audit-ready Knowledge Management package exported to vault?
