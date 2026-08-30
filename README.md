# PolarisLex

Legal-document intelligence for Indian website-privacy law. Upload a private-company privacy policy; the app builds two graphs and scores the text against DPDP, SPDI Rules, CERT-In directions, and the IT Act.

The stack **parses** documents, **embeds** clauses for search, can **export** a graph to Neo4j, **compares** a policy to those statutes, **analyzes** obligation gaps with linked penalties, and can **write a client memo + PDF** from those findings (India MVP). `/analyze` does **not** traverse Neo4j. Memo Themes and the first summary sentence come from the engine, not Qwen.

## Quick start (product UI)

Requires [Docker Desktop](https://docs.docker.com/get-docker/) (macOS or Windows) and **Ollama on the host** — not inside the Compose file. Models are too large to put in `pip` or the API image.

### 1. Host Ollama

Same two models on every laptop:

| Model | Used for |
|---|---|
| `nomic-embed-text` | `/analyze` embeddings (~270MB) |
| `qwen2.5:7b-instruct-q4_K_M` | Optional extra memo sentences after the engine scoreboard (~5GB). Duty table, Themes, scoreboard, and PDF still work without it. |

**macOS**

```bash
brew install ollama          # or the installer at https://ollama.com/download
ollama serve                 # skip if the Ollama app is already running
./scripts/setup-ollama.sh
```

**Windows** (no Homebrew). Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) and **Ollama for Windows** (the `.exe` from [ollama.com/download/windows](https://ollama.com/download/windows), not inside WSL). Then in PowerShell from the repo root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-ollama.ps1
```

That script uses `winget install Ollama.Ollama` if `ollama` is not on PATH, then pulls both models. After a fresh install, **open the Ollama app once** (or sign out/in) so `ollama` is on PATH, and keep it running.

Docker on Windows reaches the host at `http://host.docker.internal:11434` the same way macOS does. If you install Ollama *inside* WSL instead of the Windows app, Compose often cannot see it; use the Windows installer.

Confirm:

```bash
ollama list
curl http://localhost:11434/api/tags
```

On Windows PowerShell, `curl.exe http://localhost:11434/api/tags` (or a browser).

### 2. App containers

From the repo root:

```bash
docker compose up --build web api
```

Open [http://localhost:8080](http://localhost:8080). Drop or paste a policy (`.txt`, `.pdf`, `.docx`, `.html`). After validation:

1. **Coverage strip** — covered / partial / missing / gaps from analysis (not keyword overlay). Same strip stays on the Report page.
2. **User Graph** and **Ideal Graph** — node colors follow the same result (green covered, orange partial, red missing).
3. **Findings** — table under the graphs. Each row is a law duty plus the closest policy section/clause. Click a row to highlight those nodes. After the memo finishes, **View Report** opens it on its own page (`#report`).
4. **Report** — same coverage strip, then the client memo (upload filename, engine scoreboard + Themes, optional Qwen remainder, priority gaps, every duty grouped by law). **Download PDF** is on that page. Statuses come from analysis, not the model. **Back to Findings** returns to the graphs and table.

**Load policy** in the header replaces the current file. The API is [http://localhost:8000](http://localhost:8000) (`GET /health`, `POST /compare`, `POST /analyze`, `POST /report`, `POST /report.pdf`).

`--build` is only needed after you change `web/`, `policy_compare/`, `compliance/`, `document_pipeline/`, `vectorization/`, `graph_builder/`, or the Dockerfiles. Stop with `docker compose down`.

### Compare vs analyze

| Endpoint | Needs Qdrant / Ollama | What it does |
|---|---|---|
| `POST /compare` | No | Parse the file, draw both graphs. Topic **keywords** only group User Graph folders (Consent vs Extra). Not the coverage score or node colors. |
| `POST /analyze` | Yes | Build GraphIR from the law JSON (Obligation nodes). Score each policy clause against indexed `kg_obligation` vectors. A clause credits only its **best** in-scope hit. **Covered** also needs title-token overlap so generic privacy wording cannot cover an unrelated duty. Gaps = partial + missing. Penalties walk GraphIR `PENALIZES`. |

The UI calls `/compare`, then `/analyze` on the same file, then `POST /report` with the analysis JSON. Findings show first; the memo narrative can take up to about a minute (local Qwen). Memo Themes and the first summary sentence are engine-owned. The Report page reuses the Graph Validation coverage strip (coverage %, covered / partial / missing / gaps). **Download PDF** posts the assembled report to `/report.pdf` (no second chat call). If search is down, `/analyze` returns **503**; graphs still load. If chat is down, `/report` still returns **200** with `narrative_available: false` and the scoreboard sentence; the duty table and PDF still work.

Qdrant starts with `api`. The collection must already contain `kg_obligation` points (`vectorization ingest-kg` / `reembed`). The API reaches Ollama at `http://host.docker.internal:11434`. Analyze does **not** upsert the uploaded policy into Qdrant.

## What you get

| Package | Role |
|---|---|
| `document_pipeline/` | File → structured `DOC_*.json` (sections, clauses, entities) |
| `policy_compare/` | Ideal topic graph + overlay; FastAPI `POST /compare` and `POST /analyze` |
| `compliance/` | India obligation / gap / penalty findings (`AnalysisResult`) and client memo + PDF (`ComplianceReport`) |
| `web/` | React UI: landing, graphs, coverage strip (graphs + report), findings table, memo + PDF |
| `vectorization/` | Embed clauses into Qdrant (local Ollama by default) |
| `graph_builder/` | GraphIR schema, Cypher, optional Neo4j load, `kg_export` dump |
| `semantic_graph/` | Hierarchy builder, `dump-ir`, Neo4j export |

Law sources (already tagged): `dpdp_graph.json`, `spdi_graph.json`, `certin_graph.json`, `itact_graph.json`.

**Stores:** parsed JSON under `document_pipeline/output/`, Qdrant, optional Neo4j. No SQLite or Postgres. Embeddings default to local Ollama (`nomic-embed-text`).

### Ports (Compose)

| Port | Service |
|---|---|
| 8080 | Product UI (nginx → `web/`) |
| 8000 | FastAPI (`policy_compare`) |
| 6333 | Qdrant HTTP / dashboard |
| 6334 | Qdrant gRPC |
| 7474 | Neo4j Browser (HTTP) |
| 7687 | Neo4j Bolt (drivers) |

Neo4j is **not** used by `/compare` or `/analyze`. The UI never opens Neo4j Browser. 7474 is the web console; 7687 is what Python drivers use later.

## Requirements

- **UI:** Docker (Compose)
- **Python packages:** Python 3.12+
- **Analyze / vector search / reports:** Ollama on the host (`nomic-embed-text` now; `qwen2.5:7b-instruct-q4_K_M` for the memo narrative). See Host Ollama above. Sentence Transformers is an optional embed fallback (`vectorization/`).

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
vectorization ingest-kg
vectorization search "consent" --source-type kg_obligation --top-k 5

# Graph without Neo4j
semantic-graph dump-ir statute.txt -o ir.json
semantic-graph from-catalog dpdp_graph.json spdi_graph.json certin_graph.json itact_graph.json -o catalog-ir.json
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

**Next:** Optional [cloud chat](plan.md#b--report-polish) is still later. Cypher at analyze time and `applies_if` are still later.

## Not in this build

- Overlay clustering stays topic **keywords** (Consent vs Extra) — skipped embeddings for folders
- Neo4j / Cypher at `/analyze` (engine uses in-process GraphIR + Qdrant; no Bolt)
- `applies_if` / NOT_APPLICABLE (child-under-18, DPO, consent manager)
- LLM rewrite of retrieval text
- Pluggable jurisdictions beyond India website-privacy MVP
- Durable reports store (optional `POLARIS_REPORT_DIR` JSON files only; no SQLite)
- Cloud chat (local Ollama only; compact report JSON stays on the machine)

`/analyze` is a retrieval score against GraphIR duties, not a legal opinion. Findings copy can name the statute (`This clause satisfies {act}: {title}`) from engine rows. That is attribution, not a precondition check.
