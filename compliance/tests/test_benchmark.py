"""Frozen PASS / FAIL / PARTIAL / N-A / AMBIGUOUS engine contracts. No Qdrant."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from policy_compare.service import default_law_paths

from compliance.applicability import default_entity_profile
from compliance.benchmark_cases import AMBIGUOUS_TEXTS, FAIL_TEXTS, PARTIAL_TEXTS, PASS_TEXTS
from compliance.service import analyze_document

ROOT = Path(__file__).resolve().parents[2]
GOLD = Path(__file__).parent / "benchmark"
CA_IDS = (
  "ITACT_SEC_15",
  "ITACT_SEC_30",
  "ITACT_SEC_34",
  "ITACT_SEC_26",
  "ITACT_SEC_42_SUB_1",
  "ITACT_SEC_42_SUB_2",
)


def _document(texts: list[str], filename: str) -> EntityDocument:
  entity_clauses = []
  for index, text in enumerate(texts, start=1):
    clause = Clause(
      clause_id=f"S{index:03d}_C001",
      section_id=f"S{index:03d}",
      section_title=f"Section {index}",
      document_id="DOC_bench",
      document_type=DocumentFormat.TXT,
      clause_text=text,
      span=Span(start=0, end=len(text)),
    )
    classified = ClassifiedClause(
      clause=clause,
      role=StructuralRole.STATEMENT,
      confidence=1.0,
      classification_reason=[],
    )
    entity_clauses.append(
      EntityClause(contextual_clause=ContextualClause(classified_clause=classified), entities=[])
    )
  return EntityDocument(
    metadata=DocumentMetadata(
      document_id="DOC_bench",
      filename=filename,
      format=DocumentFormat.TXT,
    ),
    entity_clauses=entity_clauses,
  )


def _analyze(texts: list[str], filename: str, **kwargs):
  return analyze_document(
    _document(texts, filename),
    default_law_paths(ROOT),
    search=lambda _: [],
    **kwargs,
  )


def _gold(name: str) -> dict:
  return json.loads((GOLD / name).read_text(encoding="utf-8"))


def test_pass_bharatpay_style_security_and_ca_na() -> None:
  gold = _gold("gold_pass.json")
  result = _analyze(PASS_TEXTS, "privacy_policy_1.txt")
  by_id = {row.obligation_id: row for row in result.obligations}
  for oid, allowed in gold["must_status"].items():
    assert by_id[oid].status in allowed, (oid, by_id[oid].status)
  assert sum(1 for row in result.obligations if row.status == "violation") <= gold["max_violation"]
  dpdp_missing = sum(
    1
    for row in result.obligations
    if row.act == "DPDP" and row.status == "missing"
  )
  assert dpdp_missing <= gold["max_dpdp_applicable_missing"]
  for oid in CA_IDS:
    assert by_id[oid].status == "not_applicable"


def test_fail_has_violations_but_not_all_gaps() -> None:
  gold = _gold("gold_fail.json")
  result = _analyze(FAIL_TEXTS, "Fail_Policy.txt")
  violations = [row for row in result.obligations if row.status == "violation"]
  assert len(violations) >= gold["min_violation"]
  for oid in gold["violation_ids"]:
    assert any(row.obligation_id == oid for row in violations)
  gaps = [row for row in result.obligations if row.status in {"missing", "partial", "violation", "undetermined", "conflict"}]
  assert len(violations) < len(gaps)


def test_partial_mixed_and_certin_generic_is_not_no_match() -> None:
  gold = _gold("gold_partial.json")
  result = _analyze(PARTIAL_TEXTS, "Partial_Policy.txt")
  statuses = {row.status for row in result.obligations}
  assert statuses & set(gold["require_mixed_statuses"])
  certin = next(row for row in result.obligations if row.obligation_id == "CERTIN_DIR_2")
  assert certin.status in gold["certin_dir_2"]
  assert certin.evidence_quality != "NO_RELIABLE_MATCH"


def test_na_profile_without_data_fiduciary() -> None:
  gold = _gold("gold_na.json")
  result = _analyze(
    PASS_TEXTS,
    "na.txt",
    profile=default_entity_profile(roles=gold["roles"]),
  )
  by_id = {row.obligation_id: row for row in result.obligations}
  for oid in gold["dpdp_fiduciary_ids"]:
    assert by_id[oid].status == gold["expected_status"]


def test_ambiguous_generic_law_is_never_covered() -> None:
  gold = _gold("gold_ambiguous.json")
  result = _analyze(AMBIGUOUS_TEXTS, "ambiguous.txt")
  covered = [row.obligation_id for row in result.obligations if row.status == gold["forbidden_status"]]
  assert covered == []
  counts = Counter(row.status for row in result.obligations if row.status != "not_applicable")
  assert counts["missing"] or counts["undetermined"] or counts["partial"]
