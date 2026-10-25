# PolarisLex Phase 2 Test Report

**Date:** 2026-10-25  
**Baseline commit:** `ceaf61030a0f5b8dfe57ab2f272f68d5dd902145`  
**Scope:** research adapter integration repair and directly related compliance behavior.

## Tests executed in this phase

| Command | Passed | Failed | Skipped | Result |
|---|---:|---:|---:|---|
| `pytest -q research/tests` | 49 | 0 | 0 | Passed |
| `pytest -q compliance/tests/test_matching.py compliance/tests/test_classify.py compliance/tests/test_duty_rules.py` | 30 | 0 | 0 | Passed |

Both commands emitted one non-failing Windows `PytestCacheWarning`: pytest could not write under the existing `.pytest_cache` directory because access was denied. No test was skipped for a dependency or service in these commands.

The full application test matrix was not rerun in this phase. The Phase 1 audit records the previously observed broader-suite failures, skips, and missing `fastapi`; those observations must not be interpreted as results of this focused run.

## Added behavioral coverage

The research adapter tests now cover:

- explicit affirmative evidence;
- explicit contradictory evidence;
- missing and empty evidence;
- partial obligation coverage;
- multiple requirement elements;
- irrelevant keyword matches;
- ambiguous or insufficient evidence;
- decomposition contributing evidence before status classification; and
- polarity-aware contradiction evidence reaching classification.

## Smoke evaluation

A read-only in-process smoke evaluation used the existing 9-case test split and all four configurations. It did not write result artifacts.

| Configuration | Status distribution | Integration failures | Cases with decomposition hits | Cases with polarity contradiction evidence |
|---|---|---:|---:|---:|
| Baseline | `partial=6`, `missing=3` | 0 | 0 | 0 |
| Element decomposition | `partial=6`, `missing=3` | 0 | 6 | 0 |
| Polarity aware | `partial=5`, `violation=2`, `missing=2` | 0 | 0 | 2 |
| Combined | `partial=5`, `violation=2`, `missing=2` | 0 | 6 | 2 |

This smoke result demonstrates feature activation, not a replacement for the formal Phase 3 evaluation. Historical metrics and predictions were not overwritten.

## Not executed

- Qdrant-backed retrieval evaluation.
- Ollama/JEV evaluation.
- Neo4j or MongoDB integration tests.
- Full repository test matrix.
- Statistical significance testing.
- PDF/Word generation and visual document QA.
