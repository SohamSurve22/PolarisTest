from rag.service import answer_question

from tests.conftest import hit


def test_dense_answer_uses_stub_chat_and_excerpts() -> None:
  def fake_search(query: str, *, source_type: str, top_k: int, min_score: float | None = None, **_):
    assert source_type == "rag_section"
    return [
      hit(
        source_type="rag_section",
        cid="CERTIN_DIR_2",
        title="Mandatory Cyber Incident Reporting Within 6 Hours",
        text="Report cyber incidents to CERT-In within 6 hours.",
      )
    ]

  def fake_chat(system: str, user: str) -> str:
    assert "only from" in system.lower() or "only" in system.lower()
    assert "CERTIN_DIR_2" in user
    assert "6 hours" in user
    return "Incidents must be reported within 6 hours. Cited: CERTIN_DIR_2"

  result = answer_question(
    "How quickly must cyber incidents be reported to CERT-In?",
    mode="dense",
    search=fake_search,
    chat=fake_chat,
  )
  assert result.mode == "dense"
  assert "6 hours" in result.answer
  assert result.citations[0].id == "CERTIN_DIR_2"
  assert result.retrieve_ms >= 0
  assert result.generate_ms >= 0
