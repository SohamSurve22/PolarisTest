# PolarisLex

Legal-document intelligence for Indian website-privacy law. Upload a private-company privacy policy; the app **validates** it against DPDP, SPDI Rules, CERT-In, and the IT Act, and can **answer statute questions** from the Queries tab (no PDF required).

The stack **parses** documents, **embeds** law text for search, can **export** a graph to Neo4j, **compares** a policy to those statutes, **analyzes** obligation gaps with linked penalties, and can **write a client memo + PDF** from those findings (India MVP). `/analyze` does **not** traverse Neo4j. Memo Themes and the first summary sentence come from the engine, not Qwen.

Two surfaces in the UI:

| Tab | Needs a policy? | What it does |
|---|---|---|
| **Validation** | Yes | Score this document against GraphIR duties (`POST /compare` then `/analyze`, then `/report`). Coverage strip, graphs, Findings, memo. |
| **Queries** | No | Statute Q&A (`POST /rag`). Dense retrieve from merged law JSON; optional Graph retrieve. Not chat-with-PDF and not a policy score. |

## Quick start (product UI)

Requires [Docker Desktop](https://docs.docker.com/get-docker/) (macOS, Windows, or Linux) and **Ollama on the host** — not inside Compose. Models are too large to put in `pip` or the API image.

Do this in order every time you start the project. Ollama must be up **before** Compose; the API reaches it at `http://host.docker.internal:11434`. Without it, `/analyze` and Queries return **503**.

### 1. Start Ollama (host, not Docker)

If the models are **already installed**, do **not** run `./scripts/setup-ollama.sh` again. Start the Ollama process; it serves whatever is already on disk. Weights load into memory on the first `/analyze` or Queries call.

If the Ollama desktop app is already running, skip `ollama serve`.

**macOS / Linux**

```bash
ollama serve
```

Leave that terminal open. In another terminal:

```bash
ollama list
curl http://localhost:11434/api/tags
```

`list` should show `nomic-embed-text` and `qwen2.5:7b-instruct-q4_K_M`. That is enough to “up” the models — they are installed. Ollama loads each one when the API first asks for it. Optional, to load them into RAM now (avoids a slow first Validation/Queries request):

```bash
curl http://localhost:11434/api/embeddings -d '{"model":"nomic-embed-text","prompt":"ok"}'
curl http://localhost:11434/api/generate -d '{"model":"qwen2.5:7b-instruct-q4_K_M","prompt":"ok","stream":false}'
ollama ps    # both should appear as loaded
```

If `ollama` is missing, or `list` is empty, do **First-time setup** below (install + pull), then come back to this step.

**Windows.** Open the **Ollama app** (do not run it only inside WSL). Confirm with `curl.exe http://localhost:11434/api/tags`. Docker reaches the host at `http://host.docker.internal:11434`. Same rule: if `ollama list` already shows both models, skip the pull script.

### 2. Start the app containers

From the **repo root**:

```bash
docker compose up --build web api
```

Qdrant starts with `api`. Open [http://localhost:8080](http://localhost:8080). The API is [http://localhost:8000](http://localhost:8000) (`GET /health`, `POST /compare`, `POST /analyze`, `POST /report`, `POST /report.pdf`, `POST /rag`).

`--build` is needed after you change `web/`, `policy_compare/`, `compliance/`, `document_pipeline/`, `vectorization/`, `graph_builder/`, `rag/`, or the Dockerfiles.

**Stop.** Ctrl+C in the Compose terminal (or `docker compose down`). Then stop Ollama: Ctrl+C in the `ollama serve` terminal, or quit the Ollama app on Windows.

### First-time setup (once per machine)

Ollama is the local runtime. PolarisLex does **not** use Meta Llama weights; the setup script pulls **nomic-embed-text** (embeddings) and **Qwen 2.5 7B** (chat).

#### Install Ollama

**macOS**

```bash
brew install ollama          # or the installer at https://ollama.com/download
ollama serve                 # skip if the Ollama app is already running
```

**Linux**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve                 # skip if already running as a service
```

**Windows** (no Homebrew). Install [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/) and **Ollama for Windows** (the `.exe` from [ollama.com/download/windows](https://ollama.com/download/windows), **not** inside WSL). If you install Ollama only inside WSL, Compose often cannot see it.

#### Pull models (skip if `ollama list` already shows both)

Only needed the first time, or after you deleted the models. From the **repo root**, with `ollama` on PATH and `ollama serve` (or the app) already running:

**macOS / Linux**

```bash
./scripts/setup-ollama.sh
```

That script runs `ollama pull` for both models (~270MB + ~5GB). Keep Ollama running afterward, then start Compose (step 2 above).

**Windows** (PowerShell, repo root):

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup-ollama.ps1
```

The PowerShell script uses `winget install Ollama.Ollama` if `ollama` is not on PATH, then pulls the same two models. After a fresh install, **open the Ollama app once** (or sign out/in) so `ollama` is on PATH.

| Model | Used for |
|---|---|
| `nomic-embed-text` | `/analyze` search, `vectorization` ingest, Queries retrieve |
| `qwen2.5:7b-instruct-q4_K_M` | Queries answers; optional extra memo sentences after the engine scoreboard. Duty table, Themes, scoreboard, and PDF still work if chat is down. |

Manual pull (same as the script):

```bash
ollama pull nomic-embed-text
ollama pull qwen2.5:7b-instruct-q4_K_M
```

### 3. Index law vectors (first machine, once)

`/analyze` and Queries need Qdrant points. Ollama must be running on the host (`nomic-embed-text`). From the repo root, with a venv:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e vectorization -e document_pipeline

cd vectorization
vectorization ingest-kg
vectorization ingest-rag --path ../dataset/IT_ACT_POLARISLEX_MERGED.json
```

- `ingest-kg` loads `kg_export/*.json` as `kg_obligation` / `kg_section` (Validation + Graph Queries).
- `ingest-rag` loads `dataset/IT_ACT_POLARISLEX_MERGED.json` as `rag_section` (Dense Queries). Do **not** ingest that file as `kg_obligation`.

Re-run those two commands after law JSON or embed-model changes. Analyze does **not** upsert the uploaded policy into Qdrant.

## Using the UI

**Validation** — drop or paste a policy (`.txt`, `.pdf`, `.docx`, `.html`). After validation:

1. **Coverage strip** — covered / partial / missing / violation / conflict / N/A from analysis (not keyword overlay). Same strip stays on the Report page.
2. **User Graph** and **Ideal Graph** — node colors follow the same result.
3. **Findings** — each row is a law duty plus the closest policy clause. Click a row to highlight those nodes. **View Report** opens the memo (`#report`).
4. **Report** — engine scoreboard + Themes, optional Qwen remainder, priority gaps, duties grouped by law. **Download PDF** is on that page. **Back to Findings** returns to the graphs.

**Load policy** in the header replaces the current file. Switching to Queries does **not** clear a loaded policy.

**Queries** — header tab (or [http://localhost:8080/#queries](http://localhost:8080/#queries)). No file required. Ask a statute question; Dense is the default retriever, Graph is a toggle. Answers cite statute ids. This is law text, not a score of an uploaded notice.

### Compare vs analyze vs rag

| Endpoint | Needs Qdrant / Ollama | What it does |
|---|---|---|
| `POST /compare` | No | Parse the file, draw both graphs. Topic **keywords** only group User Graph folders (Consent vs Extra). Not the coverage score or node colors. |
| `POST /analyze` | Yes (`nomic-embed-text`) | Build GraphIR from the law JSON (Obligation nodes). Score policy clauses against `kg_obligation` (multi-credit + title/element gate). N/A duties skip scoring. Penalties walk GraphIR `PENALIZES`. Not statute Q&A. The HTTP handler leaves the optional policy-graph builder unset, so the response has `policy_graph: null`. |
| `POST /report` | Chat optional | Assemble the client memo from `AnalysisResult`. Themes and the first summary sentence are engine-owned. If Qwen is down: **200** with `narrative_available: false`. |
| `POST /report.pdf` | No | Render the assembled report (no second chat call). |
| `POST /rag` | Yes (embed + Qwen) | Statute Q&A. `mode=dense` retrieves `rag_section`; `mode=graph` seeds `kg_obligation` and expands GraphIR. The Queries tab calls this. Does not score a policy and does not feed the memo. |

The Validation UI calls `/compare`, then `/analyze` on the same file, then `POST /report`. Findings show first; the memo narrative can take up to about a minute (local Qwen). If search is down, `/analyze` returns **503**; graphs still load. Queries returns **503** if Qdrant or Ollama is down.

### Policy graph (optional)

`graph_builder` can turn a parsed policy into GraphIR with the existing label and relation vocabulary. `OpenIEExtractor` asks local Ollama (same `LLMClient` as the graph builder, Qwen) for subject–predicate–object JSON only. `PolicyGraphBuilder` maps those phrases through `entity_aliases.json` / `relation_aliases.json` and `ALLOWED_TRIPLES` in `ontology.py`. Phrases that do not map (`owns`, `sells`, unknown entities) stay on `MappingFailure` (`UNMAPPED_ENTITY`, `UNMAPPED_RELATION`, `AMBIGUOUS_*`, `INVALID_RELATION_COMBINATION`).

Pass `policy_builder=` into `GraphBuilderPipeline` to use that path instead of one-shot `LLMGraphBuilder` GraphIR. Pass the same builder into `analyze_document` to fill `AnalysisResult.policy_graph` and `mapping_failures`. Covered, partial, missing, violation, and conflict still come from Qdrant credits and `classify`. The Validation strip does not read those fields.

The API in Docker reaches Ollama at `http://host.docker.internal:11434`.

## What you get

| Package | Role |
|---|---|
| `document_pipeline/` | File → structured `DOC_*.json` (sections, clauses, entities) |
| `policy_compare/` | Overlay compare; FastAPI (`/compare`, `/analyze`, `/report`, `/rag`) |
| `compliance/` | India obligation / gap / penalty findings (`AnalysisResult`) and client memo + PDF |
| `rag/` | Statute Q&A: dense vs GraphRAG (`POST /rag`). Not used by `/analyze`. |
| `vectorization/` | Embed clauses and law JSON into Qdrant (local Ollama by default) |
| `graph_builder/` | GraphIR schema, Cypher, optional Neo4j load, `kg_export` dump, optional OpenIE policy graph |
| `semantic_graph/` | Hierarchy builder, `dump-ir`, Neo4j export |
| `web/` | Validation workspace + Queries tab (`localhost:8080`) |

Law sources (already tagged): `dataset/dpdp_graph.json`, `dataset/spdi_graph.json`, `dataset/certin_graph.json`, `dataset/itact_graph.json`. Dense Q&A corpus: `dataset/IT_ACT_POLARISLEX_MERGED.json`. Sample policies for live Validation: `test_policy/` (`.pdf`).

**Stores:** parsed JSON under `document_pipeline/output/`, Qdrant, optional Neo4j. No SQLite or Postgres. Embeddings default to local Ollama (`nomic-embed-text`).

### Ports (Compose)

| Port | Service |
|---|---|
| 8080 | Product UI (nginx → `web/`) |
| 8000 | FastAPI (`policy_compare`) |
| 11434 | Ollama on the **host** (`ollama serve` — not a Compose service) |
| 6333 | Qdrant HTTP / dashboard |
| 6334 | Qdrant gRPC |
| 7474 | Neo4j Browser (HTTP) |
| 7687 | Neo4j Bolt (drivers) |

Neo4j is **not** used by `/compare`, `/analyze`, or Queries. The UI never opens Neo4j Browser. 7474 is the web console; 7687 is what Python drivers use later.

## Requirements

- **UI:** Docker (Compose)
- **Python packages:** Python 3.12+
- **Host runtime:** `ollama serve` (or the Ollama app) on `:11434` before Compose
- **Analyze / ingest / Queries retrieve:** Ollama `nomic-embed-text` (`./scripts/setup-ollama.sh`)
- **Queries answers / extra memo sentences:** `qwen2.5:7b-instruct-q4_K_M` (same script)
- Sentence Transformers is an optional embed fallback (`vectorization/`)

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
vectorization ingest-rag --path ../dataset/IT_ACT_POLARISLEX_MERGED.json
vectorization search "consent" --source-type kg_obligation --top-k 5

# Statute Q&A bench (does not replace /analyze)
cd ../rag && pip install -e ".[dev]"
rag-bench

# Graph without Neo4j
semantic-graph dump-ir statute.txt -o ir.json
semantic-graph from-catalog dataset/dpdp_graph.json dataset/spdi_graph.json dataset/certin_graph.json dataset/itact_graph.json -o catalog-ir.json
graph-builder-export-kg ir.json -o ../kg_export/LAW.json --law-code LAW

# Graph into Neo4j
semantic-graph export statute.txt
```

Package READMEs have setup, env vars, and tests:

- [`document_pipeline/README.md`](document_pipeline/README.md)
- [`vectorization/README.md`](vectorization/README.md)
- [`graph_builder/README.md`](graph_builder/README.md)
- [`compliance/`](compliance/) (India analyze; hosted by `policy_compare` FastAPI)
- [`rag/README.md`](rag/README.md) (statute Q&A; Queries tab uses `POST /rag`)

How the pieces join: [`ARCHITECTURE.md`](ARCHITECTURE.md). Roadmap: [`plan.md`](plan.md).

**Next:** Optional [cloud chat](plan.md#b--report-polish) is still later. Cypher at analyze time and `applies_if` are still later.

## Not in this build

- Overlay clustering stays topic **keywords** (Consent vs Extra) — skipped embeddings for folders
- Chat-with-PDF RAG (Queries is statute Q&A only; Validation scores the upload)
- Neo4j / Cypher at `/analyze` (engine uses in-process GraphIR + Qdrant; no Bolt)
- `applies_if` / NOT_APPLICABLE (child-under-18, DPO, consent manager)
- LLM rewrite of retrieval text
- Pluggable jurisdictions beyond India website-privacy MVP
- Durable reports store (optional `POLARIS_REPORT_DIR` JSON files only; no SQLite)
- Cloud chat (local Ollama only; compact report JSON stays on the machine)

`/analyze` is a retrieval score against GraphIR duties, not a legal opinion. Findings copy can name the statute (`This clause satisfies {act}: {title}`) from engine rows. That is attribution, not a precondition check.
