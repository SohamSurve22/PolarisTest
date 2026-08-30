from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from vectorization.models import SearchHit

from compliance.duty_rules import load_duty_rules
from compliance.matching import gather_evidence
from compliance.service import analyze_document

ROOT = Path(__file__).resolve().parents[2]


def _clause(text: str, *, clause_id: str = "S002_C001") -> Clause:
  return Clause(
    clause_id=clause_id,
    section_id="S002",
    section_title="Security",
    document_id="DOC_x",
    document_type=DocumentFormat.TXT,
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )


def _document(*clauses: Clause) -> EntityDocument:
  entity_clauses = []
  for clause in clauses:
    classified = ClassifiedClause(
      clause=clause,
      role=StructuralRole.STATEMENT,
      confidence=1.0,
      classification_reason=[],
    )
    entity_clauses.append(
      EntityClause(
        contextual_clause=ContextualClause(classified_clause=classified),
        entities=[],
      )
    )
  return EntityDocument(
    metadata=DocumentMetadata(
      document_id="DOC_x",
      filename="policy.txt",
      format=DocumentFormat.TXT,
    ),
    entity_clauses=entity_clauses,
  )


def _hit(obligation_id: str, score: float) -> SearchHit:
  return SearchHit(
    score=score,
    source_type="kg_obligation",
    payload={"obligation_id": obligation_id, "law_code": "DPDP"},
  )


def test_security_clause_credits_dpdp_and_is_not_missing() -> None:
  from policy_compare.service import default_law_paths

  text = (
    "BharatPay implements encryption, tokenisation, MFA, least-privilege access, "
    "logging, monitoring, backups and vendor due diligence."
  )

  def search(_query: str) -> list[SearchHit]:
    return [_hit("CERTIN_DIR_2", 0.80), _hit("DPDP_SEC_8_SUB_5", 0.78)]

  result = analyze_document(
    _document(_clause(text)),
    default_law_paths(ROOT),
    search=search,
  )
  by_id = {row.obligation_id: row for row in result.obligations}
  assert by_id["DPDP_SEC_8_SUB_5"].status != "missing"
  assert by_id["DPDP_SEC_8_SUB_5"].status in {"covered", "partial"}
  assert by_id["DPDP_SEC_8_SUB_5"].matched_clauses
  assert by_id["CERTIN_DIR_2"].matched_clauses


def test_unrelated_low_score_is_no_reliable_match() -> None:
  from policy_compare.service import default_law_paths

  def search(_query: str) -> list[SearchHit]:
    return [_hit("ITACT_SEC_43A", 0.32)]

  result = analyze_document(
    _document(_clause("Contact our grievance officer at complaints@example.com.")),
    default_law_paths(ROOT),
    search=search,
  )
  row = next(item for item in result.obligations if item.obligation_id == "ITACT_SEC_43A")
  assert row.evidence_quality == "NO_RELIABLE_MATCH"
  assert row.matched_clauses == []


def test_element_keywords_without_vector_hit_are_medium() -> None:
  rule = load_duty_rules()["DPDP_SEC_8_SUB_5"]
  clause = _clause(
    "We use encryption, MFA, logging and vendor due diligence.",
    clause_id="S008_C001",
  )
  bundle = gather_evidence("DPDP_SEC_8_SUB_5", "Security Safeguards", rule, [clause], [])
  assert bundle.element_hits
  assert bundle.quality in {"HIGH", "MEDIUM"}
  assert bundle.matched_clauses
