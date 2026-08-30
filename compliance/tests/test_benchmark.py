"""Frozen PASS / FAIL / PARTIAL / N-A / AMBIGUOUS engine contracts. No Qdrant."""

from __future__ import annotations

import json
import tempfile
from collections import Counter
from pathlib import Path

import pytest

from document_pipeline.models.clause import Clause
from document_pipeline.models.context import ContextualClause
from document_pipeline.models.entity import EntityClause, EntityDocument
from document_pipeline.models.document import DocumentSource
from document_pipeline.models.metadata import DocumentFormat, DocumentMetadata, Span
from document_pipeline.models.semantic import ClassifiedClause, StructuralRole
from document_pipeline.pipeline.orchestrator import create_default_orchestrator
from policy_compare.service import default_law_paths

from compliance.applicability import default_entity_profile
from compliance.benchmark_cases import AMBIGUOUS_TEXTS, FAIL_TEXTS, PARTIAL_TEXTS, PASS_TEXTS
from compliance.citations import closest_citation
from compliance.duty_rules import load_duty_rules
from compliance.report import assemble_report, counts_banner
from compliance.service import AnalyzeError, analyze_document

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


def _live_analyze_pdf(filename: str, document_id: str):
  pdf = ROOT / "test_policy" / filename
  if not pdf.exists():
    pytest.skip(f"{filename} is not in the repo")
  temp_path: Path | None = None
  try:
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
      handle.write(pdf.read_bytes())
      temp_path = Path(handle.name)
    source = DocumentSource(
      metadata=DocumentMetadata(
        document_id=document_id,
        filename=filename,
        format=DocumentFormat.PDF,
        source_path=str(temp_path),
      ),
    )
    outputs = create_default_orchestrator().run(source)
    return analyze_document(outputs.entity, default_law_paths(ROOT))
  except AnalyzeError:
    pytest.skip("Qdrant or embeddings unavailable")
  finally:
    if temp_path is not None:
      temp_path.unlink(missing_ok=True)


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


@pytest.mark.live
def test_live_fail_policy_pdf_must_violations() -> None:
  result = _live_analyze_pdf("Fail_Policy.pdf", "DOC_fail_live")
  by_id = {row.obligation_id: row for row in result.obligations}
  must = (
    "DPDP_SEC_6_SUB_5",
    "DPDP_SEC_8_SUB_7",
    "DPDP_SEC_8_SUB_10",
    "DPDP_SEC_9_SUB_1",
  )
  for oid in must:
    assert by_id[oid].status in {"violation", "conflict"}, (oid, by_id[oid].status)
    assert by_id[oid].status != "covered"
  assert by_id["DPDP_SEC_8_SUB_5"].status != "covered"


def test_gold_fail_citations_covers_catalog() -> None:
  gold = _gold("gold_fail_citations.json")
  catalog = set(load_duty_rules())
  assert set(gold["duties"]) == catalog
  mix = gold["applicable_identity"]
  assert mix["covered"] + mix["partial"] + mix["missing"] + mix["violation"] + mix["conflict"] == mix["total"]
  assert mix["total"] + mix["not_applicable"] == mix["catalog"]
  for oid in ("DPDP_SEC_8_SUB_10", "SPDI_RULE_5_SUB_9", "SPDI_RULE_6_SUB_1", "DPDP_SEC_9_SUB_3", "DPDP_SEC_6_SUB_5"):
    assert "citation_must_include" in gold["duties"][oid] or "citation_must_include_any" in gold["duties"][oid]


@pytest.mark.live
def test_live_fail_policy_citations_banner_and_priority() -> None:
  gold = _gold("gold_fail_citations.json")
  result = _live_analyze_pdf("Fail_Policy.pdf", "DOC_fail_live")
  by_id = {row.obligation_id: row for row in result.obligations}
  for oid, spec in gold["duties"].items():
    row = by_id[oid]
    assert row.status in spec["status"], (oid, row.status, spec["status"])
    if spec.get("forbidden_status"):
      assert row.status not in spec["forbidden_status"], (oid, row.status)
    cited = closest_citation(row)
    for needle in spec.get("citation_must_include") or []:
      assert needle.lower() in cited.lower(), (oid, needle, cited)
    any_needles = spec.get("citation_must_include_any") or []
    if any_needles:
      assert any(needle.lower() in cited.lower() for needle in any_needles), (oid, cited)
    for banned in spec.get("citation_must_not") or []:
      assert banned.lower() not in cited.lower(), (oid, banned, cited)
    assert row.status != "covered" or oid not in {
      "DPDP_SEC_6_SUB_5",
      "DPDP_SEC_8_SUB_6",
      "DPDP_SEC_8_SUB_10",
      "ITACT_SEC_43A",
    }
  report = assemble_report(result, generated_at="2026-08-30T12:00:00Z")
  banner = counts_banner(report.counts)
  assert "Conflict" in banner
  assert report.counts.covered + report.counts.partial + report.counts.missing + report.counts.undetermined + report.counts.violation + report.counts.conflict == report.counts.total
  assert all(row.status != "partial" for row in report.priority_gaps) or any(
    by_id[row.obligation_id].status == "violation" for row in report.priority_gaps
  )
  if report.priority_gaps:
    first = by_id[report.priority_gaps[0].obligation_id]
    assert first.status in {"violation", "conflict"}


@pytest.mark.live
def test_live_bharatpay_pass_lock() -> None:
  gold = _gold("gold_pass.json")
  result = _live_analyze_pdf("privacy_policy_1.pdf", "DOC_pass_live")
  by_id = {row.obligation_id: row for row in result.obligations}
  for oid, allowed in gold["must_status"].items():
    assert by_id[oid].status in allowed, (oid, by_id[oid].status)
  assert sum(1 for row in result.obligations if row.status == "violation") <= gold["max_violation"]
  for oid in CA_IDS:
    assert by_id[oid].status == "not_applicable"
