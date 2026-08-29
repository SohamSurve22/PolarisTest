# PolarisLex

Legal-document intelligence for Indian privacy law. Upload a private-company website privacy policy and overlay it against an ideal topic graph drawn from DPDP, SPDI Rules, CERT-In directions, and the IT Act.

The stack **parses** documents, can **embed** clauses for search, can **export** a graph, can **compare** a policy to those statutes, and can **analyze** obligation gaps and linked penalties (India MVP). It does **not** yet generate LLM reports or traverse Neo4j obligations.

## Quick start (product UI)

Requires [Docker](https://docs.docker.com/get-docker/). From the repo root:

```bash
docker compose up --build web api
```

Open [http://localhost:8080](http://localhost:8080). Landing: drop or paste a policy; after compare, graphs and a coverage strip fill the page (**Load policy** in the header to replace it). Formats: `.txt`, `.pdf`, `.docx`, `.html`. The API listens on [http://localhost:8000](http://localhost:8000) (`GET /health`, `POST /compare`, `POST /analyze`).

`--build` is only needed after you change `web/`, `policy_compare/`, `compliance/`, `document_pipeline/`, `vectorization/`, or the Dockerfiles. Stop with `docker compose down`.

Graphs from `/compare` work without Qdrant or Ollama (keyword overlay). `/analyze` needs Qdrant (Compose starts it with `api`) and **Ollama on the host** (`nomic-embed-text`) so the API container can reach `http://host.docker.internal:11434`. The index must already contain `kg_obligation` points (from `vectorization ingest-kg` / `reembed`). If search is down, the inspector shows an analysis error; the graphs stay.

## What you get

| Package | Role |
|---|---|
| `document_pipeline/` | File → structured `DOC_*.json` (sections, clauses, entities) |
| `policy_compare/` | Ideal topic graph + overlay match; FastAPI `POST /compare` and `POST /analyze` |
| `compliance/` | India obligation / gap / penalty findings |
| `web/` | React UI: landing, graphs, inspector |
| `vectorization/` | Embed clauses into Qdrant (local Ollama by default) |
| `graph_builder/` | GraphIR schema, Cypher, optional Neo4j load, `kg_export` dump |
| `semantic_graph/` | Hierarchy builder, `dump-ir`, Neo4j export |

Law sources (already tagged): `dpdp_graph.json`, `spdi_graph.json`, `certin_graph.json`, `itact_graph.json`.

**Stores:** parsed JSON under `document_pipeline/output/`, Qdrant at `localhost:6333`, Neo4j at `localhost:7474` (Bolt `7687`). No SQLite or Postgres. Embeddings default to local Ollama (`nomic-embed-text`).

## Requirements

- **UI:** Docker (Compose)
- **Python packages:** Python 3.12+
- **Vector search:** Docker Qdrant + [Ollama](https://ollama.com/) with `nomic-embed-text` (or Sentence Transformers; see `vectorization/`)

## Optional: vectors and Neo4j

```bash
docker compose up -d qdrant neo4j
```

Qdrant dashboard: [http://localhost:6333/dashboard](http://localhost:6333/dashboard). Neo4j Browser: [http://localhost:7474](http://localhost:7474) (auth is in `docker-compose.yml`).

```bash
docker compose up --build   # web, api, qdrant, and neo4j together
```

## Python CLIs (local packages)

Each package is independently installable (`pip install -e ".[dev]"` from that directory). Typical flow:

```bash
# Parse
cd document_pipeline && pip install -e ".[dev]"
document-pipeline preview path/to/policy.txt

# Vectors (Qdrant + Ollama must be running)
cd ../vectorization && pip install -e ../document_pipeline -e ".[dev]"
vectorization
vectorization search "personal data" --top-k 5

# Graph without Neo4j
semantic-graph dump-ir statute.txt -o ir.json
graph-builder-export-kg ir.json -o ../kg_export/LAW.json --law-code LAW

# Graph into Neo4j
semantic-graph export statute.txt
```

Package READMEs have setup, env vars, and tests:

- [`document_pipeline/README.md`](document_pipeline/README.md)
- [`vectorization/README.md`](vectorization/README.md)
- [`graph_builder/README.md`](graph_builder/README.md)
- [`compliance/`](compliance/) (India analyze; hosted by `policy_compare` FastAPI)

How the pieces join: [`ARCHITECTURE.md`](ARCHITECTURE.md). Roadmap: [`plan.md`](plan.md).

## Not in this build

- Neo4j obligation traversal (GraphIR dump still has no Obligation nodes)
- Report generation and a reports database
- Hybrid graph + vector fusion at query time
- LLM rewrite of retrieval text
- Pluggable jurisdictions beyond India website-privacy MVP

The overlay graphs are **topic coverage** (keywords), not a legal determination. `/analyze` scores clauses against indexed obligations; it is still not a legal opinion.
