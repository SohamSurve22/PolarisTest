# Client-facing report PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `/report` into a self-contained client memo (all engine findings + optional Qwen prose) and add a deterministic `POST /report.pdf` download plus a matching on-screen preview.

**Architecture:** `generate_report` always copies every `ObligationFinding` (and scored penalties) from `AnalysisResult`. Qwen only fills `executive_summary` and `law_notes`; chat failure sets `narrative_available=false` and does not 503. `render_pdf(report) -> bytes` uses ReportLab from that JSON only. The UI previews the memo and POSTs the same JSON to `/api/report.pdf`.

**Tech Stack:** Python 3.12, pydantic v2, FastAPI, ReportLab 4, React (existing `web/`), pytest. Local Qwen via Ollama remains optional for prose.

## Global Constraints

- Engine owns every status, score, closest clause, and penalty. The model must not add, drop, or change obligation ids or statuses.
- PDF is rendered from `ComplianceReport` only. Download must not call Ollama.
- Chat down: still return a complete report JSON and a valid PDF; `narrative_available` is false.
- ReportLab built-in Helvetica only. A4 portrait. Footer on every page: `Not a legal opinion. Coverage statuses are from automated analysis, not the language model.`
- Filename: `polarislex-{document_id}.pdf`.
- No Markdown export, no reports DB, no WeasyPrint.
- This repo uses 2-space indent in Python and JSX. After Python edits run `./scripts/graphify.sh update .` from the repo root.
- Do not commit unless the user asked; skip Task commit steps if they have not.

**Spec:** `.cursor/plans/2026-08-30-client-facing-report-pdf.md`

---

## File map

| File | Responsibility |
|---|---|
| `compliance/src/compliance/models.py` | `ReportCounts`, `LawNote`, richer `ComplianceReport`; remove `ReportHighlight` |
| `compliance/src/compliance/report.py` | Title-only `compact_payload`, `assemble_report`, optional chat in `generate_report` |
| `compliance/src/compliance/pdf.py` | `render_pdf(report: ComplianceReport) -> bytes` |
| `compliance/src/compliance/__init__.py` | Export `render_pdf` |
| `compliance/pyproject.toml` | Add `reportlab>=4.0.0` |
| `compliance/tests/test_report.py` | Assembly, invented acts, chat-down |
| `compliance/tests/test_pdf.py` | `%PDF` + all obligation ids in bytes |
| `policy_compare/src/policy_compare/api.py` | `/report` no chat-503; `POST /report.pdf` |
| `policy_compare/tests/test_api.py` | 200 when chat patched to fail; PDF content-type |
| `web/src/ReportPanel.jsx` | Memo preview + download |
| `web/src/index.css` | Memo layout |
| `plan.md`, `README.md`, `ARCHITECTURE.md` | Client memo + PDF, not gap teaser |

---

### Task 1: Report models

**Files:**
- Modify: `compliance/src/compliance/models.py`
- Modify: `compliance/src/compliance/__init__.py` (only if you re-export new types; not required)
- Test: `compliance/tests/test_report.py` (add `test_compliance_report_holds_engine_findings`)

**Interfaces:**
- Consumes: existing `ObligationFinding`, `PenaltyFinding`
- Produces:
  - `class ReportCounts(BaseModel)` with `covered`, `partial`, `missing`, `total` ints default 0
  - `class LawNote(BaseModel)` with `act: str`, `note: str = ""`
  - `class ComplianceReport` fields listed below
  - `ReportHighlight` **deleted**

`ComplianceReport` fields:

- `document_id: str`
- `jurisdiction: str = ""`
- `applicable_laws: list[str] = Field(default_factory=list)`
- `generated_at: str = ""`
- `model: str = ""`
- `counts: ReportCounts = Field(default_factory=ReportCounts)`
- `executive_summary: str = ""`
- `narrative_available: bool = False`
- `law_notes: list[LawNote] = Field(default_factory=list)`
- `findings: list[ObligationFinding] = Field(default_factory=list)`
- `penalties: list[PenaltyFinding] = Field(default_factory=list)`
- `caveats: str = "Not a legal opinion. Statuses come from analysis, not the language model."`

- [ ] **Step 1: Write the failing test**

At the top of `compliance/tests/test_report.py` import `ComplianceReport`, `ReportCounts`, `LawNote`. Add:

```python
def test_compliance_report_holds_engine_findings() -> None:
  row = ObligationFinding(
    obligation_id="TINY_SECURE",
    title="Secure personal data",
    act="TINY",
    status="missing",
  )
  report = ComplianceReport(
    document_id="DOC_x",
    jurisdiction="IN",
    applicable_laws=["TINY"],
    generated_at="2026-08-30T05:00:00Z",
    counts=ReportCounts(covered=0, partial=0, missing=1, total=1),
    findings=[row],
    narrative_available=False,
  )
  dumped = report.model_dump()
  assert "highlights" not in dumped
  assert dumped["findings"][0]["obligation_id"] == "TINY_SECURE"
  assert dumped["counts"]["total"] == 1
  assert dumped["narrative_available"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest compliance/tests/test_report.py::test_compliance_report_holds_engine_findings -v`

Expected: FAIL (`ReportCounts` / `LawNote` missing, or `highlights` still on the model).

- [ ] **Step 3: Write minimal implementation**

In `compliance/src/compliance/models.py` delete `ReportHighlight`. Add `ReportCounts` and `LawNote`. Replace `ComplianceReport` with the fields above. Keep `executive_summary` optional-empty (`str = ""`) so a table-only report validates.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest compliance/tests/test_report.py::test_compliance_report_holds_engine_findings -v`

Expected: PASS. Other tests in this file will fail until Task 2–3; that is OK.

- [ ] **Step 5: Commit** (only if the user asked)

```bash
git add compliance/src/compliance/models.py compliance/tests/test_report.py
git commit -m "$(cat <<'EOF'
Add self-contained ComplianceReport fields for the client memo.

EOF
)"
```

---

### Task 2: Assemble engine memo (no chat)

**Files:**
- Modify: `compliance/src/compliance/report.py`
- Modify: `compliance/tests/test_report.py`

**Interfaces:**
- Consumes: `AnalysisResult`, new `ComplianceReport` / `ReportCounts` / `LawNote`
- Produces:
  - `NARRATIVE_UNAVAILABLE = "Narrative unavailable. The table below is from automated analysis only."`
  - `def compact_payload(analysis: AnalysisResult) -> dict`
  - `def assemble_report(analysis: AnalysisResult, *, generated_at: str, model: str = "") -> ComplianceReport`

`compact_payload` must be titles only (no clause snippets, no penalty list):

```python
{
  "document_id": analysis.document_id,
  "jurisdiction": analysis.jurisdiction,
  "applicable_laws": list(analysis.applicable_laws),
  "counts": {"covered": int, "partial": int, "missing": int, "total": int},
  "by_law": [
    {
      "act": "TINY",
      "covered": ["Obtain consent"],
      "partial": [],
      "missing": ["Secure personal data"],
    },
  ],
}
```

Group `by_law` using each obligation’s `act`, in `applicable_laws` order, then any leftover acts sorted. `total` = `len(analysis.obligations)`.

`assemble_report`:

- Copy **all** `analysis.obligations` into `findings` (same objects / model_copy).
- `counts` from those rows.
- `penalties` = analysis penalties where (`amount_crore is not None` or `imprisonment_years is not None`) and `obligation_id` is in the obligation id set.
- `narrative_available=False`, `executive_summary=""`, `law_notes=[]`, `model=""` unless caller sets model later.
- Set `document_id`, `jurisdiction`, `applicable_laws`, `generated_at`.

- [ ] **Step 1: Replace compact-payload tests**

Delete `test_compact_payload_lists_gaps_not_covered_text` and `test_compact_payload_caps_gaps_and_drops_unscored_penalties`. Add:

```python
def test_compact_payload_sends_titles_not_snippets() -> None:
  payload = compact_payload(_analysis())
  blob = json.dumps(payload)
  assert payload["counts"] == {"covered": 1, "partial": 0, "missing": 1, "total": 2}
  assert "We obtain consent" not in blob
  acts = {row["act"]: row for row in payload["by_law"]}
  assert acts["TINY"]["covered"] == ["Obtain consent"]
  assert acts["TINY"]["missing"] == ["Secure personal data"]
  assert "penalties" not in payload


def test_assemble_report_copies_all_findings_and_scored_penalties() -> None:
  from compliance.report import assemble_report

  report = assemble_report(_analysis(), generated_at="2026-08-30T05:00:00Z")
  assert [row.obligation_id for row in report.findings] == ["TINY_CONSENT", "TINY_SECURE"]
  assert report.counts.total == 2
  assert report.counts.covered == 1
  assert report.counts.missing == 1
  assert report.narrative_available is False
  assert [row.obligation_id for row in report.penalties] == ["TINY_SECURE"]
  assert report.penalties[0].amount_crore == 250
```

Add an extra penalty on `_analysis()` or in this test with `amount_crore=None` and assert it is dropped. If `_analysis()` only has the scored penalty, add a second `PenaltyFinding` with `amount_crore=None` inside this test via `model_copy` of the analysis.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest compliance/tests/test_report.py::test_compact_payload_sends_titles_not_snippets compliance/tests/test_report.py::test_assemble_report_copies_all_findings_and_scored_penalties -v`

Expected: FAIL (`assemble_report` missing or old gap-cap payload).

- [ ] **Step 3: Implement `compact_payload` and `assemble_report`**

Rewrite `compliance/src/compliance/report.py`:

- Keep `ReportError`, `SYSTEM` (update in Task 3), `default_chat`, `_parse_json`, `_env_report_dir`.
- Remove `_MAX_GAPS`, `_MAX_PENALTIES`, `_SNIPPET` if unused (clip stays for PDF/UI via finding text already on the model; do not clip in `compact_payload`).
- Implement the two functions above.
- Leave `generate_report` temporarily broken if needed; Task 3 rewrites it. If `generate_report` still references `highlights`, comment it to call `assemble_report` only so the file imports:

```python
def generate_report(analysis, *, chat=None, report_dir=None, model=None, generated_at=None):
  when = generated_at or _now_iso()
  return assemble_report(analysis, generated_at=when, model=model or "")
```

```python
from datetime import datetime, timezone

def _now_iso() -> str:
  return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest compliance/tests/test_report.py::test_compact_payload_sends_titles_not_snippets compliance/tests/test_report.py::test_assemble_report_copies_all_findings_and_scored_penalties compliance/tests/test_report.py::test_compliance_report_holds_engine_findings -v`

Expected: PASS.

- [ ] **Step 5: Commit** (only if the user asked)

```bash
git add compliance/src/compliance/report.py compliance/tests/test_report.py
git commit -m "$(cat <<'EOF'
Assemble the full engine finding list before any LLM prose.

EOF
)"
```

---

### Task 3: Optional Qwen prose

**Files:**
- Modify: `compliance/src/compliance/report.py`
- Modify: `compliance/tests/test_report.py`

**Interfaces:**
- Consumes: `assemble_report`, `compact_payload`, `ChatFn`, `default_chat`
- Produces: `generate_report(analysis, *, chat=None, report_dir=None, model=None, generated_at=None) -> ComplianceReport` that **never raises `ReportError` for bad/missing chat**

`SYSTEM` and `REPORT_SCHEMA`:

```python
SYSTEM = """You write a short client-facing compliance memo from structured analysis JSON.
You must not invent laws, obligation ids, statuses, or penalties.
Statuses in the JSON are already final. Cover what is in place, what is partial, and what is missing.
Return only this object:
{"executive_summary": string, "law_notes": [{"act": string, "note": string}]}
executive_summary under 160 words. Each law note under 60 words. Use only acts listed in applicable_laws.
"""

REPORT_SCHEMA = {
  "type": "object",
  "properties": {
    "executive_summary": {"type": "string"},
    "law_notes": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "act": {"type": "string"},
          "note": {"type": "string"},
        },
        "required": ["act", "note"],
      },
    },
  },
  "required": ["executive_summary", "law_notes"],
}
```

`generate_report` algorithm:

1. `when = generated_at or _now_iso()`
2. `model_name = model or os.environ.get("POLARIS_CHAT_MODEL", DEFAULT_MODEL)`
3. `report = assemble_report(analysis, generated_at=when, model="")`
4. `chat_fn = chat or default_chat`
5. Try `raw = chat_fn(SYSTEM, json.dumps(compact_payload(analysis), ensure_ascii=False))` then `_parse_json`. On `ReportError`, `json.JSONDecodeError`, `TypeError`, `ValueError`, or empty `executive_summary`: leave `narrative_available=False` and skip to persist.
6. On success: `report.executive_summary = summary.strip()`; `report.narrative_available = True`; `report.model = model_name`; `law_notes` = items whose `act` is in `set(analysis.applicable_laws)`.
7. If `report_dir` or `_env_report_dir()` is set, write `{document_id}.json` as today.

- [ ] **Step 1: Write failing tests**

Replace `test_generate_report_uses_chat_json_and_drops_invented_ids`, `test_generate_report_raises_when_chat_returns_garbage`, and `test_generate_report_writes_json_when_dir_set`:

```python
def test_generate_report_uses_law_notes_and_keeps_engine_ids() -> None:
  def chat(_system: str, user: str) -> str:
    assert "Obtain consent" in user
    assert "We obtain consent" not in user
    return json.dumps(
      {
        "executive_summary": "Consent is covered; security is missing.",
        "law_notes": [
          {"act": "TINY", "note": "Security duty is absent."},
          {"act": "FAKE", "note": "Invented statute."},
        ],
      }
    )

  report = generate_report(_analysis(), chat=chat, generated_at="2026-08-30T05:00:00Z")
  assert report.narrative_available is True
  assert "consent" in report.executive_summary.lower()
  assert [row.act for row in report.law_notes] == ["TINY"]
  assert [row.obligation_id for row in report.findings] == ["TINY_CONSENT", "TINY_SECURE"]
  assert report.findings[0].status == "covered"


def test_generate_report_survives_garbage_chat() -> None:
  def chat(_system: str, _user: str) -> str:
    return "not json"

  report = generate_report(_analysis(), chat=chat, generated_at="2026-08-30T05:00:00Z")
  assert report.narrative_available is False
  assert report.executive_summary == ""
  assert len(report.findings) == 2


def test_generate_report_survives_empty_summary() -> None:
  def chat(_system: str, _user: str) -> str:
    return json.dumps({"executive_summary": "  ", "law_notes": [{"act": "TINY", "note": "x"}]})

  report = generate_report(_analysis(), chat=chat)
  assert report.narrative_available is False
  assert report.law_notes == []


def test_generate_report_writes_json_when_dir_set(tmp_path: Path) -> None:
  def chat(_system: str, _user: str) -> str:
    return json.dumps(
      {
        "executive_summary": "Covered consent; missing security.",
        "law_notes": [{"act": "TINY", "note": "Security gap."}],
      }
    )

  report = generate_report(_analysis(), chat=chat, report_dir=tmp_path)
  saved = tmp_path / "DOC_x.json"
  body = json.loads(saved.read_text(encoding="utf-8"))
  assert body["document_id"] == report.document_id
  assert body["narrative_available"] is True
  assert len(body["findings"]) == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest compliance/tests/test_report.py -v`

Expected: FAIL on leftover `highlights` / `pytest.raises(ReportError)` behavior.

- [ ] **Step 3: Implement `generate_report` as specified**

Keep `default_chat` using `format: REPORT_SCHEMA` and `options: {"temperature": 0.2, "num_ctx": 8192}`. `default_chat` may still raise `ReportError`; `generate_report` catches it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest compliance/tests/test_report.py -v`

Expected: all PASS.

- [ ] **Step 5: Commit** (only if the user asked)

```bash
git add compliance/src/compliance/report.py compliance/tests/test_report.py
git commit -m "$(cat <<'EOF'
Keep the memo complete when local chat fails or returns junk.

EOF
)"
```

---

### Task 4: ReportLab PDF

**Files:**
- Modify: `compliance/pyproject.toml` — add `"reportlab>=4.0.0"` to `[project].dependencies`
- Create: `compliance/src/compliance/pdf.py`
- Create: `compliance/tests/test_pdf.py`
- Modify: `compliance/src/compliance/__init__.py` — export `render_pdf`

**Interfaces:**
- Consumes: `ComplianceReport`
- Produces: `def render_pdf(report: ComplianceReport) -> bytes`

PDF rules:

- `SimpleDocTemplate` A4, Helvetica via default stylesheet.
- Header callback: `PolarisLex` and `report.document_id`.
- Footer callback: caveat string **exactly** `Not a legal opinion. Coverage statuses are from automated analysis, not the language model.` plus `page n of m` if easy; at least page number.
- Flowables: title PolarisLex; document id; `generated_at`; jurisdiction; applicable laws; counts line `Covered N · Partial N · Missing N · Total N`.
- Heading Executive summary: if `narrative_available` and summary, print it; else print `NARRATIVE_UNAVAILABLE` from `report.py`.
- For each act in `applicable_laws`: optional matching `law_notes` paragraph; then a table of findings for that act. Columns: Status (text COVERED/PARTIAL/MISSING), Duty title, Id, Closest clause (`section_title` + first matched text clipped to 180 chars, or `No matching clause`).
- Findings whose `act` is not in `applicable_laws` go in a final “Other” section so **no row is dropped**.
- Penalties section only if `report.penalties` non-empty.
- Do not drop rows to fit a page (`repeatRows=1` on tables).

- [ ] **Step 1: Add dependency and failing test**

```toml
dependencies = [
    "httpx>=0.27.0",
    "pydantic>=2.6.0",
    "reportlab>=4.0.0",
    "document-pipeline",
    "policy-compare",
    "vectorization",
]
```

Install: `.venv/bin/pip install -e compliance`

`compliance/tests/test_pdf.py`:

```python
from compliance.models import (
  ComplianceReport,
  LawNote,
  ObligationFinding,
  PenaltyFinding,
  ReportCounts,
)
from compliance.pdf import render_pdf
from compliance.report import NARRATIVE_UNAVAILABLE


def _report() -> ComplianceReport:
  return ComplianceReport(
    document_id="DOC_x",
    jurisdiction="IN",
    applicable_laws=["TINY"],
    generated_at="2026-08-30T05:00:00Z",
    counts=ReportCounts(covered=1, partial=0, missing=1, total=2),
    executive_summary="",
    narrative_available=False,
    law_notes=[LawNote(act="TINY", note="Security is missing.")],
    findings=[
      ObligationFinding(
        obligation_id="TINY_CONSENT",
        title="Obtain consent",
        act="TINY",
        status="covered",
      ),
      ObligationFinding(
        obligation_id="TINY_SECURE",
        title="Secure personal data",
        act="TINY",
        status="missing",
      ),
    ],
    penalties=[
      PenaltyFinding(
        obligation_id="TINY_SECURE",
        title="Fine for insecure processing",
        amount_crore=250,
        act="TINY",
      ),
    ],
  )


def test_render_pdf_contains_all_obligation_ids() -> None:
  pdf = render_pdf(_report())
  assert pdf.startswith(b"%PDF")
  assert b"TINY_CONSENT" in pdf
  assert b"TINY_SECURE" in pdf
  assert b"PolarisLex" in pdf
  assert NARRATIVE_UNAVAILABLE.encode("latin-1") in pdf
  assert b"Not a legal opinion. Coverage statuses are from automated analysis" in pdf
```

If Helvetica encoding rejects a character, keep the fallback sentence ASCII-only (it already is).

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest compliance/tests/test_pdf.py::test_render_pdf_contains_all_obligation_ids -v`

Expected: FAIL (`compliance.pdf` missing) or import error until reportlab is installed.

- [ ] **Step 3: Implement `render_pdf`**

Create `compliance/src/compliance/pdf.py` with the layout above. Export in `__init__.py`:

```python
from compliance.pdf import render_pdf
```

Add `"render_pdf"` to `__all__`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest compliance/tests/test_pdf.py compliance/tests/test_report.py -v`

Expected: PASS.

- [ ] **Step 5: Commit** (only if the user asked)

```bash
git add compliance/pyproject.toml compliance/src/compliance/pdf.py compliance/src/compliance/__init__.py compliance/tests/test_pdf.py
git commit -m "$(cat <<'EOF'
Render the client memo as a ReportLab PDF from assembled findings.

EOF
)"
```

---

### Task 5: FastAPI `/report` and `/report.pdf`

**Files:**
- Modify: `policy_compare/src/policy_compare/api.py`
- Modify: `policy_compare/tests/test_api.py`

**Interfaces:**
- Consumes: `generate_report(analysis) -> ComplianceReport`, `render_pdf(report) -> bytes`
- Produces:
  - `POST /report` body `AnalysisResult` → JSON `ComplianceReport`. **Do not** map chat failure to 503.
  - `POST /report.pdf` body `ComplianceReport` → `application/pdf` with `Content-Disposition: attachment; filename="polarislex-{document_id}.pdf"`

```python
from fastapi.responses import Response
from compliance.models import AnalysisResult, ComplianceReport
from compliance.pdf import render_pdf
from compliance.report import generate_report

@app.post("/report")
def report(body: AnalysisResult) -> dict:
  return generate_report(body).model_dump()

@app.post("/report.pdf")
def report_pdf(body: ComplianceReport) -> Response:
  pdf = render_pdf(body)
  filename = f"polarislex-{body.document_id}.pdf"
  return Response(
    content=pdf,
    media_type="application/pdf",
    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
  )
```

Remove the `ReportError` try/except on `/report`. You can drop the `ReportError` import if unused.

Pydantic 422 handles missing `findings` if the client omits the field **and** you do **not** give `findings` a default. Spec also allows empty findings for an empty analysis. Keep `default_factory=list` so empty analysis still PDFs. Old highlight-only JSON will 422 on unexpected `highlights` if the model forbids extra fields; set `model_config = ConfigDict(extra="ignore")` on `ComplianceReport` **or** leave extra forbidden so stale UI gets 422. Prefer **forbid extra** (pydantic default) so `highlights` in the body 422s.

- [ ] **Step 1: Rewrite API tests**

Replace `test_report_from_analysis_json` and `test_report_503_when_chat_down`:

```python
def test_report_from_analysis_json(monkeypatch: object) -> None:
  from compliance.models import ComplianceReport, ObligationFinding, ReportCounts

  def fake_report(analysis, **_kwargs):
    return ComplianceReport(
      document_id=analysis.document_id,
      jurisdiction=analysis.jurisdiction,
      applicable_laws=analysis.applicable_laws,
      generated_at="2026-08-30T05:00:00Z",
      counts=ReportCounts(total=0),
      narrative_available=True,
      executive_summary="One gap remains.",
      findings=[],
    )

  monkeypatch.setattr("policy_compare.api.generate_report", fake_report)
  client = TestClient(app)
  response = client.post(
    "/report",
    json={
      "document_id": "DOC_x",
      "jurisdiction": "IN",
      "applicable_laws": ["TINY"],
      "obligations": [],
      "gaps": [],
      "penalties": [],
    },
  )
  assert response.status_code == 200, response.text
  body = response.json()
  assert body["document_id"] == "DOC_x"
  assert body["executive_summary"] == "One gap remains."
  assert body["narrative_available"] is True
  assert "highlights" not in body


def test_report_200_when_generate_report_has_no_narrative(monkeypatch: object) -> None:
  from compliance.models import ComplianceReport, ReportCounts

  def fake_report(analysis, **_kwargs):
    return ComplianceReport(
      document_id=analysis.document_id,
      generated_at="2026-08-30T05:00:00Z",
      counts=ReportCounts(),
      narrative_available=False,
      findings=[],
    )

  monkeypatch.setattr("policy_compare.api.generate_report", fake_report)
  client = TestClient(app)
  response = client.post(
    "/report",
    json={
      "document_id": "DOC_x",
      "jurisdiction": "IN",
      "obligations": [],
      "gaps": [],
      "penalties": [],
    },
  )
  assert response.status_code == 200
  assert response.json()["narrative_available"] is False


def test_report_pdf_returns_pdf_bytes() -> None:
  client = TestClient(app)
  response = client.post(
    "/report.pdf",
    json={
      "document_id": "DOC_x",
      "jurisdiction": "IN",
      "applicable_laws": ["TINY"],
      "generated_at": "2026-08-30T05:00:00Z",
      "counts": {"covered": 0, "partial": 0, "missing": 1, "total": 1},
      "narrative_available": False,
      "findings": [
        {
          "obligation_id": "TINY_SECURE",
          "title": "Secure personal data",
          "act": "TINY",
          "status": "missing",
        }
      ],
      "penalties": [],
    },
  )
  assert response.status_code == 200, response.text
  assert response.headers["content-type"].startswith("application/pdf")
  assert "polarislex-DOC_x.pdf" in response.headers.get("content-disposition", "")
  assert response.content.startswith(b"%PDF")
  assert b"TINY_SECURE" in response.content
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest policy_compare/tests/test_api.py::test_report_from_analysis_json policy_compare/tests/test_api.py::test_report_200_when_generate_report_has_no_narrative policy_compare/tests/test_api.py::test_report_pdf_returns_pdf_bytes -v`

Expected: FAIL (503 still, or `/report.pdf` missing).

- [ ] **Step 3: Implement endpoints**

Edit `policy_compare/src/policy_compare/api.py` as specified.

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest policy_compare/tests/test_api.py compliance/tests/test_report.py compliance/tests/test_pdf.py -v`

Expected: PASS.

- [ ] **Step 5: Commit** (only if the user asked)

```bash
git add policy_compare/src/policy_compare/api.py policy_compare/tests/test_api.py
git commit -m "$(cat <<'EOF'
Serve the memo as JSON and as a downloadable PDF.

EOF
)"
```

---

### Task 6: Memo preview + Download PDF

**Files:**
- Modify: `web/src/ReportPanel.jsx`
- Modify: `web/src/index.css` (`.report-highlights` → memo sections; download row)
- Modify: `web/src/Findings.jsx` only if ReportPanel needs no new props (download can live inside ReportPanel)

**Interfaces:**
- Consumes: report JSON from existing `App.jsx` `POST /api/report` (no App.jsx change required if the panel reads `report.findings`, `report.counts`, `report.law_notes`, `report.narrative_available`)
- Produces: preview of cover + summary + per-law notes + full duty list grouped by `applicable_laws`; **Download PDF** posts `report` to `/api/report.pdf`

`ReportPanel.jsx` behavior:

- Error / busy / empty: keep current three early returns.
- Header row: `h3` Report + `button.btn-secondary` “Download PDF” disabled while a local `downloading` flag is true.
- Cover: `Covered {n} · Partial {n} · Missing {n} · Total {n}` from `report.counts`.
- Summary: `report.executive_summary` if `report.narrative_available`; else `Narrative unavailable. The table below is from automated analysis only.`
- For each act in `report.applicable_laws`: note paragraph from `law_notes` match; then all `findings` with that `act`. Status badges reuse `badge-match` / `badge-partial` / `badge-missing` like Findings (`covered` → `badge-match`). Show title, id (`mono`), closest clause from `matched_clauses[0]` or “No matching clause”.
- Findings with act not in `applicable_laws`: “Other” group.
- Do not hide covered rows.
- Caveat at the bottom: `report.caveats`.
- Download:

```javascript
async function downloadPdf() {
  setDlError("");
  setDownloading(true);
  try {
    const response = await fetch("/api/report.pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    });
    if (!response.ok) {
      throw new Error("PDF download failed");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `polarislex-${report.document_id}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    setDlError(err.message);
  } finally {
    setDownloading(false);
  }
}
```

CSS: `.report-head { display:flex; justify-content:space-between; align-items:center; }`, `.report-counts`, `.report-law` section spacing, reuse `.findings-row` grid or a simpler stacked list so the memo is readable. Remove unused `.report-highlights` if nothing else uses it.

- [ ] **Step 1: Implement the panel**

There is no frontend test runner. Treat the JSX as the deliverable. Keep `ReportPanel` props `{ report, reportError, busy }` so `Findings.jsx` stays unchanged.

- [ ] **Step 2: Rebuild web and click through**

Run: `docker compose up --build -d web api` from the repo root.

Open http://localhost:8080, load a policy, Run Validation, wait for the memo (findings appear first). Confirm covered rows are in the memo, Download PDF saves `polarislex-DOC_….pdf`, and the file opens with the same ids as the table.

If Ollama chat is stopped, the memo still shows the table and the PDF still downloads.

- [ ] **Step 3: Commit** (only if the user asked)

```bash
git add web/src/ReportPanel.jsx web/src/index.css
git commit -m "$(cat <<'EOF'
Show the full memo on screen and attach a PDF download.

EOF
)"
```

---

### Task 7: Docs + graphify

**Files:**
- Modify: `plan.md` — Phase 5 bullets: client memo + `POST /report.pdf`; chat failure no longer 503
- Modify: `README.md` — report is a keepable memo + PDF; `/report` 200 with `narrative_available`; add `POST /report.pdf`
- Modify: `ARCHITECTURE.md` — remove “does not yet generate LLM reports”; mention hybrid memo + PDF

- [ ] **Step 1: Edit the three docs**

README compare-vs-analyze paragraph currently says `/report` returns 503 if chat is down. Change to: Findings and the memo table still load; narrative line says unavailable; PDF download still works.

`plan.md` Phase 5: mark PDF download done when this task lands; keep “no SQLite”.

- [ ] **Step 2: Update the knowledge graph**

Run: `./scripts/graphify.sh update .`

Expected: graph rebuild completes without error.

- [ ] **Step 3: Full pytest slice**

Run: `.venv/bin/pytest compliance/tests/test_report.py compliance/tests/test_pdf.py policy_compare/tests/test_api.py -v`

Expected: PASS.

- [ ] **Step 4: Commit** (only if the user asked)

```bash
git add plan.md README.md ARCHITECTURE.md graphify-out
git commit -m "$(cat <<'EOF'
Document the client memo and PDF download.

EOF
)"
```

`graphify-out/` is gitignored; do not force-add it.

---

## Spec coverage

| Spec requirement | Task |
|---|---|
| Full findings in report object | 2 |
| Qwen summary + per-law notes; drop invented acts | 3 |
| Chat down → still complete, no 503 | 3, 5 |
| Cover, summary, by-law tables, penalties, footer | 4, 6 |
| `POST /report.pdf` deterministic | 4, 5 |
| UI preview + download | 6 |
| ReportLab on API image | 4 (`pip install -e compliance` in Dockerfile already) |
| Docs | 7 |

## Placeholder scan

No TBD, no “add tests later”, no “similar to Task N” without copied code.
