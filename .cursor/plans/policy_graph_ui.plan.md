---
name: Policy graph UI
overview: "Upload a private-company website privacy policy (GitHub, Snap, etc.), show a concise policy graph, and overlay it against one ideal graph of what that policy should cover under DPDP, SPDI, CERT-In, and the IT Act."
todos:
  - id: law-projection
    content: "Add compare package: load 4 law JSON files, filter website-privacy topics, project Topic + LawChunk ideal graph"
    status: pending
  - id: policy-view
    content: Build condensed policy ViewGraph (Introduction for S001, sections as nodes, clauses in detail only)
    status: pending
  - id: matcher
    content: Embed law chunks; match policy sections to topics; assign covered/weak/missing/extra
    status: pending
  - id: api
    content: "FastAPI POST /compare: upload file, run pipeline + compare, return both graphs + links"
    status: pending
  - id: web-ui
    content: "Vite/React Flow UI via Docker Compose (web + api services)"
    status: pending
isProject: true
---

# Policy graph UI and ideal-graph overlay

**Goal:** Someone uploads a **private-company website privacy policy** (GitHub, Snap, or similar). They see a **small readable graph of that policy**, and a **side-by-side overlay** against **one ideal graph**: what a privacy policy for that kind of company website should cover, built from `dpdp_graph.json`, `spdi_graph.json`, `certin_graph.json`, and `itact_graph.json`.

**Not the goal:** Sector products (motor, finance, healthcare, etc.). There is no per-industry gold graph.

**Why Neo4j looks wrong today:** `semantic-graph export` only writes `CONTAINS` + `HAS_CLAUSE`. Unnumbered headings are sibling Sections. Clause stars and blank `S001` (preamble) are layout artifacts. The product UI will **not** use Neo4j Browser.

## Ideal graph: one private-company website privacy profile

The four files are Indian statutes/rules, already tagged with topics (`TOPIC_CONSENT`, …) and chunk types (`obligation`, `right`, …).

The ideal graph answers: **if this is a private company website that collects personal data from users, what must its privacy policy speak to?** Same shape for GitHub, Snap, or any similar company site—not a new graph per brand.

v1 = topic hubs + attached mandatory / obligation / right chunks, filtered to website privacy-policy topics.

Do not dump the whole IT Act. Include IT Act only where it overlaps website privacy.

Default topic set:

- DPDP + SPDI: consent, processing, retention, children, security, user rights, grievance, cross-border, sensitive personal data, disclosure, collection, privacy policy.
- CERT-In (body corporates / online services): incident/breach reporting, log/record retention.
- Drop: governance-only definitions, IT Act procedure/digital-signature topics, generic penalty dumps unless tied to a kept topic.

## Two view graphs

- **Policy view:** Document → Sections. Untitled `S001` caption **Introduction**. Clauses hidden until click.
- **Ideal view:** Topic → LawChunk. Edges are topic membership, not `CONTAINS`.
- **Overlay:** topic `covered` / `missing` / `weak`; policy section `mapped` / `extra`. Match by embeddings + topic tags, not title strings.

## Matching

Load the four law arrays; keep obligation/right/compliance chunks with kept topics; embed summaries into Qdrant (`law_topic_chunk`); vote policy sections onto topics. No LLM obligations, no penalties in v1.

## Product UI

FastAPI `POST /compare` (no Neo4j). Vite + React Flow: two canvases, colors by status. Fixtures: `github_style.txt`, `snap_style.txt`.

## Out of scope

Motor/finance/sector graphs, Neo4j Browser restyle, LLMGraphBuilder, full compliance engine.
