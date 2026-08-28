---
name: Rewrite plan.md
overview: Neither document is a good source of truth today. The optimize plan is a finished rewrite brief; plan.md is its output and is now stale. Rewrite plan.md against the actual repo (document_pipeline + vectorization + graph_builder), drop SQLite, and stop treating the optimize plan as a backlog.
todos:
  - id: rewrite-plan-md
    content: Replace plan.md current-state + phase checkboxes with repo-accurate status; skip SQLite; archive optimize_plan as non-backlog
    status: completed
  - id: readme-status
    content: Update document_pipeline README status section so it is not “skeleton only”
    status: in_progress
isProject: false
---

# Rewrite plan.md against the repo

## Verdict: which is better?

**Neither, as a backlog.** They are parent and child, not two competing roadmaps.

- [`.cursor/plans/optimize_plan.md_e883823e.plan.md`](.cursor/plans/optimize_plan.md_e883823e.plan.md) is a **one-shot rewrite spec** (“delete §1/§4/§11, fix these five facts, emit a lean 70-line `plan.md`”). Its todos are already `completed`. It is useful as history of why `plan.md` looks the way it does. It is **not** a product plan to execute.
- [`plan.md`](plan.md) is that rewrite’s **output**. Same Phase 1–5 bullets, plus a “current state” table that copied the optimize plan’s facts.

The optimize plan was **better as a document** (it named real bugs: abstract `LLMPreparer`, CLI bypassing the orchestrator, broken mermaid). [`plan.md`](plan.md) is **better as the living file** — but both are now **wrong against the code**. Following Phase 1 leftovers from either file is how we almost built SQLite nobody needs.

Do not follow the optimize plan’s Phase 1 list. Treat it as archived. Refresh `plan.md` only.

## Facts that are now false (in both)

Checked against code:

| Claim in both docs | Reality |
|---|---|
| `document_understanding` / `context_builder` / `entity_extractor` not wired | Wired in [`orchestrator.py`](document_pipeline/src/document_pipeline/pipeline/orchestrator.py) after `clause_extractor` |
| `LLMPreparer` abstract only; orchestrator cannot run E2E | [`DefaultLLMPreparer`](document_pipeline/src/document_pipeline/pipeline/stages/llm_preparer.py) exists; input is `EntityDocument` |
| CLI bypasses orchestrator, stops at `clause_extractor` | [`preview.py`](document_pipeline/src/document_pipeline/cli/preview.py) calls `create_default_orchestrator()`; preview JSON includes `entity_clauses` / `contextual_clauses` |
| No HTML parser | [`HtmlParser`](document_pipeline/src/document_pipeline/parsers/html_parser.py); `.html`/`.htm` on loader + preview |
| No heading fixtures; 18/28 GitHub benchmark | Six synthetic policies under [`tests/fixtures/policies/`](document_pipeline/tests/fixtures/policies/); STANDALONE patched; 18/28 is not CI |
| Everything after document intelligence “not yet implemented” | [`vectorization/`](vectorization/) (Qdrant ingest/search/reembed) and [`graph_builder/`](graph_builder/) + [`semantic_graph/`](semantic_graph/) (GraphIR, Neo4j export) exist |
| 188 tests | `document_pipeline` is ~205 tests excluding `test_loader.py` (reportlab) |
| README “skeleton only” | Still true — only remaining Phase 1 doc chore |

SQLite / “replace JSON as canonical store” stays **out**. Parsed store is `output/DOC_*.json`. Stores in play: JSON files, Qdrant, Neo4j. No app DB.

Entity strategy: keep dictionary/regex (`ClassifierFn` already exists). No LLM classifier in Phase 1.

## What to write into `plan.md`

Replace the file (same lean shape: header, mermaid, current-state table, phases, decisions). Tick what is done. Point Phase 2–3 at packages that already exist instead of “stand up Qdrant from scratch.”

**Current state table (target):**

- Done in orchestrator + preview: loader (txt/pdf/docx/html), cleaner, section_extractor, block_extractor, clause_builder, clause_extractor, document_understanding, context_builder, entity_extractor, DefaultLLMPreparer
- Vectorization (separate package): ingest, search, chunking, EmbeddingProvider, richer JSON, KG JSON ingest, reembed. Parked: LLM `retrieval_text` (Spec 4)
- Graph: GraphIR + Neo4j export. Not wired: dump GraphIR → `kg_export/*.json` for `vectorization ingest-kg`
- Still not built: compliance engine, reports, APIs, app DB

**Phase 1 leftover (docs only):** update [`document_pipeline/README.md`](document_pipeline/README.md) status (not a skeleton; HTML + fixtures + orchestrator preview).

**Phase 2 leftover:** optional Spec 4; live batch ingest when you want it. KG JSON dump from graph_builder is the real join, not SQLite.

**Phase 3 leftover:** exporter GraphIR → `kg_export` shape; hybrid fusion stays later (compliance).

**Phases 4–5:** unchanged in spirit (API, compliance, reports).

Leave [`.cursor/plans/optimize_plan.md_e883823e.plan.md`](.cursor/plans/optimize_plan.md_e883823e.plan.md) on disk; do not execute it. One line in `plan.md` can say it is the rewrite brief that produced an older snapshot.

## Out of scope for this rewrite

- No SQLite, no new parsers, no vectorization code
- Do not rewrite the optimize_plan file
