from vectorization.models import clause_to_embeddable

from tests.conftest import make_clause


def test_clause_to_embeddable_joins_section_title_and_text() -> None:
  record = clause_to_embeddable(make_clause())

  assert record.clause_id == "S001_C001"
  assert record.document_id == "DOC_abc123"
  assert record.section_id == "S001"
  assert record.retrieval_text == (
    "Definitions — Personal data means any information relating to an identified person."
  )


def test_clause_to_embeddable_omits_blank_section_title() -> None:
  record = clause_to_embeddable(make_clause(section_title=None))

  assert record.retrieval_text == (
    "Personal data means any information relating to an identified person."
  )
