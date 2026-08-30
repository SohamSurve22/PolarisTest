# Compliance engine benchmarks

Deterministic pytest fixtures (no Qdrant). Live BharatPay re-run:

1. Parse `test_policy/privacy_policy_1.pdf` through the document pipeline.
2. `POST /analyze` with `jurisdiction=IN` (needs Qdrant + embeddings).
3. Assert gold ids in `gold_pass.json`: `DPDP_SEC_8_SUB_5` is covered or partial, never missing; CA/e-sign IT Act duties are `not_applicable`.

```bash
cd compliance && ../.venv/bin/python -m pytest tests/test_benchmark.py -q
```

Optional live marker (skipped unless Qdrant is up):

```bash
../.venv/bin/python -m pytest tests/test_benchmark.py -m live
```

Live `test_policy/Fail_Policy.pdf` (QuickBazaar) must mark withdrawal, erasure, grievance, and children duties `violation` or `conflict`, and must not mark `DPDP_SEC_8_SUB_5` `covered`. Per-duty citations: `gold_fail_citations.json`.
