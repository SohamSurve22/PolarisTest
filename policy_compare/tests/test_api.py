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

  def fake_analyze(document, law_paths, *, jurisdiction="IN", search=None):
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
