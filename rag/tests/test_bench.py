from __future__ import annotations

import json
from pathlib import Path

import pytest

from rag.bench import GOLD_PATH, load_gold, recall_hit, run_bench
from rag.models import RagAnswer, RagCitation, RagError

GOLD = Path(__file__).parent / "benchmark" / "gold_rag.json"


def test_gold_rag_has_twelve_questions() -> None:
  gold = json.loads(GOLD.read_text(encoding="utf-8"))
  questions = gold["questions"]
  assert len(questions) >= 12
  topics = " ".join(row["question"].lower() for row in questions)
  assert "consent" in topics
  assert "withdraw" in topics
  assert "43a" in topics or "43a" in topics
  assert "cert-in" in topics or "6 hours" in topics
  assert "grievance" in topics
  assert "child" in topics
  for row in questions:
    assert row["gold_dense_ids"]
    assert row["gold_graph_ids"]


def test_recall_hit_if_any_gold_id_is_cited() -> None:
  citations = [
    RagCitation(id="DPDP_SEC_6_SUB_5", title="x", text="y", score=0.8),
    RagCitation(id="OTHER", title="x", text="y", score=0.7),
  ]
  assert recall_hit(citations, ["DPDP_SEC_6_SUB_5", "DPDP_SEC_6_SUB_6"]) is True
  assert recall_hit(citations, ["CERTIN_DIR_2"]) is False
  assert recall_hit([], ["DPDP_SEC_6_SUB_5"]) is False


def test_run_bench_stubbed_prints_two_modes() -> None:
  def fake_answer(question: str, mode: str, **_kwargs) -> RagAnswer:
    gold = next(row for row in load_gold()["questions"] if row["question"] == question)
    ids = gold["gold_dense_ids"] if mode == "dense" else gold["gold_graph_ids"]
    return RagAnswer(
      mode=mode,
      answer="ok",
      citations=[RagCitation(id=ids[0], title="", text="", score=0.9)],
      retrieve_ms=1.0,
      generate_ms=2.0,
    )

  rows = run_bench(answer=fake_answer)
  assert [row.mode for row in rows] == ["dense", "graph"]
  assert all(row.recall == 1.0 for row in rows)
  assert all(row.retrieve_ms >= 0 for row in rows)
  assert all(row.generate_ms >= 0 for row in rows)
  table = "\n".join(row.format() for row in rows)
  assert "dense" in table
  assert "graph" in table
  assert "recall" in table.lower() or "@" in table


@pytest.mark.live
def test_live_bench_skips_when_ollama_down() -> None:
  if not _ollama_up():
    pytest.skip("Ollama is down")
  try:
    rows = run_bench()
  except RagError:
    pytest.skip("Qdrant or Ollama unavailable")
  assert {row.mode for row in rows} == {"dense", "graph"}
  assert all(row.n_questions == len(load_gold()["questions"]) for row in rows)


def _ollama_up() -> bool:
  import httpx

  try:
    response = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
    return response.status_code == 200
  except httpx.HTTPError:
    return False


def test_gold_path_matches_package() -> None:
  assert GOLD_PATH.name == "gold_rag.json"
  assert GOLD_PATH.is_file() or GOLD.is_file()
