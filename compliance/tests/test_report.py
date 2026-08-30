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
from compliance.report import (
  assemble_report,
  compact_payload,
  generate_report,
  scoreboard_sentence,
  verdict_sentence,
)


def _analysis() -> AnalysisResult:
  return AnalysisResult(
    document_id="DOC_x",
    source_filename="policy.txt",
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
  assert payload["counts"]["covered"] == 1
  assert payload["counts"]["partial"] == 0
  assert payload["counts"]["missing"] == 1
  assert payload["counts"]["total"] == 2
  assert "We obtain consent" not in blob
  acts = {row["act"]: row for row in payload["by_law"]}
  assert acts["TINY"]["titles"]["covered"] == ["Obtain consent"]
  assert acts["TINY"]["titles"]["missing"] == ["Secure personal data"]
  assert acts["TINY"]["counts"]["covered"] == 1
  assert acts["TINY"]["counts"]["missing"] == 1
  assert acts["TINY"]["counts"]["total"] == 2
  assert "penalties" not in payload


SCOREBOARD = (
  "This policy covers 1 of 2 applicable duties, with 0 partial, 1 missing, "
  "0 undetermined. 0 duties were not applicable. "
  "Missing policy language is not a finding of legal violation."
)
TINY_NOTE = "TINY: 1 covered, 0 partial, 1 missing. Themes: Secure personal data."
DPDP_NOTE = "DPDP: 0 covered, 0 partial, 0 missing."


def test_verdict_sentence_and_assemble_fills_law_notes() -> None:
  counts = ReportCounts(covered=1, partial=0, missing=1, total=2)
  assert verdict_sentence("TINY", counts) == "TINY: 1 covered, 0 partial, 1 missing."
  assert scoreboard_sentence(counts) == SCOREBOARD
  report = assemble_report(_analysis(), generated_at="2026-08-30T05:00:00Z")
  notes = {row.act: row.note for row in report.law_notes}
  assert notes["TINY"] == TINY_NOTE
  assert notes["DPDP"] == DPDP_NOTE
  assert report.executive_summary == SCOREBOARD
  assert report.narrative_available is False


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
  assert report.law_notes[0].note == TINY_NOTE
  assert [row.obligation_id for row in report.priority_gaps] == ["TINY_SECURE"]
  assert report.source_filename == "policy.txt"


def test_priority_gaps_missing_with_scored_penalty_only() -> None:
  analysis = _analysis()
  analysis.obligations.append(
    ObligationFinding(
      obligation_id="TINY_OTHER",
      title="Board minutes",
      act="TINY",
      status="missing",
    )
  )
  analysis.penalties.append(
    PenaltyFinding(
      obligation_id="TINY_CONSENT",
      title="Consent fine",
      amount_crore=10,
      act="TINY",
    )
  )
  report = assemble_report(analysis, generated_at="2026-08-30T05:00:00Z")
  ids = [row.obligation_id for row in report.priority_gaps]
  assert ids == ["TINY_SECURE"]
  assert "TINY_CONSENT" not in ids
  assert "TINY_OTHER" not in ids


def test_priority_gaps_sorted_and_capped_at_five() -> None:
  obligations = [
    ObligationFinding(
      obligation_id=f"M{i}",
      title=f"Missing {i}",
      act="TINY",
      status="missing",
    )
    for i in range(6)
  ]
  obligations.append(
    ObligationFinding(obligation_id="P0", title="Partial", act="TINY", status="partial")
  )
  penalties = [
    PenaltyFinding(obligation_id="P0", title="Partial years", imprisonment_years=5, act="TINY"),
    PenaltyFinding(obligation_id="M0", title="Low", amount_crore=10, act="TINY"),
    PenaltyFinding(obligation_id="M1", title="High", amount_crore=200, act="TINY"),
    PenaltyFinding(obligation_id="M2", title="Mid", amount_crore=50, act="TINY"),
    PenaltyFinding(obligation_id="M3", title="Years", imprisonment_years=2, act="TINY"),
    PenaltyFinding(obligation_id="M4", title="Also high", amount_crore=150, act="TINY"),
    PenaltyFinding(obligation_id="M5", title="Tiny", amount_crore=1, act="TINY"),
  ]
  analysis = AnalysisResult(
    document_id="DOC_x",
    jurisdiction="IN",
    applicable_laws=["TINY"],
    obligations=obligations,
    penalties=penalties,
  )
  report = assemble_report(analysis, generated_at="2026-08-30T05:00:00Z")
  assert [row.obligation_id for row in report.priority_gaps] == ["M1", "M4", "M2", "M0", "M5"]


def test_generate_report_uses_law_notes_and_keeps_engine_ids() -> None:
  def chat(_system: str, user: str) -> str:
    assert "Obtain consent" in user
    assert "We obtain consent" not in user
    return json.dumps(
      {
        "executive_summary": "Consent is covered; security is missing.",
        "law_notes": [
          {"act": "TINY", "theme": "security gap"},
          {"act": "FAKE", "theme": "Invented statute."},
        ],
      }
    )

  report = generate_report(_analysis(), chat=chat, generated_at="2026-08-30T05:00:00Z")
  assert report.narrative_available is True
  assert report.executive_summary.startswith(SCOREBOARD)
  assert "consent is covered" in report.executive_summary.lower()
  assert [row.act for row in report.law_notes] == ["TINY", "DPDP"]
  assert report.law_notes[0].note == TINY_NOTE
  assert "security gap" not in report.law_notes[0].note
  assert report.law_notes[1].note == DPDP_NOTE
  assert [row.obligation_id for row in report.findings] == ["TINY_CONSENT", "TINY_SECURE"]
  assert report.findings[0].status == "covered"


def test_generate_report_survives_garbage_chat() -> None:
  def chat(_system: str, _user: str) -> str:
    return "not json"

  report = generate_report(_analysis(), chat=chat, generated_at="2026-08-30T05:00:00Z")
  assert report.narrative_available is False
  assert report.executive_summary == SCOREBOARD
  assert len(report.findings) == 2
  assert report.law_notes[0].note == TINY_NOTE


def test_generate_report_survives_empty_summary() -> None:
  def chat(_system: str, _user: str) -> str:
    return json.dumps({"executive_summary": "  ", "law_notes": [{"act": "TINY", "theme": "x"}]})

  report = generate_report(_analysis(), chat=chat)
  assert report.narrative_available is False
  assert report.law_notes[0].note == TINY_NOTE


def test_generate_report_drops_banned_theme_when_missing() -> None:
  def chat(_system: str, _user: str) -> str:
    return json.dumps(
      {
        "executive_summary": "Consent exists. Gaps remain.",
        "law_notes": [
          {"act": "TINY", "theme": "Full coverage for general obligations"},
        ],
      }
    )

  report = generate_report(_analysis(), chat=chat)
  assert report.law_notes[0].note == TINY_NOTE


def test_generate_report_keeps_balanced_executive_summary() -> None:
  summary = (
    "Key areas covered include data retention, consent management, and privacy policies. "
    "Partial coverage exists for several obligations, while significant gaps remain in "
    "security measures, cross-border transfers, and breach notifications."
  )

  def chat(_system: str, _user: str) -> str:
    return json.dumps(
      {
        "executive_summary": summary,
        "law_notes": [{"act": "TINY", "theme": "security"}],
      }
    )

  report = generate_report(_analysis(), chat=chat)
  assert report.executive_summary.startswith(SCOREBOARD)
  assert "Partial coverage exists" in report.executive_summary
  assert report.narrative_available is True
  assert report.law_notes[0].note == TINY_NOTE


def test_engine_themes_missing_before_partial_capped_at_three() -> None:
  analysis = AnalysisResult(
    document_id="DOC_x",
    jurisdiction="IN",
    applicable_laws=["TINY"],
    obligations=[
      ObligationFinding(obligation_id="C", title="Covered duty", act="TINY", status="covered"),
      ObligationFinding(obligation_id="M1", title="Missing one", act="TINY", status="missing"),
      ObligationFinding(obligation_id="P1", title="Partial one", act="TINY", status="partial"),
      ObligationFinding(obligation_id="M2", title="Missing two", act="TINY", status="missing"),
      ObligationFinding(obligation_id="P2", title="Partial two", act="TINY", status="partial"),
      ObligationFinding(obligation_id="M3", title="Missing three", act="TINY", status="missing"),
      ObligationFinding(obligation_id="M4", title="Missing four", act="TINY", status="missing"),
    ],
  )
  report = assemble_report(analysis, generated_at="2026-08-30T05:00:00Z")
  note = report.law_notes[0].note
  assert "Themes: Missing one; Missing two; Missing three." in note
  assert "Missing four" not in note
  assert "Partial one" not in note
  assert "Covered duty" not in note.split("Themes:", 1)[-1]


def test_generate_report_strips_however_and_framework_wording() -> None:
  def chat(_system: str, _user: str) -> str:
    return json.dumps(
      {
        "executive_summary": (
          "However, the compliance framework covers consent. "
          "Gaps remain in security."
        ),
        "law_notes": [],
      }
    )

  report = generate_report(_analysis(), chat=chat)
  assert report.executive_summary.startswith(SCOREBOARD)
  remainder = report.executive_summary[len(SCOREBOARD) :].lstrip()
  assert not remainder.lower().startswith("however")
  assert "compliance framework" not in remainder.lower()
  assert "this policy covers consent" in remainder.lower()
  assert "Gaps remain in security" in report.executive_summary


def test_generate_report_does_not_duplicate_scoreboard_when_qwen_has_counts() -> None:
  qwen = (
    "This policy covers 1 of 2 scored duties, with 0 partial and 1 missing. "
    "Consent is in place and security is not."
  )

  def chat(_system: str, _user: str) -> str:
    return json.dumps({"executive_summary": qwen, "law_notes": []})

  report = generate_report(_analysis(), chat=chat)
  assert report.executive_summary.count("covers 1 of 2") == 1
  assert report.executive_summary.startswith("This policy")
  assert "Consent is in place" in report.executive_summary


def test_generate_report_writes_json_when_dir_set(tmp_path: Path) -> None:
  def chat(_system: str, _user: str) -> str:
    return json.dumps(
      {
        "executive_summary": "Covered consent; missing security.",
        "law_notes": [{"act": "TINY", "theme": "Security gap."}],
      }
    )

  report = generate_report(_analysis(), chat=chat, report_dir=tmp_path)
  saved = tmp_path / "DOC_x.json"
  body = json.loads(saved.read_text(encoding="utf-8"))
  assert body["document_id"] == report.document_id
  assert body["narrative_available"] is True
  assert len(body["findings"]) == 2
