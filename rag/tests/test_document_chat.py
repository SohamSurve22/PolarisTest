from rag.service import answer_document_question

from tests.conftest import hit


def test_document_chat_uses_policy_prompt_and_citations() -> None:
  captured: dict[str, str] = {}

  def search(_query, **kwargs):
    return [hit(source_type="document_clause", cid="S002_C001", text="We retain data for one year.")]

  def chat(system: str, user: str) -> str:
    captured["system"] = system
    captured["user"] = user
    return "The policy states one year. [S002_C001]"

  result = answer_document_question(
    "How long is data retained?",
    document_id="DOC_x",
    search=search,
    chat=chat,
  )

  assert result.mode == "document"
  assert result.citations[0].id == "S002_C001"
  assert "uploaded policy" in captured["system"]
  assert captured["user"].endswith("How long is data retained?")
