# vectorization

Embeds clauses produced by `document_pipeline` into a pgvector table, using
a local Ollama model.

## What changed from the old `PolarisMain/vectorization/vectorization.py`

- **Config**: nothing is hardcoded. All DB/Ollama settings come from env
  vars prefixed `VECTORIZATION_` (see `.env.example`), following the same
  pattern as `document_pipeline`'s `PipelineSettings`.
- **Input**: reads `document_pipeline`'s actual `SegmentedDocument` JSON
  output (`clause_id`, `clause_text`, etc.) instead of the old hand-curated
  `IT_ACT_POLARISLEX_MERGED.json`, which had fields (`retrieval_text`,
  `topics`, `plain_english_summary`, ...) that no longer exist upstream.
  `models.clause_to_embeddable()` is the one place that decides what text
  gets embedded — swap it if/when semantic_graph's clause enrichment gets
  wired in as a richer source.
- **Batching**: commits every `VECTORIZATION_BATCH_SIZE` records (default
  50) instead of one commit at the very end, so a crash partway through
  doesn't lose the whole run.
- **Idempotent reruns**: `ON CONFLICT (clause_id) DO UPDATE`, so re-running
  after a partial failure or a document_pipeline re-export doesn't create
  duplicates.
- **Schema vs data**: `db/schema.sql` is an actual `CREATE TABLE` migration.
  The old `mydb.sql` was a raw data dump of rows (including embedding
  vectors) — that shouldn't be committed to the repo at all.

## Setup

```bash
cd vectorization
pip install -e .
cp .env.example .env   # fill in real values
psql -f db/schema.sql
vectorization           # runs the embedding pipeline
```

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `VECTORIZATION_PG_HOST` | `localhost` | |
| `VECTORIZATION_PG_PORT` | `5432` | |
| `VECTORIZATION_PG_DATABASE` | `polarislex` | |
| `VECTORIZATION_PG_USER` | `polarislex` | |
| `VECTORIZATION_PG_PASSWORD` | *(empty)* | set this, don't hardcode it |
| `VECTORIZATION_OLLAMA_URL` | `http://localhost:11434/api/embeddings` | |
| `VECTORIZATION_EMBEDDING_MODEL` | `nomic-embed-text` | |
| `VECTORIZATION_CLAUSES_DIR` | `../document_pipeline/output` | where `document_pipeline` writes its `DOC_*.json` files |
| `VECTORIZATION_BATCH_SIZE` | `50` | |
