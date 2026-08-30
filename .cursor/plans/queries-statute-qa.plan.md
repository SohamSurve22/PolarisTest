# Queries tab statute Q&A

> **For agentic workers:** Use executing-plans or implement task-by-task. Copy this plan to [`.cursor/plans/queries-statute-qa.plan.md`](.cursor/plans/queries-statute-qa.plan.md) (repo). Do not edit `docs/superpowers/specs/`.

**Goal:** Let a user ask statute questions from the Queries tab without loading a policy. Answers come from existing `POST /rag` (dense default, optional graph).

**Architecture:** The header already lists Queries but every item except Validation is a non-clickable `span`. Make Validation and Queries real tabs. Queries renders a new panel that `POST`s `{ question, mode }` to `/api/rag` (Vite already rewrites `/api` → FastAPI). Do not upsert the upload, do not search `document_clause`, do not feed the memo.

**Tech stack:** React (existing Vite app), existing FastAPI `/rag`, local Qwen via Ollama (already required by the API).

**Constraints:**
- Statute Q&A only. Copy must say this is law text, not a policy score.
- Dense default (12/12 gold recall). Graph is a toggle, not the default.
- Do not change `duty_rules.json`, `/analyze`, or ingest-on-upload.
- No new web test runner (web has no Vitest). Verify with `npm run build` and a browser pass.
- Existing API tests in [`policy_compare/tests/test_api.py`](policy_compare/tests/test_api.py) already cover 200/503; do not duplicate unless the request shape changes.

## Files

- [`web/src/Header.jsx`](web/src/Header.jsx) — clickable Validation + Queries; `current` from props
- [`web/src/App.jsx`](web/src/App.jsx) — `tab` state (`validation` | `queries`); `#queries` hash; keep compare/analyze state when switching
- [`web/src/PageHead.jsx`](web/src/PageHead.jsx) — Queries title/meta; hide Run Validation on this tab
- **New** [`web/src/QueriesPanel.jsx`](web/src/QueriesPanel.jsx) — question, Dense/Graph, answer, citations, timings, 503
- [`web/src/index.css`](web/src/index.css) — panel layout using existing tokens (no new color palette)
- [`plan.md`](plan.md) — Q&A RAG row: web Queries panel exists; still not chat-with-PDF

Leave Dashboard / Documents / Parser / Knowledge Graph as idle labels.

## UI behavior

Queries is available on the landing screen (no file required). Switching tabs must not clear a loaded policy.

Panel:
- Textarea + Ask (disabled while in flight)
- Dense | Graph toggle (Dense default)
- Optional example chips from gold questions (withdraw consent, 43A, CERT-In 6 hours) — fill the box, do not auto-submit
- Loading: generate is ~4–7s; show retrieve/generate ms after success
- Answer + citation id, title, score; excerpt collapsed or truncated
- 503: “Q&A backend unavailable (Qdrant or Ollama).”
- Empty question: client-side error, no request

Hash: `#queries` like existing `#report`. `#report` stays Validation-only.

## Out of scope

Policy-clause retrieve, ingest-on-analyze, chat history persistence, streaming tokens, changing `/rag` request/response.
