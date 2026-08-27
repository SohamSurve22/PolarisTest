---
name: Vector KG ingest
overview: "Second Qdrant population: obligation and section text as source_type kg_obligation / kg_section. File/JSON in, no live Neo4j, no graph_builder import. Search already filters by source_type. Implement after Spec 2 (and ideally store payload generalization)."
todos:
  - id: kg-json-contract
    content: KgSource pydantic models + loader for VECTORIZATION_KG_DIR JSON files
    status: pending
  - id: kg-records
    content: Map obligations/sections to EmbeddableRecord with PRD payload fields; paragraph chunking
    status: pending
  - id: generalize-upsert
    content: Upsert source_type, law_code, obligation_id from the record; namespaced point_id
    status: pending
  - id: cli-ingest-kg
    content: vectorization ingest-kg CLI; search --source-type kg_obligation works unchanged
    status: pending
  - id: tests-docs
    content: Tests with fixture JSON (no Neo4j); README + .env.example
    status: pending
isProject: true
---

# Spec 6 — KG obligation / section ingest

**Depends on:** Spec 1 (search `source_type` filter — done). Spec 2 chunking helpers if already landed (reuse skip/split for long KG text). **Does not wait on:** live Neo4j, graph_builder package import, hybrid fusion (PRD §14.7).

PRD §14.2–14.5: knowledge-graph **Obligation** and **Section** text is pre-indexed in Qdrant. Query side embeds a document clause and searches `source_type=kg_obligation`. Today only `document_clause` points exist; `law_code` and `obligation_id` are always null.

graph_builder / semantic_graph already produce `GraphIR` with `Obligation` and `Section` nodes, and export to Neo4j. This spec does **not** open a Neo4j driver and does **not** import `graph_builder`. Wiring dump-from-graph → this JSON is a later task.

```mermaid
flowchart LR
  json[KG JSON files]
  records[EmbeddableRecord]
  embed[Embedder]
  store[VectorStore.upsert]
  qdrant[Qdrant same collection]
  json --> records --> embed --> store --> qdrant
```

## Input contract (file only)

Directory: `VECTORIZATION_KG_DIR` default `../kg_export` (empty until someone dumps files). Load `*.json` (not only `DOC_*`).

Each file is one law/framework:

```json
{
  "law_code": "DPDPA-2023",
  "language": "en",
  "sections": [
    {
      "section_id": "S8",
      "title": "Data principal rights",
      "text": "A Data Principal shall have the right to ..."
    }
  ],
  "obligations": [
    {
      "obligation_id": "obl_S8_0",
      "section_id": "S8",
      "text": "The Data Fiduciary shall allow a Data Principal to access their personal data."
    }
  ]
}
```

- `law_code` required (payload + point-id namespace).
- `text` is what gets embedded. If `text` is missing/blank, skip that item and log.
- Obligation `section_id` optional (nullable payload).
- Extra keys ignored.

**GraphIR adapter is out of this spec.** When graph_builder is wired, a small exporter will write this shape (Obligation `text` = join of `subject` / `action` / `object` / `condition` / `exception`; Section `text` = `title` plus any body). Do not parse `nodes`/`relationships` GraphIR inside vectorization now.

Pydantic models in vectorization (e.g. `vectorization/kg_models.py`): `KgFile`, `KgSection`, `KgObligation`.

## Records and payload

Reuse `EmbeddableRecord` with fields the store already conceptually has:

| EmbeddableRecord | Qdrant payload |
|---|---|
| `source_type` | `kg_obligation` or `kg_section` |
| `law_code` | file `law_code` |
| `obligation_id` | obligation id or null for sections |
| `section_id` | section id |
| `document_id` | **null** |
| `clause_id` | **null** |
| `clause_text` | original item `text` (full, before chunk) |
| `retrieval_text` | chunk text actually embedded |
| `source["chunk_index"]` | 0-based |
| `source["chunk_type"]` | `"obligation_text"` or `"section_text"` (PRD §14.2) |

Add `source_type`, `law_code`, `obligation_id` to `EmbeddableRecord` with defaults (`document_clause`, `None`, `None`) so document ingest stays valid.

## Chunking

PRD: KG text at **paragraph** granularity (typically 100–300 tokens), one point per chunk.

- Split `text` on blank lines (`\n\n`).
- Each paragraph: if token count &gt; `VECTORIZATION_KG_MAX_TOKENS` (default **300**), reuse Spec 2 sentence/token split + overlap (`CHUNK_OVERLAP_TOKENS`, default 50).
- Do **not** apply the document 5-token skip to KG items; skip only empty text.
- `retrieval_text` for a section chunk may prefix `title — ` when title is present (same join idea as clauses). Obligations embed `text` / chunk only (no fake section title).

## Point id

Must not collide with document clauses. After Spec 2, document ids should already be:

```text
document_clause:{document_id}:{clause_id}:{chunk_index}
```

KG:

```text
kg_obligation:{law_code}:{obligation_id}:{chunk_index}
kg_section:{law_code}:{section_id}:{chunk_index}
```

Implement as one helper:

```python
def point_id(key: str) -> str:
  return str(uuid.uuid5(_POINT_NAMESPACE, key))
```

Store builds `key` from `record.source_type` + stable ids. Keep a thin wrapper `document_point_id(document_id, clause_id, chunk_index=0)` if Spec 2 already shipped a 3-arg function — migrate it to the namespaced key in this spec if Spec 2 used `{document_id}:{clause_id}:{chunk_index}` only (one collection recreate; document in README).

**Same collection** `document_clauses` (name is historical). Search filters `source_type`; do not create a second collection.

## Store

[`VectorStore.upsert_batch`](vectorization/src/vectorization/store.py) today hardcodes `"source_type": "document_clause"` and null `law_code` / `obligation_id`. Change it to copy from the record:

- `source_type`, `law_code`, `obligation_id`, `document_id`, `clause_id` from the record
- `chunk_index` / `chunk_type` from `record.source`

Search is unchanged. CLI already has `--source-type`.

## Pipeline + CLI

```bash
vectorization ingest-kg
```

`run_kg(settings)` loads `VECTORIZATION_KG_DIR`, builds records, embeds, upserts — same embed loop as document `run()`. Default `vectorization` (no subcommand) stays **document** ingest.

```bash
vectorization search "access personal data" --source-type kg_obligation --top-k 5
```

## Tests (TDD)

Fixture JSON with one section + one obligation. Mock embedder + Qdrant:

- upsert payload `source_type=kg_obligation`, `law_code` set, `document_id` is null
- two chunks from a long obligation → distinct point ids, same `obligation_id`
- empty `text` skipped
- `search(..., source_type="kg_obligation")` filter already covered in Spec 1; add one upsert+search mock that the filter value is `kg_obligation`
- document ingest tests still see `source_type=document_clause`

No Neo4j, no graph_builder import, no live Qdrant/Ollama.

## Out of scope

- Neo4j driver / Cypher read
- Importing `graph_builder` or `semantic_graph`
- GraphIR `nodes`/`relationships` parser
- Hybrid fusion (graph defines scope, vectors score) — compliance engine
- Eval set / KG-first re-embed ordering (extend Spec 7 later: `reembed` runs `run_kg` then `run`)
- FastAPI

## After you approve

Implement **after Spec 2** (chunking + namespaced document point ids). Specs 3–5 can land before or after this; this spec only needs embed + upsert + search. Do not start this spec in the Spec 2 implementation session.
