---
name: Graph vs Dense RAG
overview: "Add a Q&A RAG comparison that does not change `/analyze`: dense RAG retrieves from `IT_ACT_POLARISLEX_MERGED.json`; GraphRAG uses in-process GraphIR plus existing `kg_obligation`/`kg_section` vectors. Update `plan.md` with Phase 6."
todos:
  - id: docs-plan-md
    content: "Update plan.md + ARCHITECTURE.md: Phase 6 RAG; /analyze is not Q&A RAG; copy plan to .cursor/plans/"
    status: in_progress
  - id: ingest-rag-merged
    content: "TDD: rag_corpus.py + vectorization ingest-rag from IT_ACT_POLARISLEX_MERGED.json as source_type rag_section"
    status: pending
  - id: dense-retriever
    content: "TDD: dense retrieve top-k rag_section + generate stub; POST /rag mode=dense"
    status: pending
  - id: graph-retriever
    content: "TDD: kg_obligation seed + GraphIR 1-hop expand; POST /rag mode=graph"
    status: pending
  - id: rag-bench
    content: "gold_rag.json + live/skip bench: recall@k and retrieve/generate latency for both modes"
    status: pending
isProject: false
---

# GraphRAG vs dense RAG (Q&A, not analyze)

`POST /analyze` stays the compliance engine (GraphIR duties + Qdrant scores). This slice is the missing **question-answering** comparison: same generator, two retrievers, measured **latency** and **citation recall**.

**Dense RAG corpus only:** [`IT_ACT_POLARISLEX_MERGED.json`](IT_ACT_POLARISLEX_MERGED.json) (291 validated sections; embed `retrieval_text`, cite `doc_id`). Do **not** ingest this file as `kg_obligation` (that would mix with analyze).

**GraphRAG corpus:** existing catalog GraphIR ([`catalog_to_graph_ir`](graph_builder/src/graph_builder/catalog_ir.py)) plus Qdrant `kg_section` / `kg_obligation` from [`kg_export/`](kg_export/). Expand 1 hop on GraphIR relationships (`PENALIZES`, same `section_id` / `act`). No Bolt.

```mermaid
flowchart LR
  q[Question]
  dense[Dense retrieve]
  graph[Graph retrieve]
  gen[Qwen generate]
  bench[Bench latency plus recall]
  merged[IT_ACT_POLARISLEX_MERGED.json]
  qdrantRag[Qdrant rag_section]
  ir[GraphIR catalog]
  qdrantKg[Qdrant kg_obligation kg_section]
  q --> dense
  q --> graph
  merged --> qdrantRag --> dense
  ir --> graph
  qdrantKg --> graph
  dense --> gen
  graph --> gen
  gen --> bench
```

## Docs first

Update [`plan.md`](plan.md) and a short note in [`ARCHITECTURE.md`](ARCHITECTURE.md):

- Current-state table: Q&A RAG **not built**; `/analyze` is not RAG.
- New **Phase 6 — RAG comparison** with checkboxes.
- Architecture diagram: optional `POST /rag` branch (does not feed the memo).
- Decisions: dense = merged JSON; graph = GraphIR + kg vectors; local Qwen; same privacy rules as memo (no raw policy upload in this slice).

Copy this plan to [`.cursor/plans/graph_vs_dense_rag.plan.md`](.cursor/plans/graph_vs_dense_rag.plan.md). Do not edit `duty_rules.json` catalog penalties/roles.

## Dense RAG ingest

New loader next to [`vectorization/src/vectorization/kg.py`](vectorization/src/vectorization/kg.py) (e.g. `rag_corpus.py`):

- Parse merged JSON `sections[]`.
- One `EmbeddableRecord` per section: `retrieval_text` (fallback `clause_text`), `source_type="rag_section"`, `clause_id`/`obligation_id` = `doc_id`, `law_code` = `act`, payload keeps `title`, `topics`.
- CLI `vectorization ingest-rag --path ../IT_ACT_POLARISLEX_MERGED.json`.
- Tests: 291 records from fixture slice; `search_text(..., source_type="rag_section")` does not return `kg_obligation` points.

## Two retrievers + one generator

New small package **`rag/`** (or `policy_compare` module if you want zero new Docker COPY — prefer `rag/` so vectorization stays ingest-only).

Shared `RagAnswer`: `mode`, `answer`, `citations[{id, title, text, score}]`, `retrieve_ms`, `generate_ms`.

- **Dense:** `search_text(question, source_type="rag_section", top_k=5)`.
- **Graph:** seed `search_text(question, source_type="kg_obligation", top_k=5)` (fallback `kg_section`); load GraphIR via existing [`ir_from_paths`](compliance/src/compliance/graph_scope.py); add neighbors with the same `section_id` or `PENALIZES` partner; cap context at 8 chunks; cite obligation/section ids.
- **Generate:** reuse memo chat pattern ([`default_chat`](compliance/src/compliance/report.py) / Ollama). Prompt: answer only from provided excerpts; list cited ids. Stub `chat` in tests (no Ollama).

`POST /rag` on [`policy_compare/src/policy_compare/api.py`](policy_compare/src/policy_compare/api.py): `{question, mode: dense|graph}`. Skip if Qdrant/Ollama down (`503`). **No UI chat panel** in this slice.

## Bench (accuracy + speed)

[`rag/tests/benchmark/gold_rag.json`](rag/tests/benchmark/gold_rag.json): ~12 questions (DPDP consent/withdrawal, IT Act 43A, CERT-In 6 hours, SPDI grievance, children). Each row: `gold_dense_ids` (`doc_id`s from merged JSON) and `gold_graph_ids` (catalog obligation ids).

CLI `rag-bench` (or pytest `-m live`): for each mode, record retrieve/generate ms and recall@k (hit if any gold id is in citations). Print a two-row table. Live tests skip when Ollama is down.

## Out of scope

Web RAG chat, Neo4j Cypher, replacing `/analyze`, LLM-as-judge answer quality, Spec 4 `retrieval_text` rewrite on policies, ingest-on-analyze of uploads.
