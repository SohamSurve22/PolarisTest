from datetime import date

from compliance.applicability import ApplicabilityDecision, apply_duty, default_entity_profile
from compliance.duty_rules import DutyRule, LawVersionMeta, load_duty_rules
from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from pathlib import Path

from compliance.service import analyze_document

ROOT = Path(__file__).resolve().parents[2]
CA_IDS = (
  "ITACT_SEC_15",
  "ITACT_SEC_30",
  "ITACT_SEC_34",
  "ITACT_SEC_26",
  "ITACT_SEC_42_SUB_1",
  "ITACT_SEC_42_SUB_2",
)


def test_privacy_profile_marks_ca_duty_not_applicable() -> None:
  profile = default_entity_profile()
  rule = DutyRule(roles_any=["ENTITY_CERTIFYING_AUTHORITY"], document_types=["operational_security"])
  version = LawVersionMeta(status="ACTIVE", still_scored=True)
  decision = apply_duty(rule, version, profile)
  assert decision.applicable is False
  assert "role" in decision.reason


def test_dpdp_security_stays_applicable_for_privacy_policy() -> None:
  profile = default_entity_profile()
  rule = load_duty_rules()["DPDP_SEC_8_SUB_5"]
  version = LawVersionMeta(status="ACTIVE", commencement_status="PARTIALLY_COMMENCED", still_scored=True)
  decision = apply_duty(rule, version, profile)
  assert isinstance(decision, ApplicabilityDecision)
  assert decision.applicable is True


def test_wrong_document_type_is_not_applicable() -> None:
  profile = default_entity_profile()
  rule = DutyRule(roles_any=["ENTITY_BODY_CORPORATE"], document_types=["operational_security"])
  decision = apply_duty(rule, None, profile)
  assert decision.applicable is False
  assert "document type" in decision.reason


def test_repealed_and_not_still_scored_is_not_applicable() -> None:
  profile = default_entity_profile()
  rule = DutyRule(roles_any=["ENTITY_DATA_FIDUCIARY"], document_types=["privacy_policy"])
  version = LawVersionMeta(status="REPEALED", still_scored=False)
  decision = apply_duty(rule, version, profile)
  assert decision.applicable is False
  assert "repealed" in decision.reason


def test_before_effective_from_is_not_applicable() -> None:
  profile = default_entity_profile(analysis_date=date(2020, 1, 1))
  rule = DutyRule(roles_any=["ENTITY_BODY_CORPORATE"], document_types=["privacy_policy"])
  version = LawVersionMeta(status="ACTIVE", still_scored=True, effective_from="2022-06-28")
  decision = apply_duty(rule, version, profile)
  assert decision.applicable is False
  assert "not yet effective" in decision.reason


def _clause(text: str) -> Clause:
  return Clause(
    clause_id="S001_C001",
    section_id="S001",
    section_title="Intro",
    document_id="DOC_x",
    document_type=DocumentFormat.TXT,
    clause_text=text,
    span=Span(start=0, end=len(text)),
  )


def _document(clause: Clause) -> EntityDocument:
  classified = ClassifiedClause(
    clause=clause,
    role=StructuralRole.STATEMENT,
    confidence=1.0,
    classification_reason=[],
  )
  return EntityDocument(
    metadata=DocumentMetadata(
      document_id="DOC_x",
      filename="policy.txt",
      format=DocumentFormat.TXT,
    ),
    entity_clauses=[
      EntityClause(contextual_clause=ContextualClause(classified_clause=classified), entities=[]),
    ],
  )


def test_analyze_default_profile_marks_six_ca_duties_not_applicable() -> None:
  from policy_compare.service import default_law_paths

  result = analyze_document(
    _document(_clause("We obtain consent from users.")),
    default_law_paths(ROOT),
    search=lambda _: [],
  )
  by_id = {row.obligation_id: row for row in result.obligations}
  for oid in CA_IDS:
    assert by_id[oid].status == "not_applicable"
    assert "role" in by_id[oid].applicability_reason
    assert not any(gap.obligation_id == oid for gap in result.gaps)
  assert by_id["DPDP_SEC_8_SUB_5"].status != "not_applicable"
  assert "DPDP" in result.applicable_laws
  assert "IT_ACT_2000" in result.applicable_laws  # 43A still applies
