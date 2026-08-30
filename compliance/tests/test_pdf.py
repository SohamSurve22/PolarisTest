from compliance.models import (
  ComplianceReport,
  LawNote,
  ObligationFinding,
  PenaltyFinding,
  ReportCounts,
)
from compliance.pdf import display_source_name, pdf_download_name, render_pdf
from compliance.report import NARRATIVE_UNAVAILABLE


def _report() -> ComplianceReport:
  return ComplianceReport(
    document_id="DOC_x",
    jurisdiction="IN",
    applicable_laws=["TINY"],
    generated_at="2026-08-30T05:00:00Z",
    counts=ReportCounts(covered=1, partial=0, missing=1, total=2),
    executive_summary="",
    narrative_available=False,
    law_notes=[LawNote(act="TINY", note="Security is missing.")],
    findings=[
      ObligationFinding(
        obligation_id="TINY_CONSENT",
        title="Obtain consent",
        act="TINY",
        status="covered",
      ),
      ObligationFinding(
        obligation_id="TINY_SECURE",
        title="Secure personal data",
        act="TINY",
        status="missing",
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


def test_render_pdf_contains_all_obligation_ids() -> None:
  pdf = render_pdf(_report())
  assert pdf.startswith(b"%PDF")
  assert b"TINY_CONSENT" in pdf
  assert b"TINY_SECURE" in pdf
  assert b"PolarisLex" in pdf
  assert NARRATIVE_UNAVAILABLE.encode("latin-1") in pdf
  assert b"Not a legal opinion. Coverage statuses are from automated analysis" in pdf


def test_render_pdf_includes_priority_gaps_and_scoreboard() -> None:
  report = _report()
  report.executive_summary = "This policy covers 1 of 2 scored duties, with 0 partial and 1 missing."
  report.priority_gaps = [
    ObligationFinding(
      obligation_id="TINY_SECURE",
      title="Secure personal data",
      act="TINY",
      status="missing",
    )
  ]
  pdf = render_pdf(report)
  assert b"Priority gaps" in pdf
  assert b"TINY_SECURE" in pdf
  assert b"250" in pdf
  assert b"This policy covers 1 of 2 scored duties" in pdf
  assert NARRATIVE_UNAVAILABLE.encode("latin-1") not in pdf


def test_display_source_name_uses_basename_or_document_id() -> None:
  report = _report()
  report.source_filename = "uploads/foo/policy.txt"
  assert display_source_name(report) == "policy.txt"
  report.source_filename = "../../../etc/passwd"
  assert display_source_name(report) == "passwd"
  report.source_filename = ""
  assert display_source_name(report) == "DOC_x"


def test_pdf_download_name_uses_sanitized_stem() -> None:
  report = _report()
  report.source_filename = "policy.txt"
  assert pdf_download_name(report) == "polarislex-policy.pdf"
  report.source_filename = 'AetherCloud_Privacy_&_Data_Governance_Policy.pdf'
  assert pdf_download_name(report) == "polarislex-AetherCloud_Privacy_&_Data_Governance_Policy.pdf"
  report.source_filename = 'evil/"quote".pdf'
  assert '"' not in pdf_download_name(report)
  assert "/" not in pdf_download_name(report)
  report.source_filename = ""
  assert pdf_download_name(report) == "polarislex-DOC_x.pdf"


def test_render_pdf_includes_source_filename() -> None:
  report = _report()
  report.source_filename = "policy.txt"
  pdf = render_pdf(report)
  assert b"policy.txt" in pdf


def test_render_pdf_banner_includes_conflict() -> None:
  report = _report()
  report.counts = ReportCounts(
    covered=16,
    partial=9,
    missing=2,
    violation=8,
    conflict=10,
    not_applicable=18,
    total=45,
  )
  pdf = render_pdf(report)
  assert b"Conflict 10" in pdf
  assert b"Covered 16" in pdf
  assert b"N/A 18" in pdf
