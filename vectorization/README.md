# vectorization

Embeds clauses produced by `document_pipeline` into a Qdrant collection, using
a local Ollama embedding model.

## Setup

```bash
# Qdrant (from repo root)
docker compose up -d qdrant

cd vectorization
pip install -e ../document_pipeline -e .[dev]
cp .env.example .env   # fill in real values
vectorization           # runs the embedding pipeline
```

Run from this directory so the default `VECTORIZATION_CLAUSES_DIR` of
`../document_pipeline/output` resolves correctly.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `VECTORIZATION_QDRANT_URL` | `http://localhost:6333` | |
| `VECTORIZATION_QDRANT_COLLECTION` | `document_clauses` | Created on first run if missing |
| `VECTORIZATION_OLLAMA_URL` | `http://localhost:11434/api/embeddings` | |
| `VECTORIZATION_EMBEDDING_MODEL` | `nomic-embed-text` | Stored as `embedding_model_version` on each point |
| `VECTORIZATION_EMBEDDING_DIM` | `768` | Must match the model and collection vector size |
| `VECTORIZATION_CLAUSES_DIR` | `../document_pipeline/output` | `DOC_*.json` files from `document-pipeline preview` |
| `VECTORIZATION_BATCH_SIZE` | `50` | |

## What gets embedded

Each clause is embedded as `section_title — clause_text`. LLM-generated
`retrieval_text` rewrites are not wired yet.

Qdrant point payload follows PRD §14.4 for document clauses (`source_type`,
`document_id`, `clause_id`, `section_id`, `embedding_model_version`, `language`).
`retrieval_text` is also stored so you can see what was actually embedded.
Points are upserted by a stable UUID of `(document_id, clause_id)`, so reruns
overwrite rather than duplicate.
