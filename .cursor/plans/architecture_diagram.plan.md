---
name: Architecture diagram
overview: "Produce a senior-ready architecture walkthrough of PolarisLex as it exists today: an interactive Cursor canvas plus a markdown file with mermaid diagrams covering document_pipeline, vectorization, graph_builder/semantic_graph, stores, and what is not built yet."
todos:
  - id: canvas-overview
    content: "Write polarislex-architecture.canvas.tsx: system DAG, built vs not-built callout, package stats"
    status: completed
  - id: canvas-pipelines
    content: Add canvas sections for document_pipeline stages, vectorization ingest/search/kg, graph dump-ir vs Neo4j vs kg_export
    status: completed
  - id: markdown-export
    content: Write ARCHITECTURE.md with mermaid + CLI cheat sheet + Phase 4/5 not-built, no secrets
    status: completed
isProject: false
---

# PolarisLex architecture diagram (current state)

Halt graph-builder nesting work. Deliver a presentation artifact that matches the **repo as it runs today**, not the PRD end-state.

**For agentic workers:** After approval, build the canvas and markdown from this outline. Do not start Neo4j/Qdrant or change pipeline code.

## Deliverables

- **Interactive canvas** at canvases/polarislex-architecture.canvas.tsx
- **Exportable markdown** at ARCHITECTURE.md

Honest split on every diagram: **built** vs **not built** (compliance engine, reports, APIs, app DB, LLM retrieval_text).

Repo copy of the architecture-diagram plan. Preview copy stays under ~/.cursor/plans/.
