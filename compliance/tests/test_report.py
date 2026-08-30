from __future__ import annotations

import json
from pathlib import Path

from compliance.models import (
  AnalysisResult,
  ComplianceReport,
  GapFinding,
  MatchedClause,
  ObligationFinding,
  PenaltyFinding,
  ReportCounts,
)
from compliance.report import assemble_report, compact_payload, generate_report


def _analysis() -> AnalysisResult:
  return AnalysisResult(
    document_id="DOC_x",
    jurisdiction="IN",
    applicable_laws=["TINY", "DPDP"],
    obligations=[
      ObligationFinding(
        obligation_id="TINY_CONSENT",
        title="Obtain consent",
        act="TINY",
        status="covered",
        score=0.8,
        matched_clause_ids=["S002_C001"],
        matched_clauses=[
          MatchedClause(clause_id="S002_C001", section_title="Consent", text="We obtain consent."),
        ],
      ),
      ObligationFinding(
        obligation_id="TINY_SECURE",
        title="Secure personal data",
        act="TINY",
        status="missing",
        score=0.0,
      ),
    ],
    gaps=[
      GapFinding(
        obligation_id="TINY_SECURE",
        title="Secure personal data",
        status="missing",
        act="TINY",
      ),
    ],
    penalties=[
      PenaltyFinding(
        obligation_id="TINY_SECURE",
        title="Fine for insecure processing",
        amount_crore=250,
        act="TINY",
      ),
    ],
  )


def test_compliance_report_holds_engine_findings() -> None:
  row = ObligationFinding(
    obligation_id="TINY_SECURE",
    title="Secure personal data",
    act="TINY",
    status="missing",
  )
  report = ComplianceReport(
    document_id="DOC_x",
    jurisdiction="IN",
    applicable_laws=["TINY"],
    generated_at="2026-08-30T05:00:00Z",
    counts=ReportCounts(covered=0, partial=0, missing=1, total=1),
    findings=[row],
    narrative_available=False,
  )
  dumped = report.model_dump()
  assert "highlights" not in dumped
  assert dumped["findings"][0]["obligation_id"] == "TINY_SECURE"
  assert dumped["counts"]["total"] == 1
  assert dumped["narrative_available"] is False


def test_compact_payload_sends_titles_not_snippets() -> None:
  payload = compact_payload(_analysis())
  blob = json.dumps(payload)
  assert payload["counts"] == {"covered": 1, "partial": 0, "missing": 1, "total": 2}
  assert "We obtain consent" not in blob
  acts = {row["act"]: row for row in payload["by_law"]}
  assert acts["TINY"]["covered"] == ["Obtain consent"]
  assert acts["TINY"]["missing"] == ["Secure personal data"]
  assert "penalties" not in payload


def test_assemble_report_copies_all_findings_and_scored_penalties() -> None:
  analysis = _analysis()
  analysis.penalties.append(
    PenaltyFinding(
      obligation_id="TINY_SECURE",
      title="Unscored",
      amount_crore=None,
      act="TINY",
    )
  )
  report = assemble_report(analysis, generated_at="2026-08-30T05:00:00Z")
  assert [row.obligation_id for row in report.findings] == ["TINY_CONSENT", "TINY_SECURE"]
  assert report.counts.total == 2
  assert report.counts.covered == 1
  assert report.counts.missing == 1
  assert report.narrative_available is False
  assert [row.obligation_id for row in report.penalties] == ["TINY_SECURE"]
  assert report.penalties[0].amount_crore == 250
  assert len(report.penalties) == 1


def test_generate_report_uses_law_notes_and_keeps_engine_ids() -> None:
  def chat(_system: str, user: str) -> str:
    assert "Obtain consent" in user
    assert "We obtain consent" not in user
    return json.dumps(
      {
        "executive_summary": "Consent is covered; security is missing.",
        "law_notes": [
          {"act": "TINY", "note": "Security duty is absent."},
          {"act": "FAKE", "note": "Invented statute."},
        ],
      }
    )

  report = generate_report(_analysis(), chat=chat, generated_at="2026-08-30T05:00:00Z")
  assert report.narrative_available is True
  assert "consent" in report.executive_summary.lower()
  assert [row.act for row in report.law_notes] == ["TINY"]
  assert [row.obligation_id for row in report.findings] == ["TINY_CONSENT", "TINY_SECURE"]
  assert report.findings[0].status == "covered"


def test_generate_report_survives_garbage_chat() -> None:
  def chat(_system: str, _user: str) -> str:
    return "not json"

  report = generate_report(_analysis(), chat=chat, generated_at="2026-08-30T05:00:00Z")
  assert report.narrative_available is False
  assert report.executive_summary == ""
  assert len(report.findings) == 2


def test_generate_report_survives_empty_summary() -> None:
  def chat(_system: str, _user: str) -> str:
    return json.dumps({"executive_summary": "  ", "law_notes": [{"act": "TINY", "note": "x"}]})

  report = generate_report(_analysis(), chat=chat)
  assert report.narrative_available is False
  assert report.law_notes == []


def test_generate_report_writes_json_when_dir_set(tmp_path: Path) -> None:
  def chat(_system: str, _user: str) -> str:
    return json.dumps(
      {
        "executive_summary": "Covered consent; missing security.",
        "law_notes": [{"act": "TINY", "note": "Security gap."}],
      }
    )

  report = generate_report(_analysis(), chat=chat, report_dir=tmp_path)
  saved = tmp_path / "DOC_x.json"
  body = json.loads(saved.read_text(encoding="utf-8"))
  assert body["document_id"] == report.document_id
  assert body["narrative_available"] is True
  assert len(body["findings"]) == 2
