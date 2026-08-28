# Document Intelligence Pipeline

Preprocessing pipeline for **PolarisLex** — prepares uploaded legal documents for semantic analysis and Knowledge Graph generation.

## Scope

This package implements document intelligence through LLM preparation:

1. Document Loading (txt, pdf, docx, html)
2. Document Cleaning
3. Section Extraction
4. Clause Extraction
5. Document understanding, context, entities, then LLM preparation → `SemanticExtractionInput`

`document-pipeline preview <file>` runs the orchestrator end-to-end and writes `output/DOC_*.json`.

Out of scope in this package: compliance engine, APIs, and an app database. Embeddings/Qdrant live in `vectorization/`; GraphIR/Neo4j live in `graph_builder/` and `semantic_graph/`.

## Project layout

```
document_pipeline/
├── src/document_pipeline/
│   ├── config/        # Centralized configuration
│   ├── constants/     # Shared constants
│   ├── core/          # Base abstractions and shared exceptions
│   ├── models/        # Domain-specific pipeline data models
│   ├── parsers/       # txt, pdf, docx, html
│   ├── validators/    # Input/output validators
│   ├── serializers/   # Artifact serialization
│   ├── semantic/      # Semantic extraction services (future)
│   ├── prompts/       # Prompt templates (future)
│   ├── pipeline/      # Stage interfaces and orchestration
│   ├── services/      # Cross-cutting service abstractions
│   ├── utils/         # Shared utilities (logging)
│   └── cli/           # Command-line entry point
├── tests/             # pytest test suite
└── data/              # Sample and runtime data directories
```

## Requirements

- Python 3.12+

## Setup

```bash
cd document_pipeline
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Running tests

```bash
pytest --ignore=tests/test_loader.py   # test_loader needs reportlab (in [dev])
```

Heading regression fixtures live in `tests/fixtures/policies/` (`.txt` + `.expected.json`).

## Status

Orchestrator runs end-to-end from load through `DefaultLLMPreparer`. Preview CLI writes JSON with clauses, classifications, and entities. Formats: `.txt`, `.pdf`, `.docx`, `.html` / `.htm`. Parsed artifacts are JSON files under `output/` — there is no SQLite store in this package.
