# Document Intelligence Pipeline

Preprocessing pipeline for **PolarisLex** — prepares uploaded legal documents for semantic analysis and Knowledge Graph generation.

## Scope

This package implements stages 1–5 of document intelligence:

1. Document Loading
2. Document Cleaning
3. Section Extraction
4. Clause Extraction
5. LLM Preparation → `SemanticExtractionInput`

Out of scope (implemented later): Compliance Engine, Knowledge Graph, Neo4j, vector search, embeddings, LLM calls, APIs, and database integration.

## Project layout

```
document_pipeline/
├── src/document_pipeline/
│   ├── config/        # Centralized configuration
│   ├── constants/     # Shared constants
│   ├── core/          # Base abstractions and shared exceptions
│   ├── models/        # Domain-specific pipeline data models
│   │   ├── document.py
│   │   ├── section.py
│   │   ├── clause.py
│   │   ├── metadata.py
│   │   └── semantic.py
│   ├── parsers/       # Format-specific document parsers
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
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"
```

## Running tests

```bash
pytest
```

## Status

**Architecture skeleton only** — processing logic is not yet implemented.
