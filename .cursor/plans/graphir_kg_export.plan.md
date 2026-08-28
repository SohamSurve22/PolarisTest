---
name: GraphIR kg_export dump
overview: "Dump GraphIR Section/Obligation nodes to the Spec 6 JSON shape for vectorization ingest-kg. No Neo4j, no vectorization import."
todos:
  - id: export-fn
    content: graph_ir_to_kg_dict + write_kg_export
    status: completed
  - id: export-cli
    content: graph-builder-export-kg CLI
    status: completed
  - id: export-tests
    content: Tests, README, plan.md checkbox
    status: completed
isProject: true
---

# GraphIR → kg_export

`graph_builder.kg_export` writes Spec 6 JSON. Vectorization still does not import graph_builder.
