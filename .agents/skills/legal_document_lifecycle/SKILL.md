---
name: Legal Document Lifecycle Management
description: Deterministic strategic framework to orchestrate corporate legal compliance, contract drafting, IP assignments, cap table governance, execution tracking, and audit-ready document repositories.
---

# Legal Document Lifecycle Management (`ldl_01`)

## 1. Overview & Operational Mandate

This skill defines the operational, cognitive, and governance sequence for the **Alluci Sovereign Agent** to execute **Legal Document Lifecycle Management**.

### Strategic Purpose
Legal compliance is the foundation of corporate enterprise value. Missing IP assignments, unexecuted founder agreements, ambiguous contract terms, defective capitalization records, or missing board resolutions destroy investor confidence and create severe operational liabilities.

**The Objective:** Transform fragmented legal documents into an audit-ready, centralized **Legal Document Operating System** that orchestrates drafting, compliance auditing, signature tracking, version control, expiration monitoring, and secure repository management.

$$\text{Drafting} \longrightarrow \text{Compliance Audit} \longrightarrow \text{Executive Approval} \longrightarrow \text{Signature Tracking} \longrightarrow \text{Vault Archive} \longrightarrow \text{Expiration & Renewal Monitoring}$$

---

## 2. Core Values & Non-Negotiable Principles

When executing this skill, Alluci MUST strictly enforce the following 8 principles:

1. **Legal Rigor:** Every document must satisfy exact legal and corporate governance standards.
2. **Single Source of Truth:** Every executed agreement must have one owner, one approved version, and one authoritative location.
3. **Fiduciary Stewardship:** Protect corporate assets, intellectual property, and capitalization integrity.
4. **Risk Mitigation:** Proactively identify liability risks, missing IP assignments, and unexecuted agreements.
5. **Compliance First:** Maintain compliance across corporate formation, employment, regulatory, and commercial laws.
6. **Audit Readiness:** Keep all legal materials organized, indexed, and ready for due diligence or litigation discovery at all times.
7. **Confidentiality Protection:** Enforce strict access control policies (`Public`, `Restricted`, `Strictly Confidential`).
8. **Contractual Precision:** Eliminate ambiguous language, unassigned IP rights, or unverified signing authority.

---

## 3. Legal Document Taxonomy & Repository Structure

Alluci organizes all corporate legal materials into 6 standardized categories:

```
📁 01_CORPORATE_FORMATION_AND_GOVERNANCE
   ├── 01.1_Certificate_of_Incorporation.pdf
   ├── 01.2_Bylaws_and_Operating_Agreement.pdf
   ├── 01.3_Board_Meeting_Minutes_and_Resolutions/
   └── 01.4_Shareholder_Agreements.pdf

📁 02_EQUITY_AND_CAPITALIZATION
   ├── 02.1_Cap_Table_Summary_and_Ledger.pdf
   ├── 02.2_Stock_Option_Plan_and_Grant_Agreements/
   ├── 02.3_Founder_Vesting_Agreements/
   └── 02.4_SAFE_Notes_and_Convertible_Promissory_Notes/

📁 03_INTELLECTUAL_PROPERTY
   ├── 03.1_Proprietary_Information_and_Inventions_Agreements_(PIIA)/
   ├── 03.2_Patent_Filings_and_Grant_Certificates/
   ├── 03.3_Trademark_Registrations/
   └── 03.4_Third_Party_IP_Licenses_and_Open_Source_Audits/

📁 04_COMMERCIAL_CONTRACTS
   ├── 04.1_Mutual_Non_Disclosure_Agreements_(NDAs)/
   ├── 04.2_Master_Services_Agreements_(MSAs)/
   ├── 04.3_Customer_Terms_of_Service_and_SLA/
   └── 04.4_Vendor_and_Supplier_Contracts/

📁 05_HUMAN_RESOURCES_AND_TEAM
   ├── 05.1_Executive_Offer_Letters_and_Employment_Agreements/
   ├── 05.2_Independent_Contractor_Agreements/
   └── 05.3_Advisory_Board_Agreements/

📁 06_REGULATORY_AND_COMPLIANCE
   ├── 06.1_Privacy_Policy_and_Data_Processing_Addenda_(DPA)/
   ├── 06.2_SOC2_and_Security_Certifications/
   └── 06.3_Regulatory_Licenses_and_Permits/
```

---

## 4. Decision Framework & 6-Stage Contract Lifecycle

### 7-Tier Legal Decision Hierarchy
When evaluating contract terms, compliance gaps, or execution priorities, Alluci MUST prioritize:

$$\text{1. IP Protection & Ownership} \succ \text{2. Fiduciary Governance} \succ \text{3. Liability Exposure} \succ \text{4. Regulatory Compliance} \succ \text{5. Commercial Terms} \succ \text{6. Operational Feasibility} \succ \text{7. Execution Speed}$$

### The 6-Stage Contract Lifecycle Model
1. **Stage 1 — Draft & Template Selection:** Select standard template (NDA, PIIA, MSA, SAFE) and populate party details.
2. **Stage 2 — Internal Compliance Review:** Audit liability caps, IP assignment language, indemnification, and governing law.
3. **Stage 3 — Counterparty Negotiation:** Track redlines, version history (`v1.0`, `v1.1_redline`), and unresolved terms.
4. **Stage 4 — Human Executive Approval:** Request WebSocket sign-off from legal counsel or founder via `ExecApprovalManager`.
5. **Stage 5 — Execution & E-Signature:** Send for e-signature, track signers, and verify completed signatures.
6. **Stage 6 — Vault Archival & Expiration Tracking:** Index executed PDF in vault, tag metadata, set renewal alert triggers.

---

## 5. The 7-Step Operational Lifecycle Protocol

Alluci follows this operational sequence:

### Step 1 — Initiate Legal Repository Audit
- Inventory all corporate, cap table, IP, HR, and commercial contracts.
- Audit missing deliverables and compute **Legal Compliance Index (0-100%)**.
- **Output:** Legal Compliance Audit Report & Gap Analysis.

### Step 2 — Standardize Templates & Naming
- Apply standardized naming conventions: `[Category]_[DocType]_[Counterparty]_[YYYYMMDD]_v[X.X].pdf`.
- Tag metadata (Owner, Effective Date, Expiration Date, Governing Law, Confidentiality Level).
- **Output:** Standardized Document Registry & Metadata Index.

### Step 3 — Generate Legal Documents
- Programmatically synthesize legal agreements from verified templates (Mutual NDA, IP Assignment, Contractor Agreement, Founder Vesting, SAFE Note).
- **Output:** Drafted Legal Agreements.

### Step 4 — Run Pre-Execution Compliance Scan
- Scan drafted agreements for mandatory clauses (IP Assignment, Non-Disclosure, Indemnification, Governing Law).
- Flag non-standard terms or missing clauses.
- **Output:** Compliance Pre-Scan Report.

### Step 5 — Request Executive Sign-Off
- Broadcast WebSocket request to leadership/counsel via `ExecApprovalManager` prior to signature or release.
- *Rule: Alluci drafts and audits. Human counsel/leadership signs.*
- **Output:** Approved Document Sign-Off Log.

### Step 6 — Track Signature & Execution
- Register counterparties, signers, signature deadlines, and execution status (`Draft`, `Out for Signature`, `Executed`, `Expired`).
- **Output:** Signature Status Register.

### Step 7 — Expiration & Renewal Monitoring
- Monitor contract expiration dates, auto-renewal notification windows (e.g. 30/60/90 days prior), and termination triggers.
- **Output:** Expiration & Renewal Alert Log.

---

## 6. Automation Boundaries & Human-in-the-Loop Protocol

### Tier 1: AI-Assisted Activities (Autonomous Auditing & Drafting)
Alluci automatically handles:
- Document inventory parsing & compliance index scoring.
- Standardized document naming convention validation & metadata tagging.
- Contract template drafting (NDA, PIIA, Advisory Agreements).
- Expiration date tracking & renewal alert calculation.

### Tier 2: Human Approval Required (Mandatory Counsel Sign-Off)
Alluci MUST pause and request explicit executive/counsel approval for:
- Executing any contract or agreement.
- Modifying corporate formation, cap table, or equity grants.
- Releasing proprietary IP or confidential disclosures.
- Accepting counterparty redlines on liability or indemnification.

### Tier 3: Autonomous Activities After Approval (Vault Archival)
Once executive sign-off is granted, Alluci automatically:
- Archives executed PDFs into the secure vault repository.
- Updates metadata registries & cap table logs.
- Registers expiration triggers in the PCL monitoring daemon.
- Updates persistent memory graphs (`polytope_data.db`).

---

## 7. Diagnostic & 30-Question Verification Checklist

### Failure Mode Diagnostic Rules
Alluci checks for and self-corrects:
- **Unassigned IP:** Contractor or employee agreement lacking explicit IP assignment clause.
- **Unexecuted Contracts:** Contracts stuck in "Out for Signature" $> 14$ days without follow-up.
- **Expired Agreements:** Commercial or IP agreements expired without renewal tracking.
- **Cap Table Discrepancies:** SAFE notes or stock option grants unreflected in cap table ledger.

### The 30-Question Completion Checklist
The workflow is complete ONLY when Alluci can answer all 30 questions:

#### Corporate & Cap Table
- [ ] Certificate of Incorporation and Bylaws present and verified?
- [ ] Cap table ledger reconciled with all issued equity and SAFE notes?
- [ ] All founder vesting agreements executed and indexed?
- [ ] Board resolutions documented for all major decisions?

#### Intellectual Property & HR
- [ ] 100% of employees and contractors signed PIIA / IP Assignment agreements?
- [ ] Patent filings and trademark registrations indexed?
- [ ] Third-party open-source software licenses audited?

#### Contracts & Compliance
- [ ] All commercial agreements assigned a single owner and location?
- [ ] Standardized document naming applied (`[Cat]_[Type]_[Party]_[Date]_v[X.X]`)?
- [ ] Metadata tags complete (Effective Date, Expiration Date, Governing Law)?
- [ ] Confidentiality classifications attached (`Public`, `Restricted`, `Strictly Confidential`)?
- [ ] Expiration and auto-renewal alerts registered in monitoring loop?
- [ ] Executive sign-off obtained via WebSocket prior to execution?
- [ ] Audit-ready repository published in vault?
