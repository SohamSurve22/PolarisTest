# Client-facing compliance report (UI memo + PDF)

Date: 2026-08-30

A keepable PolarisLex memo: on-screen preview plus a downloadable PDF. The Findings table stays the interactive graph picker. The report is the document a person would send or file.

## Locked decisions

- Full memo in the UI **and** a **PDF download** (not Markdown).
- Audience: **client-facing** — cover, counts, narrative, full duty list, caveat on every PDF page. Still not legal advice.
- **Hybrid:** engine owns every status, score, closest clause, and penalty. Qwen only writes `executive_summary` and one short `note` per applicable law.
- PDF is rendered from the assembled `ComplianceReport` only. Download does **not** call the chat model again.
- If Ollama chat is down, preview and PDF still build from the engine table, with a one-line “narrative unavailable.”
- ReportLab on the API (already a `document_pipeline` extra; add it to the API image). No WeasyPrint, no browser-print-as-the-product.
- No reports database. Optional `POLARIS_REPORT_DIR` JSON persist can remain for the JSON object; PDF is generated on demand.

## Non-goals

- Markdown export, email send, letterhead/logo branding pack.
- Letting the model invent, drop, or change obligation ids or statuses.
- Replacing Findings (click-to-graph). The memo is a copy; Findings stay for navigation.
- SQLite / app DB.

## Why the current report is weaker than Findings

`POST /report` sends a capped gap list (12 rows) and asks Qwen for a 120-word summary plus a few highlights. The Findings table lists every duty. A client copy must include **all** engine rows. Prose is extra; it is not the source of coverage.

## Document contents

1. **Cover** — “PolarisLex”, document id, generated date (UTC), jurisdiction, applicable laws, counts (covered / partial / missing / total).
2. **Executive summary** — Qwen; balanced (what is in place, weak, missing). If chat failed: one sentence that narrative is unavailable; table still follows.
3. **By law** — for each act in `applicable_laws`: Qwen paragraph (dropped if the act is not in that list), then the **full** duty table for that act: status, duty title, obligation id, closest policy section + clipped clause (same 180-char clip as Findings).
4. **Penalties** — only rows with `amount_crore` or `imprisonment_years` set, ids that exist on engine obligations.
5. **PDF footer every page** — “Not a legal opinion. Coverage statuses are from automated analysis, not the language model.”

Filename: `polarislex-{document_id}.pdf`.

## Data model

Replace highlight-only teaser fields. `ComplianceReport` becomes self-contained:

| Field | Source |
|---|---|
| `document_id`, `jurisdiction`, `applicable_laws` | engine |
| `generated_at` | server clock, ISO-8601 UTC |
| `model` | `POLARIS_CHAT_MODEL` or empty if narrative skipped |
| `counts` | covered / partial / missing / total from obligations |
| `executive_summary` | Qwen, or empty when narrative unavailable |
| `narrative_available` | bool |
| `law_notes` | `{act, note}` only for acts in `applicable_laws`; invented acts dropped |
| `findings` | **all** `ObligationFinding` rows copied from analysis (status, score, matched clauses, titles) |
| `penalties` | engine penalties with a scored amount or imprisonment |
| `caveats` | existing fixed string |

`ReportHighlight` is removed from the live report object (tests and UI that read `highlights` switch to `law_notes` + `findings`).

Chat JSON schema (model output only):

```json
{
  "executive_summary": "string",
  "law_notes": [{"act": "string", "note": "string"}]
}
```

Compact chat payload: overall counts, per-law counts, **titles** of covered / partial / missing (not 63 full snippets). Snippets live on `findings` for the PDF/UI, not in the prompt. Cap prompt size by sending titles only; do not cap the assembled `findings` list.

## API

- `POST /report` — body `AnalysisResult` → `ComplianceReport` JSON. **Does not 503** when chat fails; `narrative_available: false` and engine fields still filled. 422 on invalid body.
- `POST /report.pdf` — body `ComplianceReport` → `application/pdf`. Deterministic. Same JSON twice → equivalent PDF. `Content-Disposition: attachment; filename="polarislex-{document_id}.pdf"`. 422 if `findings` is missing or empty while the analysis had obligations (client must send the assembled report, not the old highlight teaser).
- Nginx already has `proxy_read_timeout 200s` on `/api/`; PDF render is short. Chat still uses the existing timeout on `/report`.

UI flow stays: compare → analyze → `POST /report` with analyze JSON. Download: `POST /api/report.pdf` with the in-memory report JSON (blob download). No second analyze.

## UI

`ReportPanel` becomes a memo preview: cover counts, summary (or fallback line), per-law notes, full duty list grouped by act (same badges as Findings). **Download PDF** button when a report object exists (including narrative-unavailable). Findings table unchanged below (or beside) for graph focus.

Do not hide covered rows in the memo.

## PDF layout (ReportLab)

- A4, portrait, consistent header (PolarisLex + document id) and footer (caveat + page n of m).
- Status labels as text (COVERED / PARTIAL / MISSING), not color-only.
- Tables wrap long titles; do not drop rows to fit a page.
- No images/fonts beyond ReportLab built-ins (Helvetica) so the slim API image stays simple.

## Files (expected)

| File | Role |
|---|---|
| `compliance/src/compliance/models.py` | Richer `ComplianceReport`; drop live `ReportHighlight` |
| `compliance/src/compliance/report.py` | Compact prompt, assemble findings, optional chat |
| `compliance/src/compliance/pdf.py` | `render_pdf(report) -> bytes` |
| `compliance/tests/test_report.py` | Assembly, invented acts dropped, chat-down still returns findings |
| `compliance/tests/test_pdf.py` | Bytes start with `%PDF`; all obligation ids appear in extracted text |
| `policy_compare/src/policy_compare/api.py` | `POST /report.pdf` |
| `policy_compare/tests/test_api.py` | PDF content-type; report 200 when chat raises |
| `compliance/pyproject.toml` + API image | `reportlab` dependency |
| `web/src/ReportPanel.jsx` + CSS | Memo preview + download |
| `plan.md` / README | Report is a client memo + PDF, not a gap teaser |

## Tests (must pass)

- Assembled `findings` length and statuses equal `analysis.obligations`; chat stub cannot add/remove ids.
- `law_notes` with unknown `act` dropped.
- Chat `ReportError` or empty `executive_summary` → `narrative_available` false, findings still complete (no 503).
- `render_pdf` returns `%PDF` and includes every `obligation_id`.
- API: `/report.pdf` 200 + `application/pdf`; `/report` 200 when chat is patched to fail.

## Out of scope later

Native branded template, i18n, per-recipient redaction, storing PDFs on disk.
