# PolarisLex Audit Assessment and 8+ Remediation Prompt

## Assessment of the supplied artifact

The supplied document is a **compliance memorandum output**, not an architecture specification. It provides enough evidence to diagnose the current product behaviour, but it does not expose the underlying retrieval, classification, scoring, applicability, legal-source, contradiction-detection, or report-generation architecture.

### Overall current assessment

**Current product quality: 2.5/10 for compliance-assessment reliability.** The output is useful as a document-extraction prototype, but it is not reliable for legal or compliance decisions because it systematically confuses textual similarity with substantive satisfaction of a duty.

| Area | Severity | Gap evidenced by the audit |
|---|---|---|
| Summary arithmetic | Critical | The report states 36 covered + 8 partial + 1 missing + 18 N/A with a total of 45. These figures sum to 63, not 45. |
| Semantic classification | Critical | A clause that expressly denies a right is classified as covering the duty that grants or protects that right. |
| Contradiction handling | Critical | The engine does not detect that “consent cannot be withdrawn,” “deletion may be denied under all circumstances,” and “no grievance mechanism” contradict the corresponding DPDP obligations. |
| Evidence quality | Critical | Definitions, recipient lists, retention language, and parent-supervision language are used as evidence for unrelated duties such as security, accuracy, processor contracts, breach notification, erasure, and parental consent. |
| Applicability | High | Several duties are marked “not applicable” merely because no matching clause exists. “No evidence found” must not be treated as “not applicable.” |
| Duty decomposition | High | Duties are treated as single labels rather than structured requirements with elements, thresholds, actors, conditions, exceptions, deadlines, and required operational actions. |
| Severity and risk | High | The report highlights an ISO/IEC 27001 reference gap while failing to elevate unrestricted sale of Personal Data, indefinite retention, denial of deletion, child-data processing without consent, unrestricted transfers, and rights waivers. |
| Legal-source management | High | The report does not show source version, effective date, provenance, amendment status, or whether a requirement is statutory, regulatory, guidance-based, or framework-based. |
| Citation traceability | Medium | “Closest clause” is helpful, but there is no sentence-level evidence, span offsets, confidence, rationale, or counter-evidence. |
| Audit calibration | High | There is no indication of benchmark performance, false-positive rate, false-negative rate, or confidence calibration. |
| Report safety | High | The headline “36 covered” creates a misleading impression even though the disclaimer says missing language is not a legal violation. |

## Principal product defects to fix

The central defect is a **keyword-to-coverage architecture**. A compliance engine must not treat the existence of a semantically related word or section as proof that a duty is satisfied. It must evaluate whether the policy contains an operative rule that satisfies every material element of the duty.

For example, “we may investigate suspected incidents” does not establish mandatory reporting within six hours. “Personal Data means data about an identifiable individual” does not establish security safeguards. “Parents are responsible for supervision” does not establish verifiable parental consent. “We may retain data indefinitely” does not establish data accuracy, erasure, or legitimate-use compliance. “Third parties may be governed by their own privacy notices” does not establish processor contracts or onward-disclosure controls.

The current output also fails to distinguish **absence**, **contradiction**, **partial support**, **positive support**, and **not applicable**. These must be separate states. In particular, a contradiction is not a missing clause and must be reported as a high-risk adverse finding.

## Target-state design requirements

The revised architecture should use the following pipeline:

1. **Document ingestion and segmentation.** Extract headings, paragraphs, tables, lists, footnotes, dates, and page or character offsets. Preserve the original text and create stable evidence IDs.
2. **Legal-source registry.** Store each duty with jurisdiction, instrument, provision, source URL or official citation, version, effective date, applicability conditions, required elements, exceptions, deadlines, actors, and severity.
3. **Applicability engine.** Determine applicability from facts about the organisation, service, processing activity, sector, role, geography, user population, and technical environment. Use `APPLICABLE`, `CONDITIONALLY_APPLICABLE`, `NOT_APPLICABLE_WITH_REASON`, and `UNKNOWN`; never infer N/A solely from missing text.
4. **Requirement decomposition.** Break each duty into atomic elements. For a reporting duty, separate incident trigger, responsible actor, recipient, deadline, channel, records, and escalation. For a consent duty, separate notice, purpose, affirmative action, voluntariness, withdrawal, proof, and post-withdrawal handling.
5. **Evidence retrieval.** Retrieve candidate clauses using hybrid lexical and semantic search, but do not classify from retrieval alone. Require direct evidence for each atomic element.
6. **Entailment and contradiction analysis.** Evaluate each candidate clause as `SUPPORTS`, `PARTIALLY_SUPPORTS`, `CONTRADICTS`, `IRRELEVANT`, or `AMBIGUOUS`. Run explicit contradiction rules and a second-pass adversarial review.
7. **Duty-level aggregation.** A duty is `COVERED` only when all material elements are supported and no material contradiction exists. It is `PARTIAL` when some material elements are supported but at least one material element is absent or ambiguous. It is `MISSING` when no adequate support exists. It is `ADVERSE` when the policy expressly contradicts the duty. It is `NOT_APPLICABLE` only when the applicability engine provides a documented reason.
8. **Risk scoring.** Assign severity independently of coverage. An adverse clause involving children, consent, deletion, breach reporting, security, rights, sale, or cross-border transfers must score higher than a documentation-only framework gap.
9. **Arithmetic validation.** Validate that category totals, status totals, applicable-duty totals, and document-level totals reconcile before generating the report. Block publication if they do not.
10. **Explainable reporting.** Show the duty, status, atomic elements, evidence spans, counter-evidence, rationale, confidence, source version, applicability reason, severity, and remediation recommendation.

## Required status model

Use the following status definitions exactly:

| Status | Meaning |
|---|---|
| `COVERED` | Every material requirement element has direct, operative support and no material contradiction is present. |
| `PARTIAL` | Some material elements are supported, but one or more material elements are missing, ambiguous, or incomplete. |
| `MISSING` | The duty appears applicable, but the policy contains no adequate operative support. |
| `ADVERSE` | The policy contains language that expressly permits, requires, disclaims, or claims the opposite of the duty. |
| `AMBIGUOUS` | The wording is capable of materially different interpretations and cannot be safely classified without clarification. |
| `NOT_APPLICABLE` | Applicability is affirmatively established and the report records the factual or legal reason. |
| `UNKNOWN` | Applicability or legal interpretation cannot be determined from available inputs. |

Do not collapse `ADVERSE` into `COVERED`, `MISSING`, or `PARTIAL`. Do not collapse `UNKNOWN` into `NOT_APPLICABLE`.

## Required contradiction rules for the DPDP-oriented test set

Implement explicit tests for at least the following contradiction patterns:

- “Consent cannot be withdrawn,” “consent is irrevocable,” or equivalent language contradicts withdrawal rights and post-withdrawal cessation requirements.
- “Deletion may be denied under all circumstances,” “data may be retained permanently,” or equivalent language contradicts purpose-completion, erasure, and retention-limitation requirements.
- “No grievance mechanism,” “complaints may be ignored,” or equivalent language contradicts grievance-redressal obligations.
- “Children’s data may be processed without parental consent” contradicts parental-consent requirements.
- “No safeguards for children,” “targeted advertising to children is permitted,” or equivalent language contradicts child-protection restrictions.
- “Transfer without regard to Indian restrictions” contradicts cross-border-transfer restrictions and applicable-law controls.
- “No responsibility for employee or processor breaches” contradicts fiduciary responsibility and security-accountability requirements.
- “Users waive all privacy rights” contradicts statutory rights and must be reported as a high-severity rights-waiver clause.
- “Any data useful to the company” or “any future purpose” indicates inadequate purpose and data minimisation specificity, even if a separate purpose list exists.
- “Sell, rent, license, or monetise Personal Data” must trigger a commercialisation or disclosure risk finding and must not count as meaningful user control.

## Required evidence and explanation schema

Every duty result should contain a machine-readable record similar to the following:

```json
{
  "duty_id": "DPDP_SEC_6_SUB_6",
  "instrument": "DPDP",
  "provision": "Consent - Cessation of Processing Post-Withdrawal",
  "applicability": {
    "status": "APPLICABLE",
    "reason": "The organisation relies on consent for optional processing."
  },
  "status": "ADVERSE",
  "severity": "CRITICAL",
  "confidence": 0.99,
  "elements": [
    {
      "element": "processing stops after valid withdrawal where no other lawful basis applies",
      "result": "CONTRADICTED",
      "evidence_ids": ["S004_P002_C001"],
      "rationale": "The policy states that consent cannot be withdrawn and processing may continue after an account is closed."
    }
  ],
  "counter_evidence_ids": [],
  "remediation": "Provide a functional withdrawal mechanism and cease consent-based processing unless another lawful basis applies."
}
```

The report should display the evidence sentence in full or provide a reliable expandable view. “Closest clause” alone is insufficient.

## Improved scoring model

Do not use the raw number of covered titles as the headline score. Report at least three separate measures:

1. **Coverage accuracy:** whether the classification is correct against a labelled benchmark.
2. **Risk detection recall:** whether the engine identifies adverse high-severity clauses.
3. **Report integrity:** whether counts, applicability, citations, and explanations are internally consistent.

For an operational product score, use a weighted model such as:

| Dimension | Weight |
|---|---:|
| Legal-semantic classification accuracy | 30% |
| Contradiction and adverse-risk detection | 25% |
| Applicability reasoning | 15% |
| Evidence traceability and explanations | 10% |
| Source/version governance | 10% |
| Arithmetic and report integrity | 10% |

An 8+ rating should require all of the following, not merely a high average: no arithmetic inconsistencies; no critical adverse finding misclassified as covered; documented applicability for every N/A result; evidence for every status; and a benchmarked macro-F1 of at least 0.85 across `COVERED`, `PARTIAL`, `MISSING`, `ADVERSE`, and `NOT_APPLICABLE`.

## Copy-paste implementation prompt

> **Role:** You are a senior compliance-AI architect, legal NLP engineer, and evaluation lead. Upgrade PolarisLex from keyword-based clause matching into an evidence-grounded, contradiction-aware compliance assessment engine. The target is a trustworthy product rating of 8+/10, achieved through measurable improvements rather than inflated coverage counts.
>
> **Context:** The current output incorrectly reports 36 covered, 8 partial, 1 missing, and 18 N/A out of 45 even though those numbers sum to 63. It classifies adverse policy language as coverage. Examples include treating “consent cannot be withdrawn” as coverage for withdrawal rights, indefinite retention as coverage for erasure and legitimate-use duties, parent-supervision language as coverage for parental consent, a generic incident-investigation clause as coverage for mandatory reporting, and a third-party recipient list as coverage for processor contracts and grievance redressal.
>
> **Primary objective:** Redesign the assessment pipeline so that every result is based on atomic legal requirements, direct evidence, applicability reasoning, and explicit contradiction analysis. The system must distinguish `COVERED`, `PARTIAL`, `MISSING`, `ADVERSE`, `AMBIGUOUS`, `NOT_APPLICABLE`, and `UNKNOWN`.
>
> **Implement the following:**
>
> 1. Add a versioned legal-source registry. Each duty must contain instrument, provision, official source, version, effective date, jurisdiction, applicability conditions, atomic requirements, exceptions, deadlines, required actors, and severity.
> 2. Add document segmentation with stable evidence IDs and exact page, paragraph, character, or token offsets. Preserve original text for auditability.
> 3. Add an applicability layer based on organisation facts and processing context. Missing policy language must never produce `NOT_APPLICABLE`. Every N/A result requires a recorded reason; unresolved cases become `UNKNOWN`.
> 4. Decompose every duty into atomic elements. Do not classify a duty from a title, definition, recipient list, generic disclaimer, or semantically adjacent clause.
> 5. Use hybrid retrieval only to generate candidates. Use entailment analysis to decide whether each element is supported, partially supported, contradicted, irrelevant, or ambiguous.
> 6. Add a contradiction detector with explicit rules for consent withdrawal, deletion, retention, child data, child advertising, security accountability, breach notification, grievance redressal, cross-border transfers, rights waivers, purpose limitation, data minimisation, and Personal Data sale or monetisation.
> 7. Make `ADVERSE` a first-class status. An adverse clause must never count as coverage. When adverse and supportive clauses coexist, report both and resolve the duty using a documented precedence rule.
> 8. Add counter-evidence retrieval. For each claimed covered duty, search for clauses that disclaim, limit, waive, override, or contradict the relevant right or obligation.
> 9. Add a deterministic aggregation layer. `COVERED` requires all material elements supported and no material contradiction. `PARTIAL` requires some support but incomplete elements. `MISSING` requires applicability plus no adequate support. `ADVERSE` requires material contradiction. `NOT_APPLICABLE` requires an affirmative applicability reason.
> 10. Add severity independent of status. Escalate child data, consent, deletion, security, breach reporting, rights waivers, sale of Personal Data, and unrestricted international transfers to critical or high severity where applicable.
> 11. Add arithmetic and schema validation. Ensure all category totals reconcile with document totals. Refuse to publish a memorandum with inconsistent counts, missing duty IDs, missing statuses, or unsupported N/A results.
> 12. Replace “closest clause” with full evidence spans, evidence IDs, element-level results, rationale, counter-evidence, confidence, source version, applicability reason, and remediation text.
> 13. Prevent unsupported legal conclusions. Use language such as “the policy text supports,” “the policy text contradicts,” “no evidence found,” and “potential exposure,” while clearly distinguishing text analysis from a legal opinion.
> 14. Add multilingual and accessibility checks for notices, including whether the policy is provided in clear language and in languages required by the applicable legal framework. Do not infer language compliance from a generic statement that the policy should be read with other documents.
> 15. Add regression tests using the QuickBazaar policy and a labelled test suite containing positive, negative, partial, contradictory, irrelevant, and non-applicable examples.
>
> **Minimum QuickBazaar expected results:** The engine must identify as `ADVERSE` or high-risk `PARTIAL`, as supported by the exact text, the following: irrevocable consent/no withdrawal; deletion denial; indefinite or permanent retention; no privacy grievance mechanism; processing children’s data without verifiable parental consent; lack of child safeguards; unrestricted commercial sharing; sale or monetisation of Personal Data; unrestricted international transfers; no responsibility for employee or service-provider breaches; rights waiver; and unnotified policy changes. It must not classify definitions, generic security language, recipient lists, parent-supervision language, or retention language as full coverage for unrelated duties.
>
> **Acceptance criteria:**
>
> - Summary arithmetic passes automated validation for every report.
> - No `NOT_APPLICABLE` result is generated without an applicability rationale.
> - No `COVERED` result is generated where a material contradiction is present.
> - Every status has at least one evidence span or an explicit “no evidence found” record.
> - Every `PARTIAL` result identifies the missing atomic elements.
> - Every `ADVERSE` result identifies the contradictory language and explains the conflict.
> - High-severity adverse clauses appear in the executive summary before framework-documentation gaps.
> - The QuickBazaar test policy produces a risk-oriented report rather than a headline claiming broad coverage.
> - On a labelled benchmark, achieve macro-F1 ≥ 0.85, adverse-risk recall ≥ 0.90, and arithmetic/report-integrity accuracy of 100%.
> - Provide before-and-after examples for at least 15 duties and a short error analysis for every false positive and false negative.
>
> **Deliverables:** Return the revised data model, classification rubric, contradiction rules, scoring formula, applicability logic, evaluation dataset specification, regression tests, sample corrected QuickBazaar report, and implementation notes. Do not claim an 8+ score until the acceptance criteria are measured and passed.

## Expected impact

If implemented faithfully, these changes should improve the product from a **retrieval-and-keyword prototype** into an **evidence-grounded compliance analysis system**. The target 8+ rating is realistic only if the product treats adverse language as a first-class result, validates report integrity, and measures performance on a labelled benchmark rather than relying on the count of clauses that appear superficially related to a duty.

*This assessment is a product-quality review, not a legal opinion. A qualified Indian privacy counsel should validate the legal-source registry and duty decomposition before production use.*
