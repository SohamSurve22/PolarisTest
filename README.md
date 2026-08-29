# PolarisLex

Legal-document intelligence for Indian privacy law. Upload a private-company website privacy policy and overlay it against an ideal topic graph drawn from DPDP, SPDI Rules, CERT-In directions, and the IT Act.

The stack **parses** documents, can **embed** clauses for search, can **export** a graph, and can **compare** a policy to those statutes. It does **not** yet run a full compliance engine, compute penalties, or generate reports.

## Quick start (product UI)

Requires [Docker](https://docs.docker.com/get-docker/). From the repo root:

```bash
docker compose up --build web api
```

Open [http://localhost:8080](http://localhost:8080). Landing: drop or paste a policy; after compare, graphs and a coverage strip fill the page (**Load policy** in the header to replace it). Formats: `.txt`, `.pdf`, `.docx`, `.html`. The API listens on [http://localhost:8000](http://localhost:8000) (`GET /health`, `POST /compare`).

`--build` is only needed after you change `web/`, `policy_compare/`, `document_pipeline/`, or the Dockerfiles. Stop with `docker compose down`.

Qdrant and Neo4j are **not** required for this UI. The compare path reads the four law JSON files at the repo root and matches policy headings to topics with keywords (no Ollama).

## What you get

| Package | Role |
|---|---|
| `document_pipeline/` | File → structured `DOC_*.json` (sections, clauses, entities) |
| `policy_compare/` | Ideal topic graph + overlay match; FastAPI `POST /compare` |
| `web/` | React UI: landing, then side-by-side graphs |
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

How the pieces join: [`ARCHITECTURE.md`](ARCHITECTURE.md). Roadmap: [`plan.md`](plan.md).

## Not in this build

- Compliance engine (applicable law → obligations → gaps → penalties)
- Report generation and a reports database
- Hybrid graph + vector fusion at query time
- LLM rewrite of retrieval text

The overlay UI is **topic coverage**, not a legal determination.
