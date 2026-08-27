from document_pipeline.models.clause import Clause
from document_pipeline.models.metadata import DocumentFormat, Span


def make_clause(**overrides: object) -> Clause:
  values: dict[str, object] = {
    "clause_id": "S001_C001",
    "section_id": "S001",
    "section_title": "Definitions",
    "document_id": "DOC_abc123",
    "document_type": DocumentFormat.TXT,
    "clause_text": "Personal data means any information relating to an identified person.",
    "span": Span(start=0, end=70),
    "clause_number": "2(1)",
  }
  values.update(overrides)
  return Clause.model_validate(values)
