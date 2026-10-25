# Phase 3 Experimental Evaluation Report

**Run:** `phase3_20261025_173805`  
**Date:** 2026-10-25 (Asia/Calcutta)  
**Commit:** `ceaf61030a0f5b8dfe57ab2f272f68d5dd902145`  
**Retrieval:** keyword-stub, no Qdrant  
**Split:** existing `test` split, 9 cases  
**Dataset hash:** `04ea2a127be98d938f751b174defc9e5a71b83754a7ed9a27608cbb56d8b935b`

## Scope and reproducibility

This is a pilot evaluation because the dataset contains only synthetic, single-annotator cases and no development or validation split. The same nine cases, gold labels, retrieval mode, thresholds, and adapter commit were used for configurations A–D. Historical runs under `research/results/` were not overwritten; this run is stored in the current directory.

Qdrant was not used. The local TCP check for `localhost:6333` failed and the Docker daemon was unavailable. Results therefore describe the keyword-stub adapter only and must not be generalized to vector retrieval.

## Dataset integrity

The source JSONL contains 42 unique records: 33 train and 9 test. All records are synthetic, use annotator `R001`, and cover three obligations: `DPDP_SEC_6_SUB_1`, `DPDP_SEC_6_SUB_5`, and `DPDP_SEC_8_SUB_5`. Three training records (`SYN_007`, `SYN_020`, and `SYN_032`) use the expected-element ID `organisational_measures`, whereas the current duty-rule schema uses `organisational`. This metadata mismatch was recorded, not silently repaired. The nine test cases used here have valid expected-element IDs. The test gold distribution is:

| Gold status | Count |
|---|---:|
| covered | 2 |
| partial | 5 |
| missing | 1 |
| violation | 1 |

The manifest was corrected from invalid/empty JSON metadata to reflect the existing split assignments. No case text, gold status, or expected element annotation was changed. The original files are preserved under `dataset_snapshot/`.

## Configuration results

The binary evaluation treats `covered` as positive and every other status as negative. `false_covered_rate = FP / (FP + TN)` and specificity is `TN / (TN + FP)`.

| Configuration | TP | FP | TN | FN | Precision | Recall | F1 | Specificity | False-covered rate | Element F1 | Integration failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A baseline | 0 | 0 | 7 | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.800 | 0 |
| B decomposition | 0 | 0 | 7 | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.800 | 0 |
| C polarity-aware | 0 | 0 | 7 | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.800 | 0 |
| D combined | 0 | 0 | 7 | 2 | 0.000 | 0.000 | 0.000 | 1.000 | 0.000 | 0.800 | 0 |

The zero false-covered rate is not evidence of successful compliance classification: no configuration predicted `covered`, so recall is also zero. Independent metrics are stored in `independent_metrics.json`; the confusion matrices are duplicated in `confusion_matrices.json` for convenient inspection.

### Multiclass status results

| Configuration | Predicted status distribution |
|---|---|
| A baseline | `partial=6`, `missing=3` |
| B decomposition | `partial=6`, `missing=3` |
| C polarity-aware | `partial=5`, `violation=2`, `missing=2` |
| D combined | `partial=5`, `violation=2`, `missing=2` |

Per-class precision, recall, and F1 are available in `independent_metrics.json`. For example, baseline `partial` has precision `0.667`, recall `0.800`, F1 `0.727`; polarity-aware `partial` has precision `0.600`, recall `0.600`, F1 `0.600`. The polarity-aware `violation` predictions have zero precision because both occurred on gold `partial` cases, while the one gold `violation` case remained predicted `missing`.

## Case-level analysis

Only two cases changed status across configurations:

| Case | Gold | A | B | C | D | Interpretation |
|---|---|---|---|---|---|---|
| `SYN_010` | partial | missing | missing | violation | violation | Polarity detector identified a relevant publisher denial involving continued processing after withdrawal. This is a meaningful feature activation, but the gold label treats the mixed clause as partial, so the run shows possible over-classification of violation. |
| `SYN_027` | partial | partial | partial | violation | violation | Polarity detector identified an explicit limitation on safeguards. The gold label is partial; the feature likely treats the limitation as a stronger contradiction than the annotation does. |

`SYN_022` is the explicit irrevocable-consent violation case, but all configurations predicted `missing`; this exposes a retrieval/actor-filter limitation rather than a successful polarity result. The two gold covered cases (`SYN_009`, `SYN_026`) remained `partial` in every configuration, so decomposition and polarity did not recover positive-class recall. `SYN_023` remained `partial` despite security language, and `SYN_024` remained `missing` for non-consent contractual/legitimate-interest language.

The raw per-case predictions and diagnostic feature traces are in the four `predictions_*.jsonl` files and `case_error_analysis.json`.

## Interpretation

- **Requirement decomposition:** Activated in B and D and produced diagnostic element hits, but did not change any final status or aggregate metric on this split. The decomposition hypothesis is not supported by this run.
- **Polarity awareness:** Activated in C and D and changed two cases from baseline statuses to `violation`. Those changes were not correct under the existing gold labels, and the known violation case remained `missing`. This run does not support an improvement claim.
- **Combined method:** Behaved identically to polarity-aware on final status, so no interaction benefit was observed.
- **Overall:** The evidence is inconclusive for superiority and exposes a degenerate positive-class classifier. The pilot does not justify statistical significance, generalization to real policies, or claims about Qdrant-backed retrieval.

## Tests and blockers

Phase 2 tests were rerun before this evaluation:

- `pytest -q research/tests`: 49 passed, 0 failed, 0 skipped; one Windows cache-permission warning.
- `pytest -q compliance/tests/test_matching.py compliance/tests/test_classify.py compliance/tests/test_duty_rules.py`: 30 passed, 0 failed, 0 skipped; one Windows cache-permission warning.

Qdrant and Docker were unavailable. No Qdrant-backed run was substituted or represented as completed. Statistical testing was not performed because the test split is too small and the binary predictions are degenerate.

## Proceeding decision

The evidence is sufficient to proceed to literature/reference verification and a limitations-aware paper outline, but not to write a positive-results paper or claim that either proposed method improves compliance classification. A larger, independently annotated, real-policy dataset and a non-degenerate retrieval/evaluation setup are required before strong conclusions.
