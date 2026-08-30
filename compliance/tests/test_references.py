from document_pipeline.models.clause import Clause
from document_pipeline.models.metadata import DocumentFormat, Span

from compliance.references import expand_clause_evidence, has_generic_legal_language


def _clause(text: str, *, clause_id: str, section_id: str, title: str) -> Clause:
  return Clause(
    clause_id=clause_id,
    section_id=section_id,
    section_title=title,
    document_id="DOC_x",
    document_type=DocumentFormat.TXT,
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )


def test_see_section_9_expands_to_retention_section() -> None:
  pointer = _clause(
    "Retention is as described in Section 9.",
    clause_id="S001_C001",
    section_id="S001",
    title="Overview",
  )
  target = _clause(
    "We delete personal data when the purpose ends.",
    clause_id="S009_C001",
    section_id="S009",
    title="Section 9 Data Retention and Deletion",
  )
  other = _clause(
    "We use cookies.",
    clause_id="S002_C001",
    section_id="S002",
    title="Cookies",
  )
  expanded = expand_clause_evidence(pointer, [pointer, target, other])
  texts = [row.clause_text for row in expanded]
  assert target.clause_text in texts
  assert other.clause_text not in texts


def test_applicable_law_does_not_expand_and_is_generic() -> None:
  clause = _clause(
    "We handle incidents as required by applicable law.",
    clause_id="S001_C001",
    section_id="S001",
    title="Incidents",
  )
  other = _clause(
    "CERT-In six hour reporting.",
    clause_id="S002_C001",
    section_id="S002",
    title="Section 2 Security",
  )
  expanded = expand_clause_evidence(clause, [clause, other])
  assert [row.clause_id for row in expanded] == ["S001_C001"]
  assert has_generic_legal_language(clause.clause_text) is True
