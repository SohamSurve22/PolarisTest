# PolarisLex — Project Plan

`document_pipeline/` ingests legal documents and writes parsed JSON. `vectorization/` embeds clauses into Qdrant. `graph_builder/` / `semantic_graph/` build GraphIR and can export to Neo4j. Overlay compare (`POST /compare`) and India analysis (`POST /analyze`) are built. LLM reports and Neo4j obligation traversal are not.

An older rewrite brief lives at `.cursor/plans/optimize_plan.md_e883823e.plan.md`. It is historical (how this file was first slimmed). Do not execute its Phase 1 list.

## Architecture

```mermaid
flowchart LR
  User --> Upload --> DocStore
  Upload --> PDFProc --> TextExtract --> SectionDetect --> ParsedStore
  ParsedStore --> EntityExtract --> Embeddings --> Qdrant
  EntityExtract --> GraphBuilder --> Neo4j
  User --> ComplianceRequest --> ComplianceEngine
  ParsedStore --> ComplianceEngine
  Qdrant --> ComplianceEngine
  Neo4j --> ComplianceEngine
  ComplianceEngine --> LawDetect --> Obligations --> GapDetect --> Penalties --> ReportContext --> ReportGen --> ReportsDB
  ReportGen --> User
```

Parsed store today is `document_pipeline/output/DOC_*.json`. Vectors live in Qdrant. Graph lives in Neo4j when exported. There is no app DB (no SQLite/Postgres).

## Current state

| Area | Status |
|---|---|
| `document_pipeline` orchestrator | End-to-end: loader (txt/pdf/docx/html) → cleaner → section_extractor → block_extractor → clause_builder → clause_extractor → document_understanding → context_builder → entity_extractor → `DefaultLLMPreparer` |
| CLI | `document-pipeline preview` calls `create_default_orchestrator()`; JSON includes `clauses`, `contextual_clauses`, `entity_clauses` |
| Heading regression | Six synthetic policies in `document_pipeline/tests/fixtures/policies/` with gold title lists |
| `vectorization` | Ingest, search, skip/split, EmbeddingProvider, richer JSON, KG JSON ingest (`ingest-kg`), `reembed`. Parked: LLM `retrieval_text` (Spec 4) |
| Graph | GraphIR dump (`semantic-graph dump-ir`) → `graph-builder-export-kg` → `kg_export/*.json`. Neo4j via `semantic-graph export`. |
| Overlay match | Lexical keywords in `policy_compare` (`TOPIC_KEYWORDS`). Parked: smarter matching (below) |
| Analyze v1 | `compliance/` + `POST /analyze`: Qdrant `kg_obligation` match + law-JSON penalties (India). Neo4j later |
| Not built | Neo4j obligation traversal, LLM reports, app DB, pluggable jurisdictions |

Entity extraction stays dictionary/regex (`ClassifierFn` already exists). No LLM classifier in this phase.

**~205** `document_pipeline` tests excluding `tests/test_loader.py` (needs `reportlab` extra). Vectorization has its own pytest suite.

## Phase 1 — Document intelligence

- [x] Wire `document_understanding` → `context_builder` → `entity_extractor` after `clause_extractor`
- [x] Concrete `DefaultLLMPreparer` on `EntityDocument`
- [x] Unify `preview` with orchestrator; nested context/entity in preview JSON
- [x] Synthetic policy fixture library + heading-detector patches
- [x] Keep dictionary/regex entities (no LLM swap-in)
- [x] HTML parser (`.html` / `.htm`)
- [x] Update `document_pipeline/README.md` status (not a skeleton)
- SQLite parsed store — **won't do**; JSON files are the store

## Phase 2 — Embeddings + Qdrant

Package: `vectorization/`. Local Qdrant via root `docker-compose.yml`; default embedder is Ollama `nomic-embed-text`.

- [x] Embed at clause level (unwrap `entity_clauses` / `contextual_clauses` when present)
- [x] Local embedding backend (Ollama default; optional Sentence Transformers)
- [x] Qdrant collection `document_clauses`
- [ ] Optional Spec 4: LLM `retrieval_text` rewrite (parked; needs a chat model)
- [x] Live batch ingest when ready (`vectorization` then `ingest-kg`, or `reembed`)
- [x] GraphIR → `kg_export` JSON dump so obligation search has law text (not SQLite)

## Phase 3 — Policy graph + Neo4j

Packages: `graph_builder/`, `semantic_graph/`.

- [x] GraphIR schema and Neo4j export path
- [x] Save GraphIR JSON to disk (`semantic-graph dump-ir`, or `export --ir-output`)
- [x] Exporter into the `kg_export` file shape (`law_code`, `sections`, `obligations`)
- [x] Idempotent re-ingest tests against a running Neo4j if not already covered
- Hybrid graph+vector fusion — later (compliance engine)

## Phase 4 — Compliance engine

- [x] Policy overlay UI (`policy_compare` + Docker `web`/`api`) — topic coverage, not full gap/penalty analysis
- [ ] Overlay matching: still keyword-based; **do later** — see [Later — smarter matching](#later--smarter-matching)
- [x] API v1: `POST /analyze` (upload + optional `jurisdiction` default `IN`) → `AnalysisResult`. Document-ID lookup of stored `DOC_*.json` is later.
- [x] Pull parsed JSON + Qdrant `kg_obligation` + four law JSON files (penalties). Neo4j obligation traversal is later (`dump-ir` still has no Obligation nodes).
- [x] Steps v1: applicable law (IN) → obligations (vector match) → gaps (missing/partial) → penalties. Output is `AnalysisResult`, not pipeline `context_builder`.
- [x] **Decision:** single-framework MVP (India website privacy). Pluggable jurisdictions later.

## Phase 5 — Report generation + Reports DB

- [ ] LLM report from structured compliance context (not free-form)
- [ ] Fixed sections: applicable law, obligations, gaps, penalties
- [ ] Persist reports by document ID + analysis run

## Later — smarter matching

**Do not do this in the current UI pass.** Overlay colors stay keyword-based so Docker compare does not need Ollama/Qdrant.

Today: `policy_compare/src/policy_compare/topics.py` `TOPIC_KEYWORDS` + `matcher.py`. A policy section maps to a topic if enough keywords hit. Cheap and demo-able. False positives are expected (e.g. “access” in “access logs” looking like a user-rights hit).

When we pick this up, replace or layer matching — not the landing/workspace chrome. Candidate steps, in order:

1. **Embeddings (likely first)** — embed law-chunk summaries and policy section text (Qdrant already exists; `vectorization/` already filters by `source_type`). Vote sections onto topics by similarity instead of (or as a vote with) keywords. Needs running Qdrant + Ollama for `/compare`, which the UI path currently avoids.
2. **LLM classification** — optional second pass: “this paragraph is about retention.” Validate against a pydantic label set. Do not let the model invent statutes.
3. **Graph obligations** — match to GraphIR `Obligation` nodes / Neo4j traversal (“this clause satisfies DPDP §X”), not topic-tag smell. This is the compliance engine, not a UI tweak.

Out of scope for overlay matching: embeddings on `/compare`, hybrid fusion at query time, changing `KEPT_TOPICS`. Penalties live on `/analyze`, not on the overlay graph.

## Decisions

- **Privacy:** local Ollama embeddings by default; cloud embedders are a settings swap, not the default.
- **Naming:** structural `ContextBuilder` is document structure only. Engine output is `AnalysisResult` (findings).
- **Schema:** LLM stages validate against pydantic before downstream use (`ClassificationResult`, `Entity`, `Reference`).
- **Stores:** JSON parsed artifacts, Qdrant vectors, Neo4j graph. No SQLite.

Each phase should end with a real-document run before moving on.
