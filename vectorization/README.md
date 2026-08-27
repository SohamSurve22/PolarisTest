# vectorization

Embeds clauses produced by `document_pipeline` into a Qdrant collection, using
a local Ollama embedding model.

## Setup

```bash
# Qdrant (from repo root)
docker compose up -d qdrant

cd vectorization
pip install -e ../document_pipeline -e .[dev]
# optional: pip install -e '.[st]'   # Sentence Transformers backend
cp .env.example .env   # fill in real values
vectorization                                 # ingest clauses
vectorization search "personal data" --top-k 5
```

Run from this directory so the default `VECTORIZATION_CLAUSES_DIR` of
`../document_pipeline/output` resolves correctly.

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `VECTORIZATION_QDRANT_URL` | `http://localhost:6333` | |
| `VECTORIZATION_QDRANT_COLLECTION` | `document_clauses` | Created on first run if missing |
| `VECTORIZATION_OLLAMA_URL` | `http://localhost:11434/api/embeddings` | |
| `VECTORIZATION_EMBEDDING_MODEL` | `nomic-embed-text` | Stored as `embedding_model_version` on each point. If backend is `sentence_transformers` and this is still `nomic-embed-text`, ingest uses `all-mpnet-base-v2` |
| `VECTORIZATION_EMBEDDING_DIM` | `768` | Must match the model and collection vector size |
| `VECTORIZATION_EMBEDDING_BACKEND` | `ollama` | `ollama` (default) or `sentence_transformers` |
| `VECTORIZATION_EMBED_BATCH_SIZE` | `32` | Texts per embed_batch call; Qdrant upsert still uses `BATCH_SIZE` |
| `VECTORIZATION_DOCUMENT_EMBED_PREFIX` | `search_document: ` | Prepended to clause text at embed time only |
| `VECTORIZATION_QUERY_EMBED_PREFIX` | `search_query: ` | Prepended to search queries at embed time only |
| `VECTORIZATION_CLAUSES_DIR` | `../document_pipeline/output` | `DOC_*.json` files from `document-pipeline preview` |
| `VECTORIZATION_BATCH_SIZE` | `50` | |
| `VECTORIZATION_SEARCH_TOP_K` | `10` | kNN result cap before the score floor |
| `VECTORIZATION_SEARCH_MIN_SCORE` | `0.55` | Hits below this score are dropped |
| `VECTORIZATION_MIN_CLAUSE_TOKENS` | `5` | Clauses shorter than this are not embedded |
| `VECTORIZATION_MAX_CLAUSE_TOKENS` | `512` | Longer clauses are split at sentence boundaries |
| `VECTORIZATION_CHUNK_OVERLAP_TOKENS` | `50` | Overlap between split chunks |

`vectorization search` prints one JSON object per hit (`score`, `clause_id`, `retrieval_text`). Filters always include `source_type` (default `document_clause`) and the current `embedding_model`. Pass `--document-id` to restrict to one document.

## What gets embedded

Each clause is embedded as `section_title — clause_text`. Before the vector is
computed, `nomic-embed-text` prefixes are added: `search_document: ` on ingest
and `search_query: ` on search. Those prefixes are **not** stored in Qdrant
payload (Ollama/Nomic only). Sentence Transformers does not use them. Switching
`VECTORIZATION_EMBEDDING_BACKEND` requires a full re-ingest so search does not
mix models.

Clauses under
`VECTORIZATION_MIN_CLAUSE_TOKENS` (default 5, counted on `clause_text` only)
are skipped. Clauses over `VECTORIZATION_MAX_CLAUSE_TOKENS` (default 512) are
split at sentence boundaries with `VECTORIZATION_CHUNK_OVERLAP_TOKENS`
(default 50) overlap. The original `clause_id` stays the citation unit;
each chunk is a separate Qdrant point with `chunk_index` in the payload.

LLM-generated `retrieval_text` rewrites are not wired yet.

Qdrant point payload follows PRD §14.4 for document clauses (`source_type`,
`document_id`, `clause_id`, `section_id`, `embedding_model_version`, `language`).
`retrieval_text` is also stored so you can see what was actually embedded.
Points are upserted by a stable UUID of
`document_clause:{document_id}:{clause_id}:{chunk_index}`, so reruns overwrite
rather than duplicate.

After this point-id change, delete the existing `document_clauses` collection
(or `docker compose down -v` from the repo root) and re-ingest. Old point ids
will not match.
