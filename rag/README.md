# rag

Statute Q&A comparison. Same local Qwen generator, two retrievers. This package
does **not** score privacy policies and does not feed `POST /analyze` or the memo.

## Modes

| Mode | Retrieve |
|---|---|
| `dense` | Qdrant `source_type=rag_section` (merged JSON, cite `doc_id`) |
| `graph` | Seed `kg_obligation` (fallback `kg_section`), expand GraphIR `PENALIZES` / same `section_id`, cap 8 |

```bash
# Ingest dense corpus (from vectorization/, Qdrant + Ollama embeddings)
vectorization ingest-rag --path ../dataset/IT_ACT_POLARISLEX_MERGED.json

# API (policy_compare FastAPI) and web Queries tab (no policy upload)
# POST /rag  {"question": "...", "mode": "dense"|"graph"}
# UI: http://localhost:8080/#queries

# Bench (skips / exit 2 when Ollama or Qdrant is down)
cd rag && pip install -e ".[dev]"
rag-bench
../.venv/bin/python -m pytest tests/ -q
../.venv/bin/python -m pytest tests/ -q -m live   # skip if Ollama is down
```
