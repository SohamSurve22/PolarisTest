# PolarisLex Phase 3 Experiment Report

The complete Phase 3 report and raw artifacts are stored in:

`research/paper/results/phase3_20261025_173000/EXPERIMENT_REPORT.md`

Summary: on the frozen 9-case synthetic test split using keyword-stub retrieval, all four configurations produced binary `covered` F1 = `0.000` with `TP=0`, `FP=0`, `TN=7`, and `FN=2`. Requirement decomposition did not change final statuses. Polarity-aware and combined configurations changed two cases to `violation`, but both were gold `partial` cases and the known gold `violation` case remained `missing`. The evidence is therefore inconclusive and does not support a superiority claim.

Qdrant-backed evaluation was not run because the local service and Docker daemon were unavailable. Historical results were preserved. The dataset manifest was corrected and the original manifest/dataset are preserved in the Phase 3 run snapshot.
