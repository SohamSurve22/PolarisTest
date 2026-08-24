# PolarisLex — Project Overview

PolarisLex is a legal-document intelligence platform that ingests legal documents
(e.g. privacy policies, contracts), extracts their structure and meaning, and
builds a knowledge graph to support downstream compliance analysis. The repository
is split into three independently installable Python packages that form a data
pipeline: **document_pipeline → graph_builder → semantic_graph**.

## High-level flow

```
Legal doc (.txt/.pdf/.docx)
   │
   ▼  document_pipeline  — structural + entity extraction
EntityDocument
   │
   ▼  graph_builder      — LLM → validated Neo4j graph (GraphIR → Cypher)
GraphIR / Neo4j
   │
   ▼  semantic_graph     — hierarchy + reference resolution + obligation enrichment
Enriched semantic graph (for future compliance engine)
```

Everything after graph/semantic construction (compliance engine, report
generation, vector search, embeddings) is planned but **not yet implemented**.

---

## 1. `document_pipeline/` — Document Intelligence

The preprocessing layer. Ingests documents, extracts structure (sections,
clauses) and entities, and produces a structured `EntityDocument`.

- **Stack:** Python 3.12+, pydantic v2, `pypdf`, `python-docx`.
- **CLI:** `document-pipeline preview <file>`.
- **Stages (pipeline/stages/):**
  - Wired & tested: `loader` → `cleaner` → `section_extractor` →
    `block_extractor` → `clause_builder` → `clause_extractor`.
  - Built but not wired into orchestrator: `document_understanding` →
    `context_builder` → `entity_extractor`.
  - Interface only (no concrete impl): `llm_preparer`.
- **Key pieces:**
  - `parsers/` — format-specific loaders (txt/pdf/docx).
  - `sectioning/heading_detector.py` — heuristic heading detection
    (`STANDARD`/`STANDALONE`), benchmarked ~18/28 headings on a real policy.
  - `models/` — domain models (`document`, `section`, `clause`, `context`,
    `entity`, `metadata`, `semantic`).
  - `pipeline/orchestrator.py` — stage runner.
  - `serializers/pipeline_preview.py` — preview artifact JSON output
    (`output/DOC_*.json`).
- **Status:** 188 unit tests passing. Cannot yet run end-to-end (abstract
  `LLMPreparer`); CLI `preview` manually wires stages and stops at
  `clause_extractor`.

## 2. `graph_builder/` — Knowledge Graph Ingestion

Offline pipeline that converts a structured `EntityDocument` into a validated
Neo4j knowledge graph. It never makes compliance decisions.

- **Pipeline:**
  `EntityDocument → LLMGraphBuilder → GraphIR → GraphValidator → CypherGenerator → Neo4jLoader`
- **Key modules:**
  - `graph_ir.py` — intermediate graph representation.
  - `llm_graph_builder.py` — LLM produces schema-validated graph JSON only.
  - `graph_validator.py` — validates IR against the schema.
  - `cypher_generator.py` — emits idempotent `MERGE` Cypher (no duplicates on
    re-ingest).
  - `neo4j_loader.py` — writes to Neo4j via `Neo4jConfig`.
  - `graph_builder_pipeline.py` — orchestrates the above.
- **Usage:** `GraphBuilderPipeline(llm_builder=..., neo4j_loader=...).build(entity_document)`.

## 3. `semantic_graph/` — Semantic Graph Enrichment

Builds on the `EntityDocument` + graph_builder IR to add legal semantics.
Consumes `EntityDocument` from document_pipeline and produces an enriched
`GraphIR`.

- **Active stages (semantic_graph_builder.py):**
  1. `HierarchyBuilder` — constructs the document skeleton.
  2. `ReferenceResolver` — resolves cross-references between clauses/terms.
- **Semantic enrichment (`semantic_enrichment/`):**
  - `enrichment_models.py` — `Obligation`, `ClauseMeaning` (subject / action /
    object / condition / exception).
  - `clause_analyzer.py` / `llm_clause_analyzer.py` — extract obligations,
    permissions, prohibitions from clauses.
  - `semantic_enrichment_stage.py` — stage wrapper.
- **Export:** `neo4j_exporter.py` + `cli/export_graph.py` write the graph to
  Neo4j using `neo4j_schema.py`.

---

## Roadmap (from `plan.md`)

- **Phase 1:** Finish document intelligence — wire the three un-wired stages into
  the orchestrator, implement concrete `LLMPreparer`, add persistence (SQLite),
  fix heading-detection gaps.
- **Phase 2:** Clause-level embeddings + local Qdrant.
- **Phase 3:** Finalize Neo4j graph schema/ingestion (nodes: `Clause`, `Party`,
  `Obligation`, `DefinedTerm`; edges: `OBLIGATES`, `REFERENCES`, `DEFINED_IN`).
- **Phase 4:** Compliance engine (applicable law → obligations → gaps →
  penalties → compliance context).
- **Phase 5:** LLM report generation + Reports DB.

## Key design decisions

- All LLM stages validate output against pydantic models before downstream use
  (`ClassificationResult`, `Entity`, `Reference`).
- Python owns all graph writes (LLM emits JSON only); `MERGE` is idempotent.
- Privacy posture is undecided (self-hosted vs. third-party LLM/embeddings) —
  relevant before Phase 2.
- Naming collision to resolve: structural `ContextBuilder` vs. future
  compliance-level context builder.
