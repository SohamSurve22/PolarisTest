# PolarisLex — Product Gap Fixation & Improvement Plan

**Document Type:** Product Engineering / Compliance Reasoning Roadmap  
**Based On:** PolarisLex BharatPay privacy-policy test and generated compliance memorandum  
**Date:** 30 August 2026  
**Priority:** High

---

## 1. Executive Summary

The current PolarisLex prototype demonstrates that the ingestion, section/clause extraction, and candidate legal-obligation matching pipeline is functional. However, the BharatPay positive test exposed important weaknesses in the compliance reasoning layer.

The most important issue is that PolarisLex currently treats **"missing coverage" too readily as a compliance failure**, without sufficiently establishing:

1. whether the law is applicable to the entity/document;
2. whether the legal provision is currently applicable/enforceable;
3. whether the retrieved clause actually satisfies the obligation;
4. whether a general statement should be considered PARTIAL rather than MISSING;
5. whether a missing clause actually creates a legal violation;
6. whether a penalty/consequence is applicable to the detected issue.

The product should therefore evolve from a **keyword/semantic obligation matcher** into an **applicability-aware, evidence-backed compliance reasoning engine**.

---

# 2. Current Test Result

The BharatPay privacy policy was intentionally constructed as the positive/PASS test case.

The policy contains explicit provisions for:

- specified purposes of processing;
- consent and withdrawal;
- notice;
- access, correction and erasure;
- grievance redressal;
- security safeguards;
- retention and deletion;
- children's data;
- processor controls;
- cross-border processing;
- breach handling;
- Data Fiduciary responsibilities;
- privacy and grievance contacts.

However, the generated PolarisLex report returned:

- **21 Covered**
- **22 Partial**
- **20 Missing**
- **63 Total duties**

It also evaluated the policy against:

- CERT-In Directions 2022
- DPDP
- IT Act 2000
- SPDI Rules 2011

This produced several results that require validation before the report can be treated as a reliable legal-compliance assessment.

---

# 3. Critical Gaps Identified

## GAP-01 — No Law Applicability Layer

### Problem

PolarisLex appears to evaluate a document against a broad collection of Indian legal duties without first determining whether each law and obligation applies to the organization, industry, processing activity, or document.

This produces false positives such as IT Act duties relating to Certifying Authorities, electronic signatures, and subscriber private-key control.

### Required Fix

Introduce an explicit **Law Applicability Engine** before obligation matching.

### Proposed flow

```text
Document
  ↓
Entity / Industry / Activity Context
  ↓
Jurisdiction
  ↓
Applicable Laws
  ↓
Applicable Legal Duties
  ↓
Clause Matching
  ↓
Compliance Reasoning
```

### Required metadata

Each legal obligation should contain:

- jurisdiction;
- applicable entity types;
- applicable industry/sector;
- regulated activity;
- document relevance;
- effective date;
- commencement date;
- repeal/supersession status;
- dependencies;
- exceptions;
- applicability conditions.

### Acceptance Criteria

A BharatPay privacy policy must not automatically receive unrelated IT Act obligations merely because the entity operates in India.

---

# GAP-02 — Legacy / Current Law Handling

### Problem

The report simultaneously evaluates the document against DPDP, IT Act 2000, SPDI Rules 2011, and CERT-In Directions 2022.

The engine needs to distinguish between:

- currently applicable law;
- partially commenced law;
- repealed/omitted provisions;
- superseded rules;
- sector-specific continuing obligations;
- historical law requested by the user.

### Required Fix

Implement legal-version metadata.

```text
Law
 ├── Status
 │    ├── ACTIVE
 │    ├── PARTIALLY_COMMENCED
 │    ├── REPEALED
 │    ├── SUPERSEDED
 │    └── HISTORICAL
 │
 ├── Effective From
 ├── Effective Until
 ├── Commencement Date
 └── Supersedes
```

### Acceptance Criteria

The engine must not score an outdated or superseded obligation as a present-day compliance failure without explicitly explaining why it remains relevant.

---

# GAP-03 — Security Safeguard False Negative

### Problem

The report marked:

`DPDP_SEC_8_SUB_5 — General Obligations - Security Safeguards`

as **MISSING**.

This is inconsistent with the source policy, which contains a dedicated Data Security Safeguards section describing:

- encryption;
- tokenisation;
- masking;
- least-privilege access;
- MFA;
- environment segregation;
- secure development;
- vulnerability management;
- logging;
- monitoring;
- malware protection;
- backups;
- recovery testing;
- confidentiality;
- vendor due diligence;
- risk assessments;
- audits and testing.

### Required Fix

Improve semantic obligation-to-clause retrieval and clause aggregation.

The matcher must recognize that one legal obligation can be satisfied by a group of related clauses rather than a single exact sentence.

### Acceptance Criteria

For the BharatPay PASS policy:

`DPDP_SEC_8_SUB_5`

must not be classified as `MISSING`.

Expected state:

`COVERED` or `PARTIAL`, depending on the exact legal-rule definition.

---

# GAP-04 — MISSING vs PARTIAL vs VIOLATION

### Problem

The current report does not sufficiently distinguish between:

- no evidence found;
- incomplete evidence;
- ambiguous evidence;
- contradictory evidence;
- actual legal violation.

These are legally and technically different states.

### Required model

```text
MISSING
No relevant clause/evidence found.

PARTIAL
Relevant clause exists, but one or more required elements are absent.

COVERED
The available clause(s) satisfy the indexed obligation.

CONFLICT
The policy contains internally contradictory provisions.

VIOLATION
The policy contains evidence directly conflicting with an applicable legal requirement.

NOT_APPLICABLE
The obligation does not apply to this entity/activity/document.

UNDETERMINED
Evidence is insufficient to confidently classify the obligation.
```

### Important Rule

**MISSING must NOT automatically mean VIOLATION.**

A privacy policy may fail to mention something while the organization could still satisfy the underlying operational/legal requirement elsewhere.

---

# GAP-05 — General Clause vs Exact Statutory Requirement

### Example

The policy says security incidents are handled according to applicable legal requirements and timelines.

If a specific CERT-In rule requires a 6-hour reporting deadline, the generic statement should not be classified as `No matching clause`.

Better:

```text
Generic requirement → MATCH
Specific deadline → NOT EXPLICIT
Overall → PARTIAL
```

### Required Fix

Introduce **specificity scoring**.

```text
Exact statutory requirement
        ↓
Explicit clause
        → HIGH MATCH

Legal concept present
        ↓
General clause
        → MEDIUM MATCH

Weak semantic similarity
        ↓
Candidate only
        → LOW MATCH
```

---

# GAP-06 — Penalty Logic Is Too Closely Coupled to Missing Coverage

### Problem

The report attaches penalties to obligations that the engine has classified as missing.

This risks producing a misleading implication:

```text
Missing clause
    ↓
Violation
    ↓
Penalty
```

This is not safe reasoning.

### Required Fix

Penalty evaluation must be a separate reasoning stage.

```text
Applicability
    ↓
Obligation
    ↓
Evidence
    ↓
Compliance status
    ↓
Actual violation?
    ↓
Penalty provision applicable?
    ↓
Potential consequence
```

### Penalty output should use

- `Potential Maximum Penalty`
- `Applicable Penalty Provision`
- `Trigger Condition`
- `Confidence`
- `Reason`
- `Not a Determination of Liability`

---

# GAP-07 — Poor Matching of Closest Clauses

Some results identify semantically unrelated clauses as the "Closest clause."

Examples include matching grievance or contact clauses to unrelated CERT-In/IT Act duties.

### Required Fix

Add a **minimum semantic relevance threshold**.

If the highest-scoring clause is below the threshold:

```text
No reliable evidence found
```

should be returned instead of forcing a match.

### Recommended evidence states

```text
HIGH
MEDIUM
LOW
NO_RELIABLE_MATCH
```

---

# GAP-08 — Obligation Ontology Needs Improvement

The legal dataset should not represent an obligation only as:

```text
Duty ID
Duty title
Penalty
```

Each obligation should be decomposed into structured requirements.

### Example

```text
Duty:
Security Safeguards

Required Elements:
├── Appropriate safeguards
├── Technical measures
├── Organisational measures
├── Risk proportionality
└── Protection against unauthorized access/loss
```

The clause evaluator can then determine which elements are satisfied.

### Benefit

This makes PARTIAL classification much more defensible.

---

# GAP-09 — Temporal Legal Reasoning

PolarisLex needs to understand:

- effective dates;
- commencement dates;
- amendments;
- repeal;
- supersession;
- transitional provisions;
- historical versions.

### Proposed graph

```text
Law
 ↓
Provision
 ↓
Effective Version
 ↓
Effective Date
 ↓
Commencement Status
 ↓
Applicable Period
```

A policy should be evaluated against the law version applicable on the **analysis date**, unless the user explicitly selects another date.

---

# GAP-10 — Entity / Role Resolution

The same organization can have different legal roles.

Example:

```text
BharatPay
 ├── Data Fiduciary
 ├── Data Processor
 ├── Payment Service Provider
 └── Other regulated roles
```

An obligation may apply only to one role.

### Required Fix

Create role-aware applicability.

```text
Entity
 ↓
Role
 ↓
Activity
 ↓
Legal obligation
```

This will prevent unrelated obligations from contaminating the compliance score.

---

# 4. Compliance Status Model

Replace a simple PASS/FAIL mindset with a richer model.

| Status | Meaning |
|---|---|
| COVERED | Strong evidence satisfies the indexed obligation |
| PARTIAL | Some required elements are satisfied |
| MISSING | No sufficient policy evidence found |
| CONFLICT | Policy contains contradictory clauses |
| VIOLATION | Explicit contradiction with an applicable obligation |
| NOT APPLICABLE | Obligation does not apply |
| UNDETERMINED | Evidence is insufficient |

---

# 5. Compliance Score Improvement

Do not calculate:

```text
Score = Covered / Total Duties
```

because this treats irrelevant duties as equally important.

Instead:

```text
Applicable Duties
        ↓
Weighted Obligations
        ↓
Evidence Evaluation
        ↓
Compliance Score
```

Possible weighting:

```text
Critical obligation   = 5
High obligation       = 4
Medium obligation     = 3
Low obligation        = 1
```

Also exclude `NOT_APPLICABLE` from the denominator.

---

# 6. Graph Improvements

## Current conceptual graph

```text
Document
   ↓
Clause
   ↓
Legal Duty
   ↓
Penalty
```

## Recommended PolarisLex graph

```text
                         ┌──────────────┐
                         │ Jurisdiction │
                         └──────┬───────┘
                                ↓
┌──────────┐              ┌──────────────┐
│  Entity  │─────────────→│ Legal Framework│
└────┬─────┘              └──────┬───────┘
     ↓                           ↓
   Role                     Legal Provision
     ↓                           ↓
 Activity                   Obligation
     ↓                           ↓
 Document Context        Applicability Rule
     ↓                           ↓
   Clause ←──────────── Evidence / Match
     ↓
 Requirement Elements
     ↓
 Compliance Status
     ↓
 Violation / Gap
     ↓
 Consequence / Penalty
```

---

# 7. Explainability Improvements

Every compliance result should expose an evidence chain.

### Recommended UI

```text
DPDP Security Safeguards
────────────────────────────────

Status: ✓ COVERED
Confidence: 94%

Legal Obligation
"Implement reasonable security safeguards..."

Matched Evidence

§8 Data Security Safeguards
" BharatPay implements reasonable security
  safeguards appropriate to the nature,
  scope, context, and risks of processing."

Supporting Elements
✓ Access controls
✓ Encryption
✓ MFA
✓ Logging
✓ Vulnerability management
✓ Backup and recovery
✓ Risk assessment

Reasoning
The policy explicitly describes technical and
organisational safeguards relevant to the
indexed obligation.
```

---

# 8. Graph Visualization Improvements

The graph should support:

- collapsible nodes;
- parent/child legal hierarchy;
- clause-to-obligation links;
- color/status indicators;
- confidence indicators;
- filters by law;
- filters by status;
- filters by severity;
- click-to-view evidence;
- "why matched?" explanation;
- "why partial?" explanation;
- "why not applicable?" explanation.

### Recommended node hierarchy

```text
Document
 ├── Section
 │    ├── Clause
 │    │    └── Evidence
 │
 └── Compliance
      ├── Law
      │    └── Provision
      │         └── Obligation
      │
      └── Result
           ├── Covered
           ├── Partial
           ├── Missing
           ├── Violation
           └── N/A
```

---

# 9. Reference Resolver Improvements

The Reference Resolver should resolve:

- section references;
- subsection references;
- law names;
- abbreviations;
- cross-references;
- defined terms;
- "applicable law" references;
- "as required by law" references;
- references between policy sections.

### Example

```text
"as described in Section 9"
        ↓
Section 9
        ↓
Data Retention and Deletion
```

This should contribute to reasoning rather than being treated as plain text.

---

# 10. Cypher Query Generator Improvements

Generated Cypher queries should support:

### Applicability

```text
Entity → Role → Activity → Obligation
```

### Evidence

```text
Obligation → MATCHED_BY → Clause
```

### Partial coverage

```text
Obligation → HAS_REQUIREMENT → RequirementElement
RequirementElement → SUPPORTED_BY → Clause
```

### Violation

```text
Clause → CONFLICTS_WITH → Obligation
```

### Consequence

```text
Violation → MAY_TRIGGER → Penalty
```

This will make graph traversal substantially more meaningful than a simple nearest-neighbour lookup.

---

# 11. LLM Integration Improvements

The LLM should NOT be the final authority.

Recommended architecture:

```text
LLM
 ↓
Candidate Extraction
 ↓
Deterministic Rule Validation
 ↓
Graph Validation
 ↓
Applicability Validation
 ↓
Final Classification
```

The LLM should produce:

- candidate obligation;
- extracted evidence;
- semantic explanation;
- requirement elements.

The rule/graph layer should determine:

- applicability;
- legal version;
- final status;
- contradiction;
- penalty eligibility.

---

# 12. Dataset Improvements

Each legal obligation in the dataset should include:

```text
duty_id
law_id
section
subsection
title
obligation_text
requirement_elements
jurisdiction
entity_types
roles
industries
activities
document_types
effective_from
effective_until
commencement_status
supersedes
exceptions
dependencies
penalty_reference
severity
keywords
semantic_embedding
```

This metadata is essential for reliable legal reasoning.

---

# 13. Test Dataset Required

Create a fixed benchmark containing at least:

### Test A — PASS

A policy where major applicable obligations are explicitly addressed.

Expected:

```text
High COVERED
Low VIOLATION
Low MISSING
```

### Test B — FAIL

A policy containing explicit contradictions.

Expected:

```text
High VIOLATION
High/Medium MISSING
```

### Test C — PARTIAL

A policy where some requirements are addressed and others are incomplete.

Expected:

```text
Mixed COVERED / PARTIAL / MISSING
```

### Test D — NOT APPLICABLE

A policy/entity combination where unrelated laws should be excluded.

Expected:

```text
NOT_APPLICABLE
```

### Test E — AMBIGUOUS

A policy containing vague clauses such as:

> "We comply with all applicable laws."

Expected:

```text
LOW EVIDENCE
UNDETERMINED / PARTIAL
```

This prevents PolarisLex from treating generic legal language as proof of compliance.

---

# 14. Immediate Fix Priority

## P0 — Must Fix

1. Law applicability engine
2. Current/legacy law handling
3. Security safeguard false negative
4. MISSING ≠ VIOLATION
5. Penalty reasoning separation
6. Better clause-to-obligation matching
7. NOT_APPLICABLE status

## P1 — High Priority

8. Requirement-element decomposition
9. Temporal legal reasoning
10. Entity-role resolution
11. Better evidence/confidence scoring
12. Cross-reference resolution
13. Explainability UI

## P2 — Product Enhancement

14. Advanced graph visualization
15. Compliance score weighting
16. Historical comparison
17. Version comparison
18. Exportable audit trail
19. Benchmark/evaluation dashboard

---

# 15. Definition of Done

PolarisLex should not be considered ready for a credible compliance demonstration until it can satisfy the following:

- [ ] Correctly identify applicable laws.
- [ ] Exclude irrelevant legal obligations.
- [ ] Distinguish current and legacy law.
- [ ] Correctly match explicit security safeguards.
- [ ] Distinguish COVERED / PARTIAL / MISSING / VIOLATION / N/A.
- [ ] Avoid treating missing policy language as automatic legal violation.
- [ ] Avoid attaching penalties directly to missing clauses.
- [ ] Provide evidence for every compliance result.
- [ ] Provide confidence scores.
- [ ] Explain why a clause matched an obligation.
- [ ] Explain why a requirement is partial.
- [ ] Explain why an obligation is not applicable.
- [ ] Support temporal legal versions.
- [ ] Support entity and legal-role applicability.
- [ ] Pass the fixed PASS / FAIL / PARTIAL benchmark.
- [ ] Produce deterministic results for the same input and rule-set version.

---

# 16. Recommended Development Order

```text
PHASE 1
Legal Dataset Validation
        ↓
PHASE 2
Applicability Engine
        ↓
PHASE 3
Reference Resolver Improvements
        ↓
PHASE 4
Clause ↔ Obligation Matching
        ↓
PHASE 5
Requirement Element Extraction
        ↓
PHASE 6
Graph Validation
        ↓
PHASE 7
Compliance Classification
        ↓
PHASE 8
Penalty / Consequence Reasoning
        ↓
PHASE 9
Explainability UI
        ↓
PHASE 10
Benchmark Evaluation
```

---

# 17. Key Product Principle

The core reasoning rule for PolarisLex should be:

> **"No applicable law + no verified evidence = not automatically a violation."**

The engine should establish the complete chain:

```text
Is the law applicable?
        ↓
Is the provision currently applicable?
        ↓
What exactly does the obligation require?
        ↓
What evidence exists in the document?
        ↓
Which requirement elements are satisfied?
        ↓
Is there a contradiction?
        ↓
What is the compliance status?
        ↓
Is a consequence/penalty actually triggered?
```

This is the key transition from a document-matching system to a genuine **Compliance Reasoning Engine**.

---

## 18. Current Assessment

**Parser / ingestion:** Functional  
**Clause extraction:** Functional  
**Semantic matching:** Promising  
**Legal applicability:** Needs major improvement  
**Legal versioning:** Needs major improvement  
**Graph reasoning:** Needs improvement  
**Compliance classification:** Needs improvement  
**Penalty reasoning:** Needs redesign  
**Explainability:** Good foundation  
**Benchmarking:** Must be formalized

The BharatPay test should therefore be retained as a regression benchmark. Any future change to the parser, reference resolver, legal dataset, graph validation, or Cypher generation should be re-run against the same fixed policy and expected outcomes.
