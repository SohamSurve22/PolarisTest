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
vectorization                                 # ingest document clauses
vectorization ingest-kg                       # ingest KG obligations/sections
vectorization reembed                         # KG first, then document clauses
vectorization search "personal data" --top-k 5
vectorization search "access personal data" --source-type kg_obligation --top-k 5
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
| `VECTORIZATION_KG_DIR` | `../kg_export` | `*.json` law files for `vectorization ingest-kg` (not GraphIR) |
| `VECTORIZATION_KG_MAX_TOKENS` | `300` | Longer KG paragraphs are split with `CHUNK_OVERLAP_TOKENS` |
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

Preview files that only have `clauses` still work. If the JSON has nested
`entity_clauses` or `contextual_clauses` (or preview `classifications` /
`entities` lists), those tags are appended to `retrieval_text`, for example
`(role: HEADING)` or `(entities: ORGANIZATION, DATE)`.

Qdrant point payload follows PRD §14.4 for document clauses (`source_type`,
`document_id`, `clause_id`, `section_id`, `embedding_model_version`, `language`).
`retrieval_text` is also stored so you can see what was actually embedded.
Points are upserted by a stable UUID of
`document_clause:{document_id}:{clause_id}:{chunk_index}`, so reruns overwrite
rather than duplicate. KG points use the same collection with keys
`kg_obligation:{law_code}:{obligation_id}:{chunk_index}` and
`kg_section:{law_code}:{section_id}:{chunk_index}`.

After this point-id change, delete the existing `document_clauses` collection
(or `docker compose down -v` from the repo root) and re-ingest. Old point ids
will not match.

## KG ingest

`vectorization ingest-kg` reads `*.json` from `VECTORIZATION_KG_DIR` (default
`../kg_export`). Each file is one law/framework:

```json
{
  "law_code": "DPDPA-2023",
  "language": "en",
  "sections": [
    {"section_id": "S8", "title": "Data principal rights", "text": "..."}
  ],
  "obligations": [
    {"obligation_id": "obl_S8_0", "section_id": "S8", "text": "..."}
  ]
}
```

Empty `text` is skipped. KG items are not subject to the 5-token document skip.
Text is split on blank lines; paragraphs over `VECTORIZATION_KG_MAX_TOKENS`
reuse the document sentence/token splitter. This path does not open Neo4j or
import `graph_builder`. Produce GraphIR with `semantic-graph dump-ir statute.txt -o ir.json`,
then `graph-builder-export-kg ir.json -o ../kg_export/LAW.json --law-code LAW`.
Search with `--source-type kg_obligation` or `kg_section`.

## Re-embed (model / backend switch)

Search only returns points whose `embedding_model_version` matches the current
`VECTORIZATION_EMBEDDING_MODEL`. After you change backend or model, old vectors
are in a different space and search will look empty until you re-embed.

1. Set `VECTORIZATION_EMBEDDING_BACKEND`, `VECTORIZATION_EMBEDDING_MODEL`, and
   `VECTORIZATION_EMBEDDING_DIM`. Dim must match both the new model and the
   Qdrant collection (nomic and `all-mpnet-base-v2` are both 768, so the
   collection can stay).
2. If **dimension changes**, delete the `document_clauses` collection (or
   `docker compose down -v` from the repo root) first. Qdrant cannot mix vector
   sizes. This CLI does not drop the collection for you.
3. `vectorization reembed` — same as `ingest-kg` then document ingest. Upserts
   overwrite by `point_id` and stamp the new model id on the payload.
4. `vectorization search "..."` should return hits whose
   `embedding_model_version` equals the new model id.

This job only updates Qdrant. It does not re-score stored reports; those keep
the model version they were generated with.

If `VECTORIZATION_CLAUSES_DIR` or `VECTORIZATION_KG_DIR` no longer contains a
document or law that was ingested under the old model, those points remain but
search will not return them after the model id changes. Delete the collection
if you need a clean index.
