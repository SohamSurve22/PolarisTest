# Beyond Keyword Matching: A Preliminary Evaluation of Requirement Decomposition and Polarity Awareness in Indian Privacy-Policy Compliance Analysis

**Author and affiliation:** To be supplied by the authors  
**Email:** To be supplied by the authors

## Abstract

Automated privacy-policy analysis must connect policy language with legal obligations while distinguishing affirmative commitments from exceptions, denials, and ambiguous statements. PolarisLex is a knowledge-graph-powered prototype for representing legal requirements, policy clauses, and compliance evidence in an Indian privacy-law setting. This paper describes a deterministic compliance architecture combining obligation rules, evidence retrieval, requirement-element decomposition, polarity-aware handling, and status classification. We evaluate four configurations—baseline, requirement decomposition, polarity-aware evidence, and a combined method—on a fixed dataset of 42 synthetic cases, using 33 cases for training context and 9 cases for testing. Because Qdrant and Docker were unavailable, the experiment uses a reproducible keyword-stub retrieval mode rather than the full vector-retrieval pipeline. All four configurations produce TP=0, FP=0, TN=7, and FN=2 for the binary `covered` class; precision, recall, and F1 are all 0.000, while specificity is 1.000. The zero false-covered rate is therefore degenerate: the system never predicts coverage. Requirement decomposition does not change final classifications in this pilot. Polarity-aware and combined configurations change two cases to `violation`, although both reference labels are `partial`. The results do not demonstrate superiority. They instead expose the need for provenance-aware retrieval, larger independently annotated data, and better calibration of contradictory versus partial evidence. A separate local corpus of 332 extracted text files is audited as a future annotation source, not as an evaluated benchmark.

## Index Terms

Privacy-policy analysis, legal NLP, Indian data protection, knowledge graphs, requirement decomposition, polarity detection, evidence retrieval, compliance classification.

## I. Introduction

Privacy policies are intended to communicate how organizations collect, use, disclose, retain, and protect personal information. Their practical interpretation is difficult because a single policy can contain affirmative commitments, conditional exceptions, cross-references, actor changes, and statements that appear contradictory when read together. Automated analysis can help organize this material, but a keyword match is not equivalent to evidence that a legal obligation is satisfied.

India provides a useful setting for this problem. PolarisLex models obligations associated with Indian privacy and information-security sources, including the Digital Personal Data Protection Act, 2023 (DPDP Act), the Information Technology Act, 2000, the Information Technology (Reasonable Security Practices and Sensitive Personal Data or Information) Rules, 2011, and CERT-In cyber-security directions. The repository contains broader legal catalogs, but the research dataset used in the present evaluation covers only three DPDP obligation identifiers. The legal sources define the context in which obligations are modeled; the experiment does not claim to establish legal compliance for any organization.

Prior privacy-policy research has studied automated extraction, policy consistency, and knowledge-graph representations. PolicyLint detects potential internal contradictions while modeling negation and semantic levels of data objects [2]. PoliGraph represents policy statements as relations in a policy knowledge graph and uses policy-local and global ontologies [1]. A systematic mapping study shows that privacy-policy analysis is multidisciplinary and that extracting isolated facts is more mature than placing those facts in legal context [3]. These works motivate structured evidence analysis, but they do not establish that the specific PolarisLex combination of requirement elements and polarity handling improves Indian obligation classification.

This paper makes a deliberately limited contribution. It documents the implementation and presents a preliminary, reproducible comparison of four configurations. It does not claim a new knowledge-graph paradigm, a new contradiction-detection problem, or superiority over prior systems. The principal result is negative and diagnostic: under the available keyword-stub retrieval condition, the classifier predicts no covered test case, and the proposed features do not recover the two positive examples.

## II. Background and Related Work

Automated privacy-policy analysis includes information extraction, policy summarization, contradiction detection, policy-to-code comparison, and compliance-oriented reasoning. The systematic mapping study by del Álamo et al. reviewed 39 papers selected from a larger search and identified a fragmented research landscape spanning information extraction, semantic analysis, readability, and legal-policy applications [3]. This supports treating a compliance classifier as one component in a broader pipeline rather than as a complete legal judgment system.

PolicyLint is directly relevant to polarity and contradiction. Andow et al. describe a system that considers negation and semantic levels when identifying contradictory collection and sharing statements in mobile-app policies [2]. The result is prior evidence that negative language and ontology structure matter for policy interpretation. PolarisLex adopts a narrower, obligation-centered formulation: a policy clause is evaluated against a modeled requirement and its atomic elements, and a relevant publisher denial can be retained as contradiction evidence.

PoliGraph is relevant to the knowledge-graph perspective. Cui et al. represent statements and relationships across an entire policy, rather than treating every sentence independently, and distinguish local from global ontologies [1]. PolarisLex similarly contains graph-oriented representations for legal and policy entities, but its Phase 3 research adapter loads duty rules directly and does not perform runtime Neo4j traversal or Qdrant vector retrieval. The distinction matters for reproducibility: the architecture and the evaluated path are related but not identical.

LegalRuleML provides an OASIS standardization context for representing legal rules and norms in machine-readable form [4]. PolarisLex does not claim conformance to LegalRuleML. Its `GraphIR` is an internal intermediate representation containing graph nodes, relationships, properties, and source-clause references. The comparison is therefore conceptual: both emphasize explicit rule structure, while the implementation described here uses project-specific schemas.

## III. Problem Formulation

Let an obligation be represented by a rule (r) with requirement elements (E(r)=\{e_1,\ldots,e_m\}), contradiction cues (C(r)), and an actor scope. Let a policy be segmented into clauses (P=\{c_1,\ldots,c_n\}). The system retrieves candidate evidence and constructs an evidence bundle containing a score, matched clauses, element hits, and contradiction clauses.

The classifier assigns one of the operational statuses `covered`, `partial`, `missing`, `violation`, `conflict`, `undetermined`, or `not_applicable`. For the binary experiment, `covered` is the positive class and every other status is negative. This mapping is intentionally stricter than treating partial evidence as success.

For binary evaluation, precision, recall, and F1 are:

\[
P=\frac{TP}{TP+FP},\quad R=\frac{TP}{TP+FN},\quad F1=\frac{2PR}{P+R}.
\]

Specificity is (TN/(TN+FP)), and the false-covered rate is (FP/(FP+TN)). Because a system can obtain a zero false-covered rate by never predicting coverage, these measures must be reported together with recall and the confusion-matrix denominators.

The research questions are:

1. Does requirement-element decomposition change obligation classifications or only element-level reporting?
2. Does polarity-aware evidence handling distinguish relevant denials from affirmative evidence?
3. Does combining the two methods improve the binary and multiclass outcomes under a fixed retrieval condition?
4. What implementation and dataset limitations prevent stronger conclusions?

## IV. PolarisLex Architecture

PolarisLex is organized as a multi-stage prototype. Document processing loads PDF, DOCX, HTML, or text sources; cleans and sections the text; segments clauses; builds contextual and entity artifacts; and prepares semantic inputs. Legal catalogs and duty rules provide obligation identifiers, requirement elements, contradiction cues, applicability metadata, and penalties. Graph-building components serialize legal and policy structures into a project-specific `GraphIR` containing typed nodes and relationships.

The production compliance path is deterministic at the status-decision layer. Evidence collection can use vector retrieval through the vectorization package and can be supplemented by graph and model services, but `classify_duty()` assigns the operational status from the evidence bundle and duty rule. The JEV/Ollama path is advisory and does not replace the primary status.

The research adapter deliberately simplifies this architecture to make a local experiment possible. It loads a duty rule, splits the case text into sentence-level clauses, scores clauses with a keyword stub, calls the production evidence and classification functions, and applies the feature flags before the final classification. It does not call Qdrant, Ollama, Neo4j, or the full document-analysis service. The evaluated path is therefore an adapter-based diagnostic experiment, not a full-system benchmark.

## V. Requirement Decomposition and Polarity-Aware Evidence Analysis

### A. Requirement elements

Each duty rule contains atomic requirement elements. For example, the consent obligation `DPDP_SEC_6_SUB_1` contains `informed_consent` and `purpose`; the withdrawal obligation contains `withdraw` and `cessation`; and the security obligation contains elements such as safeguards, technical measures, access controls, logging, and organisational measures. The research `ElementDecomposer` maps a rule to `AtomicElement` objects and records which element keywords or evidence requirements are found.

In the repaired adapter, decomposition is applied after evidence collection but before classification. It assesses text admitted into the evidence bundle rather than scanning unrelated policy text. Its element IDs are merged into the bundle consumed by `classify_duty()`. This establishes causal wiring while retaining the production engine’s evidence filters. It does not make a legal determination from a keyword alone; the pilot’s simple vocabulary remains a major limitation.

### B. Polarity and contradiction

The polarity detector identifies positive, negative, neutral, and uncertain findings using explicit patterns such as “we do not,” “we cannot,” and positive disclosure forms such as “we collect.” It also marks some third-party contexts. In polarity-aware configurations, a high-confidence, relevant publisher denial is added to contradiction evidence before classification. The production matcher separately applies contradiction cues and denial-polarity filtering.

This design distinguishes evidence-level polarity from final status. A negative sentence can support `violation` or `conflict` only when it is relevant to the obligation and actor scope; unrelated negative statements should not be promoted to legal contradictions. Conditional and mixed sentences remain difficult because the detector is pattern-based and the annotation scheme is small.

## VI. Implementation

The implementation uses Python 3.12-compatible packages, Pydantic models, project-local JSON duty rules, and pytest tests. `GraphIR` validates graph nodes and relationships before downstream export. `DutyRule` objects contain requirement-element specifications, exact terms, generic phrases, contradiction cues, severity, and actor binding. The matcher uses partial, reliable, and covered score constants of 0.30, 0.40, and 0.55 respectively.

The research harness defines four configurations:

| Configuration | Decomposition | Polarity | Description |
|---|---:|---:|---|
| A | Off | Off | Existing baseline |
| B | On | Off | Requirement-element decomposition |
| C | Off | On | Polarity-aware evidence |
| D | On | On | Combined method |

The adapter records evidence quality, element hits, contradiction clauses, polarity findings, configuration flags, and integration completeness in JSONL predictions. This makes it possible to inspect feature activation instead of relying only on aggregate metrics.

## VII. Experimental Methodology

### A. Dataset and annotations

The dataset contains 42 synthetic cases, with 33 training cases and 9 test cases. Every case is annotated by `R001` under single adjudication. The test set contains two `covered`, five `partial`, one `missing`, and one `violation` reference label. It covers only three DPDP obligation identifiers. Three training records contain an element-ID mismatch (`organisational_measures` versus the rule’s `organisational`); this was documented and not silently rewritten. The nine test records used in the reported experiment have valid element IDs.

The separate `Pdf Trainers` corpus contains 332 text files and zero PDFs. It has not been manually annotated or evaluated and is excluded from this experiment. Its audit identifies duplicate groups, short files, scraping noise, and incomplete provenance.

### B. Retrieval condition

The run uses the keyword-stub mode. Each clause is scored against the union of requirement-element keywords and contradiction-cue tokens. The query text is not used as a vector query, and no Qdrant collection is consulted. Qdrant and Docker were unavailable at evaluation time. Results must therefore be interpreted only as a reproducible local comparison under this retrieval condition.

### C. Procedure and reproducibility

The same 9-case test split, duty rules, thresholds, and retrieval mode were used for A–D. The run was associated with commit `ceaf61030a0f5b8dfe57ab2f272f68d5dd902145` and dataset SHA-256 `04ea2a127be98d938f751b174defc9e5a71b83754a7ed9a27608cbb56d8b935b`. Raw predictions, independent metrics, confusion matrices, and case analysis are stored under `research/paper/results/phase3_20261025_173000/`.

The relevant tests recorded 49 passed research tests and 30 passed related compliance tests. No statistical significance test is reported because the test set is small, synthetic, single-annotator, and binary predictions are degenerate.

## VIII. Results

### A. Binary classification

| Configuration | TP | FP | TN | FN | Precision | Recall | F1 | Specificity | False-covered rate | Element F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A baseline | 0 | 0 | 7 | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.800 |
| B decomposition | 0 | 0 | 7 | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.800 |
| C polarity-aware | 0 | 0 | 7 | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.800 |
| D combined | 0 | 0 | 7 | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.800 |

All configurations predict zero `covered` cases. Thus the false-covered rate of zero is an artifact of no positive predictions, not evidence of a reliable classifier. The two gold covered cases are false negatives for every configuration.

### B. Multiclass outcomes and case analysis

| Configuration | Predicted statuses |
|---|---|
| A | `partial=6`, `missing=3` |
| B | `partial=6`, `missing=3` |
| C | `partial=5`, `violation=2`, `missing=2` |
| D | `partial=5`, `violation=2`, `missing=2` |

Requirement decomposition does not change final classifications. Polarity-aware and combined configurations change `SYN_010` from `missing` to `violation` and `SYN_027` from `partial` to `violation`; both reference labels are `partial`. The explicit gold `violation` case `SYN_022` remains `missing`, indicating that polarity activation does not solve the retrieval or actor-filter limitation. The feature changes are therefore interpretable but not improvements under the available labels.

## IX. Discussion

The pilot does not support the hypothesis that the combined method improves compliance classification. Decomposition is activated and produces element diagnostics, but the baseline evidence path already finds the same useful elements in this small test set. Polarity awareness has a visible causal effect, but it over-classifies two partial cases and fails to recover the known violation. The combined configuration behaves identically to polarity awareness at the status level.

The result illustrates why false-covered rate must not be optimized in isolation. A system that predicts only `partial` and `missing` can achieve perfect specificity and zero false-covered rate while missing every covered obligation. It also illustrates the importance of separating evidence polarity from legal status: an explicit limitation may be contradictory for one obligation, partial for another, or ambiguous after considering exceptions and scope.

The knowledge-graph representation remains useful for structuring obligations, source clauses, and relationships, but the experiment does not measure graph traversal or Qdrant retrieval. No claim can be made that the full production architecture improves performance.

## X. Threats to Validity and Limitations

**Dataset validity.** The dataset is small, entirely synthetic, single-annotator, and limited to three obligation identifiers. It is not a real-policy benchmark, and no inter-annotator agreement was measured.

**Retrieval validity.** Keyword-stub retrieval is not semantic vector retrieval. Its vocabulary, thresholding, actor filtering, and sentence segmentation can produce false misses and false contradictions.

**Construct validity.** A policy statement is not a legal conclusion. The operational labels approximate evidence states and do not replace legal interpretation, applicability analysis, or review of authoritative sources.

**Annotation validity.** Two covered examples are insufficient to estimate recall reliably. The training element-ID mismatch also demonstrates schema drift risk.

**External validity.** The separate 332-file corpus contains scraped text with duplicate groups, short captures, navigation noise, and missing provenance. It was not used in the experiment. Results cannot be generalized to those policies or to Indian organizations.

**Implementation validity.** The research adapter bypasses some production services, including Qdrant and advisory JEV/Ollama. Runtime Neo4j traversal is not part of the measured path.

**Temporal and legal validity.** The DPDP Act and related Indian rules may have differing commencement, applicability, and implementation contexts. The paper reports repository-modeled obligations rather than an exhaustive or current legal opinion.

## XI. Future Work

Future work should first create a provenance-aware, independently annotated real-policy pilot. Each annotation should store the source hash, policy version, jurisdiction, exact evidence quote, stable clause location, page number when a PDF exists, atomic element, polarity label, ambiguity reason, final status, and adjudication state. Policy families and near-duplicate versions must be grouped before splitting.

The retrieval study should then compare the keyword stub with a frozen Qdrant snapshot under identical candidate and evaluation policies. Threshold selection should use a separate development split. Additional obligations from the Indian legal catalogs should be incorporated only after authoritative legal-source verification. Larger datasets are necessary before statistical analysis or claims of general improvement.

## XII. Conclusion

PolarisLex provides a knowledge-graph-oriented prototype for organizing Indian privacy-law obligations and policy evidence, with deterministic compliance classification and experimental support for requirement decomposition and polarity-aware evidence. A controlled four-configuration pilot on 42 synthetic cases—33 training and 9 test—found no improvement in covered-class classification. Every configuration produced TP=0, FP=0, TN=7, and FN=2, and all binary F1 scores were zero. Polarity-aware handling changed two predictions to violation, but both disagreed with partial reference labels; decomposition changed no final status. These findings are preliminary and diagnostic. They do not establish superiority, production performance, or legal compliance. The next credible step is human annotation and provenance control for a separate real-policy pilot.

## References

[1] H. Cui, R. Trimananda, A. Markopoulou, and S. Jordan, “PoliGraph: Automated Privacy Policy Analysis using Knowledge Graphs,” in *Proc. 32nd USENIX Security Symposium*, 2023, pp. 1037–1054.

[2] B. Andow, S. Y. Mahmud, W. Wang, J. Whitaker, W. Enck, B. Reaves, K. Singh, and T. Xie, “PolicyLint: Investigating Internal Privacy Policy Contradictions on Google Play,” in *Proc. 28th USENIX Security Symposium*, 2019, pp. 585–602.

[3] J. M. del Álamo, D. Guaman, B. García Gutiérrez, and A. Díez, “A systematic mapping study on automated analysis of privacy policies,” *Computing*, vol. 104, pp. 2053–2076, 2022, doi: 10.1007/s00607-022-01076-3.

[4] OASIS LegalRuleML Technical Committee, *LegalRuleML Core Specification Version 1.0*, OASIS Standard, 2022. [Online]. Available: https://docs.oasis-open.org/legalruleml/legalruleml-core-spec/v1.0/os/legalruleml-core-spec-v1.0-os.html

[5] Government of India, *The Digital Personal Data Protection Act, 2023*, Act No. 22 of 2023, Aug. 11, 2023. [Online]. Available: https://www.meity.gov.in/writereaddata/files/Digital%20Personal%20Data%20Protection%20Act%202023.pdf

[6] Government of India, *The Information Technology Act, 2000*, Act No. 21 of 2000. [Online]. Available: https://www.indiacode.nic.in/indiacode/handle/123456789/1999?locale=en

[7] Ministry of Electronics and Information Technology, Government of India, “Clarification on Information Technology (Reasonable security practices and procedures and sensitive personal data or information) Rules, 2011 under section 43A of the Information Technology Act, 2000,” Press Note, Aug. 24, 2011. [Online]. Available: https://www.meity.gov.in/writereaddata/files/PressNote_25811.pdf

[8] Indian Computer Emergency Response Team, Ministry of Electronics and Information Technology, Government of India, “Directions under Section 70B, Information Technology Act 2000,” Apr. 28, 2022. [Online]. Available: https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf

## Figures

The reproducible figures embedded in the Word manuscript are generated by `research/paper/FIGURES/generate_figures.py`:

- **Fig. 1.** PolarisLex implemented architecture and measured research path: `figure1_architecture.png`.
- **Fig. 2.** Experimental methodology with the 33/9 synthetic split and keyword-stub retrieval: `figure2_methodology.png`.
- **Fig. 3.** Configuration comparison; precision, recall, and F1 are zero for all configurations, while specificity is 1.0: `figure3_configuration_comparison.png`.
- **Fig. 4.** Common binary confusion matrix with `covered` as the positive class: `figure4_confusion_matrix.png`.
- **Fig. 5.** Feature impact and case-level error analysis; polarity changes two partial cases to violation without aggregate improvement: `figure5_feature_impact.png`.
