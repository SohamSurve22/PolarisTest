from pathlib import Path

from fastapi.testclient import TestClient

from policy_compare.api import app

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def test_health() -> None:
  client = TestClient(app)
  assert client.get("/health").json() == {"status": "ok"}


def test_compare_txt(monkeypatch: object) -> None:
  monkeypatch.setenv("POLARIS_LAW_DIR", str(FIXTURE_DIR))  # type: ignore[attr-defined]
  client = TestClient(app)
  payload = (
    "Consent\n\n"
    "We obtain consent before we process personal data. You may withdraw consent.\n"
  ).encode("utf-8")
  response = client.post(
    "/compare",
    files={"file": ("policy.txt", payload, "text/plain")},
  )
  assert response.status_code == 200, response.text
  body = response.json()
  assert body["policy"]["nodes"]
  assert body["ideal"]["nodes"]
  kinds = {node["kind"] for node in body["policy"]["nodes"]}
  assert "section" in kinds
  assert "document" in kinds
  assert "cluster" in kinds
  ideal_kinds = {node["kind"] for node in body["ideal"]["nodes"]}
  assert "cluster" in ideal_kinds
  assert "topic" in ideal_kinds
  assert "law_chunk" in ideal_kinds


def test_compare_rejects_bad_type() -> None:
  client = TestClient(app)
  response = client.post(
    "/compare",
    files={"file": ("notes.csv", b"a,b", "text/csv")},
  )
  assert response.status_code == 400


def test_analyze_txt(monkeypatch: object) -> None:
  monkeypatch.setenv("POLARIS_LAW_DIR", str(FIXTURE_DIR))  # type: ignore[attr-defined]

  from compliance.models import AnalysisResult

  def fake_analyze(document, law_paths, *, jurisdiction="IN", search=None, **_kwargs):
    _ = law_paths, search
    return AnalysisResult(
      document_id=document.metadata.document_id,
      jurisdiction=jurisdiction,
      applicable_laws=["TINY"],
      obligations=[],
      gaps=[],
      penalties=[],
    )

  monkeypatch.setattr("policy_compare.api.analyze_document", fake_analyze)  # type: ignore[attr-defined]
  client = TestClient(app)
  response = client.post(
    "/analyze",
    files={"file": ("policy.txt", b"We obtain consent.\n", "text/plain")},
    data={"jurisdiction": "IN"},
  )
  assert response.status_code == 200, response.text
  body = response.json()
  assert body["jurisdiction"] == "IN"
  assert body["document_id"].startswith("DOC_")
  assert body["applicable_laws"] == ["TINY"]


def test_report_from_analysis_json(monkeypatch: object) -> None:
  from compliance.models import ComplianceReport, ReportCounts

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


def test_report_pdf_filename_from_source_filename() -> None:
  client = TestClient(app)
  response = client.post(
    "/report.pdf",
    json={
      "document_id": "DOC_x",
      "source_filename": "uploads/policy.txt",
      "jurisdiction": "IN",
      "applicable_laws": ["TINY"],
      "generated_at": "2026-08-30T05:00:00Z",
      "counts": {"covered": 0, "partial": 0, "missing": 1, "total": 1},
      "findings": [
        {
          "obligation_id": "TINY_SECURE",
          "title": "Secure personal data",
          "act": "TINY",
          "status": "missing",
        }
      ],
    },
  )
  assert response.status_code == 200, response.text
  assert "polarislex-policy.pdf" in response.headers.get("content-disposition", "")
  assert b"policy.txt" in response.content


def test_analyze_503_when_search_backend_down(monkeypatch: object) -> None:
  monkeypatch.setenv("POLARIS_LAW_DIR", str(FIXTURE_DIR))  # type: ignore[attr-defined]
  from compliance.service import AnalyzeError

  def boom(*_args, **_kwargs):
    raise AnalyzeError("qdrant down")

  monkeypatch.setattr("policy_compare.api.analyze_document", boom)  # type: ignore[attr-defined]
  client = TestClient(app)
  response = client.post(
    "/analyze",
    files={"file": ("policy.txt", b"consent\n", "text/plain")},
  )
  assert response.status_code == 503


def test_rag_dense_returns_answer(monkeypatch: object) -> None:
  from rag.models import RagAnswer, RagCitation

  def fake_answer(question: str, mode: str, **_kwargs):
    assert question == "What is section 43A?"
    assert mode == "dense"
    return RagAnswer(
      mode="dense",
      answer="Compensation for negligent security. Cited: ITACT_SEC_43A",
      citations=[
        RagCitation(id="ITACT_SEC_43A", title="Compensation", text="pay damages", score=0.9)
      ],
      retrieve_ms=1.0,
      generate_ms=2.0,
    )

  monkeypatch.setattr("policy_compare.api.answer_question", fake_answer)
  client = TestClient(app)
  response = client.post("/rag", json={"question": "What is section 43A?", "mode": "dense"})
  assert response.status_code == 200, response.text
  body = response.json()
  assert body["mode"] == "dense"
  assert body["citations"][0]["id"] == "ITACT_SEC_43A"
  assert "retrieve_ms" in body
  assert "generate_ms" in body


def test_rag_503_when_backend_down(monkeypatch: object) -> None:
  from rag.models import RagError

  def boom(*_args, **_kwargs):
    raise RagError("qdrant down")

  monkeypatch.setattr("policy_compare.api.answer_question", boom)
  client = TestClient(app)
  response = client.post("/rag", json={"question": "consent?", "mode": "dense"})
  assert response.status_code == 503


def test_rag_graph_returns_answer(monkeypatch: object) -> None:
  from rag.models import RagAnswer, RagCitation

  def fake_answer(question: str, mode: str, **_kwargs):
    assert mode == "graph"
    return RagAnswer(
      mode="graph",
      answer="Report within 6 hours. Cited: CERTIN_DIR_2",
      citations=[
        RagCitation(id="CERTIN_DIR_2", title="6 hours", text="report within 6 hours", score=0.8)
      ],
      retrieve_ms=3.0,
      generate_ms=4.0,
    )

  monkeypatch.setattr("policy_compare.api.answer_question", fake_answer)
  client = TestClient(app)
  response = client.post("/rag", json={"question": "CERT-In 6 hours?", "mode": "graph"})
  assert response.status_code == 200, response.text
  assert response.json()["mode"] == "graph"
  assert response.json()["citations"][0]["id"] == "CERTIN_DIR_2"
