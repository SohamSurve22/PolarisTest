# PolarisLex Research Changelog

## 2026-10-25 — Phase 2 adapter integration repair

### Modified

- `research/src/research/pipeline_adapter.py`
  - Moved research feature application before the call to `classify_duty()`.
  - Requirement-element decomposition now assesses admitted evidence text rather than the entire policy, preventing irrelevant keyword mentions from satisfying an obligation.
  - Decomposed element IDs are merged into the evidence bundle consumed by the classifier.
  - High-confidence, relevant publisher denials detected in polarity-aware configurations are added to contradiction evidence before classification.
  - Added diagnostics for decomposed element hits and polarity contradiction clause IDs.

- `research/tests/test_pipeline_adapter.py`
  - Added tests proving decomposition affects classifier input.
  - Added an irrelevant-keyword regression test.
  - Added a polarity contradiction integration test.

### Added artifacts

- `research/paper/PROJECT_STATUS_AUDIT_20261025_PHASE1.md` — timestamped Phase 1 audit preserving the prior audit file.
- `research/paper/TEST_REPORT.md` — commands and actual Phase 2 outcomes.
- This changelog.

### Preserved

- Historical files under `research/results/`.
- Existing dataset and gold labels.
- Existing user modifications and untracked files outside the focused research changes.
- Baseline configuration behavior, except where the new tests establish the intended feature integration for non-baseline configurations.

### Not performed

- No threshold manipulation.
- No gold-label changes.
- No Qdrant or external-service claims.
- No manuscript or PDF generation.
- No cleanup, reset, or overwrite of the dirty working tree.
