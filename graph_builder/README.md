# Graph Builder

Offline knowledge graph ingestion pipeline for PolarisLex.

Converts structured legal document output (`EntityDocument`) into a validated
Neo4j knowledge graph. This module never makes compliance decisions.

## Pipeline

```
EntityDocument → LLM Graph Builder → Graph IR → Validator → Cypher Generator → Neo4j
```

## Install

```bash
pip install -e ../document_pipeline
pip install -e ".[dev]"
```

## Usage

```python
from graph_builder import GraphBuilderPipeline, LLMGraphBuilder, Neo4jConfig, Neo4jLoader
from graph_builder import graph_ir_to_kg_dict, write_kg_export

pipeline = GraphBuilderPipeline(
    llm_builder=LLMGraphBuilder(my_llm_client),
    neo4j_loader=Neo4jLoader(Neo4jConfig(uri="bolt://localhost:7687", username="neo4j", password="...")),
)
stats = pipeline.build(entity_document)
```

Dump GraphIR to the JSON shape `vectorization ingest-kg` reads (`VECTORIZATION_KG_DIR`, default `../kg_export`):

```bash
semantic-graph dump-ir statute.txt -o ir.json
graph-builder-export-kg ir.json -o ../kg_export/IT-ACT-2000.json --law-code IT-ACT-2000
```

Or in Python: `write_kg_export(graph_ir, Path("kg_export/IT-ACT-2000.json"), law_code="IT-ACT-2000")`.
This does not open Neo4j. `dump-ir` writes the GraphIR file; `export --ir-output`
still talks to Neo4j and also writes the file. Obligation `text` uses
`properties.text`, or else joins `subject` / `action` / `object` / `condition` /
`exception`. Sections without title/body and blank obligations are omitted.
`semantic-graph dump-ir` builds document structure (Section/Clause). Catalog
`Obligation` nodes (same ids as `/analyze`) come from `semantic-graph from-catalog`.
`/analyze` builds that same GraphIR in-process; it does not open Neo4j.
Opt-in `dump-ir --enrich` extracts slot obligations via local Ollama.
