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

pipeline = GraphBuilderPipeline(
    llm_builder=LLMGraphBuilder(my_llm_client),
    neo4j_loader=Neo4jLoader(Neo4jConfig(uri="bolt://localhost:7687", username="neo4j", password="...")),
)
stats = pipeline.build(entity_document)
```
