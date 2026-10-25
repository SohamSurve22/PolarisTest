# Phase 4 Real-Policy Corpus Audit and Evaluation Feasibility

**Audit date:** 2026-10-25  
**Repository:** `D:\Soham\Engineering\Final_Proj\Codebase2`  
**Corpus path:** `D:\Soham\Engineering\Final_Proj\Codebase2\Pdf Trainers`  
**Scope:** local files only; no documents were uploaded, moved, renamed, deleted, or modified.

## Executive finding

The intended `Pdf Trainers` folder exists, but it contains **332 UTF-8 text files and zero PDF files**. The files appear to be scraped or extracted privacy-policy web content. They are potentially useful for a real-policy annotation pilot, but they cannot currently support page-level PDF evidence because page boundaries, original URLs, retrieval timestamps, and source-document provenance are not consistently present.

A real-policy evaluation is feasible only as a manually annotated, text-based pilot after source-quality screening and evidence annotation. It must be reported separately from the 42-case synthetic experiment. The current research adapter cannot consume this corpus as a defensible gold-labeled evaluation without an annotation layer and provenance-aware case conversion.

## Corpus inventory

The machine-readable inventory is in `CORPUS_INVENTORY.csv`. Each row records the relative path, filename-derived company candidate, content-derived title/company candidates, dates explicitly found in text, file size, character/word counts, encoding status, quality flags, SHA-256 hash, and initial text sample.

| Property | Finding |
|---|---:|
| Files in folder | 332 |
| PDF files | 0 |
| Text files | 332 |
| Other file types | 0 |
| Empty files | 0 |
| UTF-8 decode failures | 0 |
| Files with an explicit update/effective-date phrase | 276 |
| Files without an explicit update-date phrase | 56 |
| Very short files (<500 words) | 26 |
| Navigation/scrape-noise flags | 47 |
| JSON or embedded page-data flag | 1 (`027-home-depot.txt`) |
| Very large files (>100,000 words) | 1 (`152-western-digital.txt`) |
| Exact byte-identical duplicate groups | 3 groups / 6 files |

Word counts range from 126 to 198,879, with a median of approximately 4,065 words. File sizes range from 864 bytes to approximately 1.7 MB. Quality flags are not mutually exclusive.

### Titles, companies, dates, and provenance

Company names are recorded as candidates, not verified identities. The filename is useful for discovery but is not treated as authoritative. The inventory also records an initial content-based title candidate and explicit date phrases where found. A year appearing elsewhere in a document is not treated as a publication date.

The corpus does not preserve a reliable original URL, retrieval timestamp, PDF metadata record, or version identifier for every file. Consequently, a date found in text is evidence to review, not a complete provenance record.

### Duplicate and near-duplicate screening

Exact byte-identical groups found:

- `046-united-technologies.txt` and `350-rockwell-collins.txt`
- `079-tiaa.txt` and `407-raymond-james-financial.txt`
- `217-cbs.txt` and `248-viacom.txt`

The last group is especially important because both files identify a Paramount/Skydance privacy-policy title despite different filenames. Several additional files share generic titles such as “Privacy Policy”; these are not treated as duplicates without content and provenance confirmation. The inventory includes SHA-256 hashes and same-title groups for split-leakage screening. A human review of policy versions and affiliated-company relationships is still required.

### Extraction and quality findings

There are no PDFs to classify as scanned versus text-extractable, and therefore no PDF page counts or PDF parser failures to report. All 332 text files decoded as UTF-8 and were non-empty. This does not mean they are clean policy documents:

- 47 files contain substantial navigation or web-page extraction noise.
- 26 files are shorter than 500 words and may be landing pages, privacy-center stubs, or incomplete captures.
- `027-home-depot.txt` begins with embedded JSON/page-data content.
- `152-western-digital.txt` is unusually large and may combine multiple pages or notices.
- Some files contain navigation labels, scripts, “download PDF” references, or links to separate regional notices.

The corpus therefore has text extraction success but incomplete document-quality success.

## Suitability for the existing research pipeline

### Reusable without behavior changes

- Existing legal-obligation IDs and duty-rule structure can be reused for the three obligations currently represented: `DPDP_SEC_6_SUB_1`, `DPDP_SEC_6_SUB_5`, and `DPDP_SEC_8_SUB_5`.
- Existing A–D configuration flags can be reused after a case-construction layer supplies one policy, one obligation, and stable evidence text.
- Existing `gather_evidence()`, `classify_duty()`, element decomposition, and polarity diagnostics can be reused as analysis components.
- Existing metrics can be used only after human gold labels are added and the positive/multiclass mapping is frozen.
- Existing SHA-256 and run-manifest practice can support corpus versioning.

### Required changes or additions

The following are required before a real-policy result can be called an evaluation:

1. A provenance-aware ingestion manifest containing source URL or archive reference, retrieval date, document title, stated policy version/effective date, company/entity, geography, language, and hash.
2. A parser-to-annotation export that retains document ID, section title, clause ID, character span, and—if original PDFs become available—page number.
3. A case schema allowing multiple obligations and multiple evidence spans per policy, rather than only one `policy_text` string per case.
4. An annotation layer separating evidence labels from final compliance status.
5. Explicit handling for regional notices, linked supplemental policies, third-party policies, cookie notices, and pages that are only navigation shells.
6. Duplicate/version grouping before train/test assignment so the same policy family or copied notice cannot cross splits.
7. A retrieval mode that records whether evidence came from the whole policy, a clause window, keyword stub, or vector retrieval.

No production code was changed during this audit. These are feasibility requirements, not completed implementation work.

### Proposed annotation fields

The unlabelled template `ANNOTATION_TEMPLATE.csv` contains 108 rows for 12 proposed policies, 3 obligations, and their atomic elements. Required fields include:

- policy and source hash;
- obligation and authoritative legal-source reference;
- atomic requirement-element ID;
- exact evidence quote;
- page number when a source PDF is available, otherwise a stable clause/character location;
- evidence label: `affirmative`, `contradictory`, `partial`, `absent`, or `ambiguous`;
- final compliance status;
- ambiguity reason;
- annotator ID, adjudication status, and notes.

Evidence-level labels must be completed before final status labels. A keyword hit or missing keyword is not sufficient evidence of legal compliance.

### Evidence and classification rules for annotation

- **Affirmative:** text explicitly supports the requirement and identifies the relevant actor/context.
- **Contradictory:** text explicitly denies, waives, limits, or conflicts with the requirement for the relevant actor/context.
- **Partial:** one or more atomic elements are supported while others are absent or unsupported.
- **Absent:** the reviewed policy text provides no reliable evidence for the element.
- **Ambiguous:** wording, scope, actor, jurisdiction, exception, or cross-reference prevents a reliable determination.

Annotators should record exact quotations and surrounding context, not paraphrases alone. Exceptions, conditional language, “as required by law” clauses, rights reserved to third parties, and cross-references must be marked for adjudication rather than automatically treated as affirmative evidence.

## Proposed defensible pilot

### Selection criteria defined before selection

The proposed pilot selection uses these fixed criteria:

1. Text file is non-empty and at least 2,000 words.
2. Content contains an identifiable privacy-policy/notice/statement title or equivalent privacy heading.
3. Prefer an explicit update/effective-date phrase, but do not infer a date from the filename.
4. Exclude exact duplicate hashes and review same-title or affiliated-company groups before assignment.
5. Include multiple sectors and document lengths.
6. Do not select documents because they appear likely to support or reject the research hypothesis.

Recommended initial pilot (12 policies):

`005-amazon-com.txt`, `006-unitedhealth-group.txt`, `008-cvs-health.txt`, `013-general-motors.txt`, `014-costco-wholesale.txt`, `019-verizon-communications.txt`, `023-phillips-66.txt`, `030-citigroup_in.txt`, `035-dupont-de-nemours.txt`, `038-ibm.txt`, `041-united-parcel-service.txt`, and `047-fedex.txt`.

This is a proposed annotation sample, not an evaluated gold set. Before annotation, a reviewer should confirm that these files are not duplicate versions of one another and that their stated jurisdictions are compatible with the selected Indian legal requirements. If the research question remains specifically Indian DPDP compliance, these mostly non-Indian corporate policies should be treated as external-policy stress tests, not as representative Indian-policy evidence.

### Annotation protocol

1. Freeze the selected-file hashes and create a policy-family grouping.
2. Verify the authoritative legal text and exact requirement source for each obligation.
3. Run document parsing only to create candidate sections/clauses; do not use model output as gold labels.
4. Annotate each atomic element with exact text, stable location, evidence label, actor, jurisdiction, exception/condition, and ambiguity note.
5. Assign final obligation status only after element-level review.
6. Use at least two annotators for a research-quality pilot where feasible; record disagreements and adjudication. If only one annotator is available, disclose that limitation and do not report agreement statistics.
7. Keep unresolved cases as ambiguous/undetermined rather than forcing a binary label.
8. Export a versioned annotation file with hashes, annotator IDs, timestamps, and adjudication state.

## Controlled experiment design

For the real-policy pilot, configurations A–D must use the same selected policies, obligations, annotations, split assignments, and retrieval condition. Synthetic and real-policy results must remain separate.

- A: baseline compliance classification.
- B: requirement-element decomposition enabled.
- C: polarity-aware evidence analysis enabled.
- D: both features enabled.

The split should occur at the policy-family/version level, never at clause level. A policy and a near-identical regional or archived version must remain in the same split. Thresholds must be frozen from the existing configuration or tuned only on a separate development set; the 12-policy pilot is too small to support test-set tuning.

Report both:

- binary `covered` versus `not covered` precision, recall, F1, specificity, false-covered rate, and confusion-matrix denominators; and
- multiclass `covered`, `partial`, `missing`, `violation`, `conflict`, and `undetermined` results where the annotation protocol supports them.

Also report element-level precision/recall/F1, evidence-label agreement or disagreement, retrieval failures, unclassified cases, and annotation uncertainty separately. A lower false-covered rate is not an improvement if recall collapses or the system simply avoids predicting `covered`.

Model errors, annotation uncertainty, and retrieval failures must be assigned separate error categories. Qdrant-backed results may be added only if the service, collection, embedding configuration, and data snapshot are available and recorded. Otherwise, label the experiment as keyword-stub or another explicitly available retrieval mode.

## Literature searches required before paper drafting

No references were added or claimed as verified in this phase. The following targeted searches should be performed using original papers, official venues, DOI records, or authoritative legal sources:

1. Automated privacy-policy compliance analysis and policy-to-regulation alignment.
2. Legal requirement decomposition, obligation modeling, and fine-grained evidence matching.
3. Knowledge graphs and graph-based reasoning for legal/regulatory NLP.
4. Negation, contradiction, polarity, and entailment detection in privacy or legal text.
5. Evidence-grounded compliance classification and human-in-the-loop legal NLP.
6. Evaluation protocols for legal NLP, including annotation agreement, uncertainty, class imbalance, and leakage control.
7. Original sources for PolicyLint, PoliCheck, Claudette, Polisis, and GraphRAG-related claims where directly relevant.
8. Authoritative DPDP Act source text and any relevant rules or official guidance used to define the obligation labels.

## Recommendation and next actions

Proceed with a **small, manually annotated real-policy pilot only after provenance and jurisdiction screening**. Do not draft the final IEEE paper yet. The current synthetic evidence supports a limitations-aware paper outline but not a superiority claim.

Exact next actions:

1. Confirm whether the research target is Indian-policy evidence or cross-jurisdiction stress testing.
2. Verify the 12 proposed files and remove duplicate policy families before annotation.
3. Obtain or record original URLs and retrieval timestamps where available.
4. Review the unlabelled `ANNOTATION_TEMPLATE.csv` with the authoritative legal sources.
5. Implement the provenance/evidence-span schema and export path before producing real-policy predictions.
6. Have human annotators complete and adjudicate the pilot; do not use current model predictions as labels.
7. Run A–D on the frozen annotated subset under one explicitly recorded retrieval mode.
8. Keep the synthetic Phase 3 results as a separate benchmark and report both limitations.

## Files produced

- `CORPUS_INVENTORY.csv` — 332-row inventory.
- `CORPUS_AUDIT.md` — this audit and feasibility/design report.
- `ANNOTATION_TEMPLATE.csv` — 108 unlabelled policy-obligation-element rows for human review.
- `inventory_summary.json` — machine-readable inventory summary.

Existing source files, production code, and Phase 3 results were preserved.
