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


def test_compare_rejects_bad_type() -> None:
  client = TestClient(app)
  response = client.post(
    "/compare",
    files={"file": ("notes.csv", b"a,b", "text/csv")},
  )
  assert response.status_code == 400
