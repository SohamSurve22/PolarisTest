from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from vectorization.models import SearchHit

from compliance.duty_rules import load_equivalence_clusters
from compliance.service import analyze_document

ROOT = Path(__file__).resolve().parents[2]


def _clause(text: str, *, clause_id: str, section_title: str) -> Clause:
  return Clause(
    clause_id=clause_id,
    section_id=clause_id.split("_")[0],
    section_title=section_title,
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
      filename="Fail_Policy.txt",
      format=DocumentFormat.TXT,
    ),
    entity_clauses=entity_clauses,
  )


def test_grievance_cluster_is_loaded() -> None:
  clusters = load_equivalence_clusters()
  grievance = next(item for item in clusters if item.id == "grievance_redressal")
  assert set(grievance.obligation_ids) == {"DPDP_SEC_8_SUB_10", "SPDI_RULE_5_SUB_9"}


def test_grievance_pair_both_violation_with_section_12_citation() -> None:
  from policy_compare.service import default_law_paths

  denial = _clause(
    "QuickBazaar does not provide a dedicated privacy grievance officer, Data Protection "
    "Officer, complaint portal, telephone line, postal channel, email address or other "
    "grievance redressal mechanism.",
    clause_id="S012_C001",
    section_title="Grievance Redressal",
  )
  purposes = _clause(
    "Purposes of Processing. We process Personal Data for providing the Services.",
    clause_id="S003_C001",
    section_title="Purposes of Processing",
  )

  def search(query: str) -> list[SearchHit]:
    if "purpose" in query.lower() or "process personal data" in query.lower():
      return [
        SearchHit(
          score=0.88,
          source_type="kg_obligation",
          payload={"obligation_id": "SPDI_RULE_5_SUB_9", "law_code": "SPDI_RULES_2011"},
        )
      ]
    return []

  result = analyze_document(
    _document(denial, purposes),
    default_law_paths(ROOT),
    search=search,
  )
  by_id = {row.obligation_id: row for row in result.obligations}
  for oid in ("DPDP_SEC_8_SUB_10", "SPDI_RULE_5_SUB_9"):
    row = by_id[oid]
    assert row.status == "violation", (oid, row.status)
    blob = " ".join(item.text for item in row.counter_evidence + row.matched_clauses)
    assert "dedicated privacy grievance" in blob.lower()
